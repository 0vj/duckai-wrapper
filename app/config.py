import os

class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    MAX_CONCURRENT_SESSIONS: int = int(os.getenv("MAX_CONCURRENT_SESSIONS", "3"))
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-6-luna")
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    SEC_CH_UA: str = os.getenv(
        "SEC_CH_UA",
        '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"'
    )
    BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
    SESSION_TIMEOUT_SECONDS: int = int(os.getenv("SESSION_TIMEOUT_SECONDS", "180"))

settings = Settings()

# Live models discovered directly from Duck.ai runtime bundle
AVAILABLE_MODELS = {
    "gpt-6-luna": {
        "name": "GPT-6 Luna",
        "owned_by": "openai",
        "setting_id": "291",
        "description": "OpenAI flagship model on Duck.ai (Free)",
        "is_default": True
    },
    "gpt-5.4-mini": {
        "name": "GPT-5.4 mini",
        "owned_by": "openai",
        "setting_id": "262",
        "description": "OpenAI compact fast model (Free)",
        "is_default": False
    },
    "claude-haiku-5-5": {
        "name": "Claude Haiku 5.5",
        "owned_by": "anthropic",
        "setting_id": "295",
        "description": "Anthropic Claude Haiku 5.5 (Free)",
        "is_default": False
    },
    "mistral-small-2603": {
        "name": "Mistral Small 4",
        "owned_by": "mistralai",
        "setting_id": "6",
        "description": "Mistral Small 4 open weights model (Free)",
        "is_default": False
    },
    "tinfoil/gpt-oss-120b": {
        "name": "gpt-oss 120B",
        "owned_by": "openai",
        "setting_id": "251",
        "description": "OpenAI open weights model running in confidential enclave (Free)",
        "is_default": False
    },
    "tinfoil/gemma4-31b": {
        "name": "Gemma 4 31B",
        "owned_by": "google",
        "setting_id": "270",
        "description": "Google Gemma 4 31B running in confidential enclave (Free)",
        "is_default": False
    }
}

# Compatibility mapping for standard OpenAI / Anthropic model identifiers
MODEL_ALIASES = {
    "gpt-4o": "gpt-6-luna",
    "gpt-4o-mini": "gpt-5.4-mini",
    "gpt-4": "gpt-6-luna",
    "gpt-4-turbo": "gpt-6-luna",
    "gpt-3.5-turbo": "gpt-5.4-mini",
    "claude-3-5-sonnet": "claude-haiku-5-5",
    "claude-3-5-sonnet-20240620": "claude-haiku-5-5",
    "claude-3-5-sonnet-20241022": "claude-haiku-5-5",
    "claude-3-7-sonnet": "claude-haiku-5-5",
    "claude-3-haiku": "claude-haiku-5-5",
    "claude-haiku": "claude-haiku-5-5",
    "mistral": "mistral-small-2603",
    "mistral-small": "mistral-small-2603",
    "mixtral": "mistral-small-2603",
    "gemma": "tinfoil/gemma4-31b",
    "gemma-2": "tinfoil/gemma4-31b",
    "gpt-oss": "tinfoil/gpt-oss-120b"
}

def resolve_model(requested_model: str) -> str:
    """Resolves an incoming model name or alias to a valid Duck.ai model ID."""
    if not requested_model:
        return settings.DEFAULT_MODEL
    requested_model = requested_model.strip().lower()
    if requested_model in AVAILABLE_MODELS:
        return requested_model
    if requested_model in MODEL_ALIASES:
        return MODEL_ALIASES[requested_model]
    for key in AVAILABLE_MODELS:
        if requested_model in key or key in requested_model:
            return key
    return settings.DEFAULT_MODEL
