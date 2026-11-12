import json
import logging
import time
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import AVAILABLE_MODELS, MODEL_ALIASES, resolve_model
from app.client import client_pool, format_openai_messages
from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatMessageResponse,
    UsageInfo,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    DeltaMessage,
    ModelData,
    ModelListResponse
)

logger = logging.getLogger("duckai_api")
router = APIRouter()

@router.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    """List all models currently supported by Duck.ai."""
    model_entries = []
    
    # 1. Primary supported models
    for model_id, details in AVAILABLE_MODELS.items():
        model_entries.append(
            ModelData(
                id=model_id,
                created=int(time.time()),
                owned_by=details["owned_by"],
                root=model_id
            )
        )
        
    # 2. Aliases for OpenAI drop-in compatibility
    for alias, target in MODEL_ALIASES.items():
        if alias not in AVAILABLE_MODELS:
            model_entries.append(
                ModelData(
                    id=alias,
                    created=int(time.time()),
                    owned_by=AVAILABLE_MODELS.get(target, {}).get("owned_by", "duckai"),
                    root=target,
                    parent=target
                )
            )

    return ModelListResponse(object="list", data=model_entries)

@router.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """Retrieve details for a single model."""
    resolved = resolve_model(model_id)
    if resolved in AVAILABLE_MODELS:
        details = AVAILABLE_MODELS[resolved]
        return ModelData(
            id=model_id,
            created=int(time.time()),
            owned_by=details["owned_by"],
            root=resolved
        )
    raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

@router.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """OpenAI-compatible chat completion endpoint supporting streaming and non-streaming."""
    if not req.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Messages list cannot be empty"
        )

    resolved_model = resolve_model(req.model)
    prompt_text = format_openai_messages(req.messages)
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    logger.info(f"Incoming chat request for model='{req.model}' (resolved to '{resolved_model}'), stream={req.stream}")

    if req.stream:
        async def event_generator() -> AsyncGenerator[str, None]:
            session = None
            try:
                session = await client_pool.acquire_session(resolved_model)
                
                # First chunk with role
                first_chunk = ChatCompletionChunk(
                    id=completion_id,
                    created=created_ts,
                    model=resolved_model,
                    choices=[
                        ChatCompletionChunkChoice(
                            index=0,
                            delta=DeltaMessage(role="assistant", content=""),
                            finish_reason=None
                        )
                    ]
                )
                yield f"data: {first_chunk.model_dump_json()}\n\n"

                async for token in session.send_chat(prompt_text, resolved_model):
                    chunk = ChatCompletionChunk(
                        id=completion_id,
                        created=created_ts,
                        model=resolved_model,
                        choices=[
                            ChatCompletionChunkChoice(
                                index=0,
                                delta=DeltaMessage(content=token),
                                finish_reason=None
                            )
                        ]
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"

                # Final chunk with finish_reason='stop'
                stop_chunk = ChatCompletionChunk(
                    id=completion_id,
                    created=created_ts,
                    model=resolved_model,
                    choices=[
                        ChatCompletionChunkChoice(
                            index=0,
                            delta=DeltaMessage(),
                            finish_reason="stop"
                        )
                    ]
                )
                yield f"data: {stop_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error during stream generation: {e}")
                err_payload = {
                    "error": {
                        "message": str(e),
                        "type": "server_error",
                        "code": 500
                    }
                }
                yield f"data: {json.dumps(err_payload)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                if session:
                    await client_pool.release_session(session)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    else:
        # Non-streaming mode
        session = None
        try:
            session = await client_pool.acquire_session(resolved_model)
            collected_tokens = []
            async for token in session.send_chat(prompt_text, resolved_model):
                collected_tokens.append(token)

            full_text = "".join(collected_tokens)
            
            # Approximate token counts
            prompt_token_count = max(1, len(prompt_text) // 4)
            completion_token_count = max(1, len(full_text) // 4)

            response = ChatCompletionResponse(
                id=completion_id,
                created=created_ts,
                model=resolved_model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatMessageResponse(role="assistant", content=full_text),
                        finish_reason="stop"
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=prompt_token_count,
                    completion_tokens=completion_token_count,
                    total_tokens=prompt_token_count + completion_token_count
                )
            )
            return response
        except Exception as e:
            logger.error(f"Error during non-streaming completion: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Duck.ai completion error: {str(e)}"
            )
        finally:
            if session:
                await client_pool.release_session(session)

@router.get("/health")
async def health_check():
    """Health status and session pool information."""
    return {
        "status": "healthy",
        "service": "duckai-openai-wrapper",
        "pool_capacity": client_pool._semaphore._value if hasattr(client_pool, "_semaphore") else 0,
        "available_models": list(AVAILABLE_MODELS.keys())
    }

@router.get("/")
async def root():
    return {
        "message": "Duck.ai OpenAI-Compatible API Wrapper",
        "docs": "/docs",
        "endpoints": [
            "GET /v1/models",
            "POST /v1/chat/completions",
            "GET /health"
        ]
    }
