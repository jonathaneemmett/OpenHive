import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CONFIG_PATH = Path.home() / ".openhive" / "config.json"


def get_api_key() -> str:
    """Load API key from env var, falling back to config file."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key

    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text())
        key = config.get("openrouter_api_key")
        if isinstance(key, str) and key:
            return key

    raise ValueError(
        "No OpenRouter API key found. Set OPENROUTER_API_KEY env var "
        f"or add 'openrouter_api_key' to {CONFIG_PATH}"
    )


def get_default_model() -> str:
    """Load default model from config file, or use a sensible default."""
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text())
        model = config.get("default_model")
        if isinstance(model, str) and model:
            return model
    return "anthropic/claude-sonnet-4-20250514"


async def chat(prompt: str, model: str | None = None) -> str:
    """Send a prompt to OpenRouter and return the response."""
    api_key = get_api_key()
    model = model or get_default_model()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data: dict[str, list[dict[str, dict[str, str]]]] = response.json()
        content: str = data["choices"][0]["message"]["content"]
        return content


async def list_models() -> list[dict[str, str]]:
    """Fetch available models from OpenRouter."""
    api_key = get_api_key()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{OPENROUTER_BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return [
            {"id": m["id"], "name": m.get("name", m["id"])}
            for m in data.get("data", [])
        ]
