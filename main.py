import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.client import client_pool
from app.api import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Duck.ai API Wrapper service...")
    await client_pool.start()
    yield
    # Shutdown
    logger.info("Shutting down Duck.ai API Wrapper service...")
    await client_pool.shutdown()

app = FastAPI(
    title="Duck.ai OpenAI-Compatible API",
    description="Production-ready OpenAI-compatible wrapper for Duck.ai (DuckDuckGo AI Chat) with automatic challenge and session handling.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
