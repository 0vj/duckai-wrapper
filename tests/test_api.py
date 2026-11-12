import pytest
from fastapi.testclient import TestClient
from main import app
from app.config import resolve_model, AVAILABLE_MODELS, MODEL_ALIASES
from app.client import format_openai_messages
from app.models import ChatMessage

client = TestClient(app)

def test_resolve_model():
    # Direct models
    assert resolve_model("gpt-6-luna") == "gpt-6-luna"
    assert resolve_model("claude-haiku-5-5") == "claude-haiku-5-5"
    assert resolve_model("mistral-small-2603") == "mistral-small-2603"

    # Aliases
    assert resolve_model("gpt-4o") == "gpt-6-luna"
    assert resolve_model("gpt-4o-mini") == "gpt-5.4-mini"
    assert resolve_model("claude-3-5-sonnet") == "claude-haiku-5-5"
    assert resolve_model("mistral") == "mistral-small-2603"

    # Default fallback
    assert resolve_model("unknown-model-xyz") == "gpt-6-luna"

def test_format_openai_messages():
    # Single message
    msgs = [ChatMessage(role="user", content="Hello world")]
    assert format_openai_messages(msgs) == "Hello world"

    # Multi-turn with system
    msgs = [
        ChatMessage(role="system", content="Be concise"),
        ChatMessage(role="user", content="Hi"),
        ChatMessage(role="assistant", content="Hello"),
        ChatMessage(role="user", content="What is 2+2?")
    ]
    formatted = format_openai_messages(msgs)
    assert "[System Instruction: Be concise]" in formatted
    assert "User: Hi" in formatted
    assert "Assistant: Hello" in formatted
    assert "User: What is 2+2?" in formatted

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "gpt-6-luna" in data["available_models"]

def test_models_list():
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "list"
    ids = [m["id"] for m in data["data"]]
    assert "gpt-6-luna" in ids
    assert "claude-haiku-5-5" in ids
    assert "gpt-4o" in ids

def test_single_model():
    res = client.get("/v1/models/gpt-6-luna")
    assert res.status_code == 200
    assert res.json()["id"] == "gpt-6-luna"
