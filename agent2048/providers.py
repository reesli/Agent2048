"""Provider registry and configuration loader.

Loads known provider presets and can also read user configs from opencode and
kilo to reuse their provider setups without copying secrets into the project.
"""

import json
import os
from pathlib import Path
from typing import Any

from agent2048.config import settings
from agent2048.logging_config import logger


# Built-in presets for common OpenAI-compatible providers.
BUILTIN_PROVIDERS: dict[str, dict[str, Any]] = {
    "0g": {
        "base_url": "https://evmrpc-testnet.0g.ai/v1",
        "models": [
            "0g/compute/default",
            "0g/compute/llama-3.3-70b",
            "0g/compute/qwen-2.5-72b",
        ],
    },
    "aerolink": {
        "base_url": "https://capi.aerolink.lat/",
        "models": [
            "aero/claude-opus-4-7",
        ],
    },
    "alibaba": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": [
            "qwen-max",
            "qwen-plus",
            "qwen-turbo",
            "qwen-coder-plus",
            "qwen2.5-72b-instruct",
            "qwen2.5-7b-instruct",
        ],
    },
    "amazon": {
        "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com",
        "models": [
            "anthropic.claude-3-7-sonnet-20250219-v1:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "us.anthropic.claude-3-opus-4-20250514-v1:0",
            "us.meta.llama-4-maverick-17b-128e-instruct-v1:0",
            "us.meta.llama-4-scout-17b-16e-instruct-v1:0",
            "us.anthropic.claude-sonnet-4-20250514-v1:0",
        ],
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "models": [
            "claude-3-5-haiku-latest",
            "claude-3-5-sonnet-latest",
            "claude-3-7-sonnet-latest",
            "claude-3-haiku-20240307",
            "claude-3-opus-latest",
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
        ],
    },
    "azure": {
        "base_url": "https://<your-resource>.openai.azure.com/openai/deployments/<deployment>",
        "models": [
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ],
    },
    "cohere": {
        "base_url": "https://api.cohere.com/v1",
        "models": [
            "command-a-03-2025",
            "command-r-plus-08-2024",
            "command-r-08-2024",
            "command-r7b-12-2024",
        ],
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": [
            "deepseek-chat",
            "deepseek-reasoner",
            "deepseek-coder",
        ],
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "models": [
            "accounts/fireworks/models/llama4-maverick-instruct-basic",
            "accounts/fireworks/models/llama4-scout-instruct-basic",
            "accounts/fireworks/models/deepseek-r1",
            "accounts/fireworks/models/deepseek-v3",
            "accounts/fireworks/models/qwen2p5-72b-instruct",
            "accounts/fireworks/models/llama3-70b-instruct",
            "accounts/fireworks/models/llama3-8b-instruct",
        ],
    },
    "freemodel": {
        "base_url": "https://api.freemodel.ai/v1",
        "models": [
            "gpt-4o-mini",
            "claude-3-5-sonnet",
        ],
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models": [
            "gemini-2.5-pro-exp-03-25",
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": [
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "qwen-2.5-32b",
            "deepseek-r1-distill-llama-70b",
        ],
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "models": [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
            "codestral-latest",
            "pixtral-large-latest",
        ],
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models": [
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "nvidia/llama-3.3-nemotron-super-49b-v1",
            "meta/llama-3.1-405b-instruct",
            "meta/llama-3.3-70b-instruct",
        ],
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "models": [
            "llama3.1",
            "llama3",
            "mistral",
            "qwen2.5",
            "phi4",
            "deepseek-r1",
        ],
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": [
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o3",
            "o4-mini",
        ],
    },
    "opengateway": {
        "base_url": "https://api.opengateway.lat/v1",
        "models": [
            "openai/gpt-4o-mini",
            "anthropic/claude-3-5-sonnet",
        ],
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "openai/gpt-4.1",
            "openai/gpt-4o",
            "anthropic/claude-3.7-sonnet",
            "anthropic/claude-3.5-sonnet",
            "meta-llama/llama-4-maverick",
            "meta-llama/llama-4-scout",
            "deepseek/deepseek-r1",
            "deepseek/deepseek-chat-v3-0324",
            "google/gemini-2.5-pro-exp-03-25",
            "x-ai/grok-3-beta",
        ],
    },
    "perplexity": {
        "base_url": "https://api.perplexity.ai",
        "models": [
            "sonar-pro",
            "sonar-reasoning-pro",
            "sonar",
            "sonar-reasoning",
        ],
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "models": [
            "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
            "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "deepseek-ai/DeepSeek-R1",
            "deepseek-ai/DeepSeek-V3",
            "Qwen/Qwen2.5-72B-Instruct-Turbo",
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        ],
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "models": [
            "grok-3-beta",
            "grok-3-mini-beta",
            "grok-2-1212",
        ],
    },
    "xiaomi": {
        "base_url": "https://api.xiaomi.ai/v1",
        "models": [
            "xiaomi-llama-3.3-70b",
            "xiaomi-qwen2.5-72b",
        ],
    },
}


def _load_jsonc(path: Path) -> dict[str, Any]:
    """Load JSONC (JSON with comments) by stripping // comments outside strings."""
    text = path.read_text(encoding="utf-8")
    # Remove // comments only when not inside a string literal.
    result = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        ch = text[i]
        if escape:
            result.append(ch)
            escape = False
            i += 1
            continue
        if ch == "\\" and in_string:
            result.append(ch)
            escape = True
            i += 1
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            i += 1
            continue
        if not in_string and ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            # Skip until end of line
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        result.append(ch)
        i += 1
    return json.loads("".join(result))


def load_user_providers() -> dict[str, dict[str, Any]]:
    """Read provider configs from opencode and kilo if available."""
    providers: dict[str, dict[str, Any]] = {}

    opencode_path = Path.home() / ".config" / "opencode" / "opencode.jsonc"
    if opencode_path.exists():
        try:
            data = _load_jsonc(opencode_path)
            provider_name = data.get("provider", "")
            if isinstance(provider_name, dict):
                # Newer opencode format: provider is a dict keyed by name.
                for name, cfg in provider_name.items():
                    providers[name] = _extract_provider(name, cfg)
            elif provider_name and isinstance(provider_name, str):
                # Legacy opencode format: provider is a string name and the
                # rest of the top-level config describes that single provider.
                providers[provider_name] = _extract_provider(provider_name, data)
        except Exception as e:
            logger.warning("Failed to load opencode providers: %s", e)

    kilo_path = Path.home() / ".config" / "kilo" / "kilo.jsonc"
    if kilo_path.exists():
        try:
            data = _load_jsonc(kilo_path)
            for name, cfg in data.get("provider", {}).items():
                providers[name] = _extract_provider(name, cfg)
        except Exception as e:
            logger.warning("Failed to load kilo providers: %s", e)

    return providers


def _extract_provider(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Extract base_url and model list from an opencode/kilo provider block."""
    options = cfg.get("options", {})
    base_url = options.get("baseURL", "")
    models = []
    if "models" in cfg:
        for model_id, model_cfg in cfg["models"].items():
            if isinstance(model_cfg, dict) and "name" in model_cfg:
                models.append(model_cfg["name"])
            else:
                models.append(model_id)
    elif "whitelist" in cfg:
        models.extend(cfg["whitelist"])
    return {"base_url": base_url, "models": models}


def get_all_providers() -> dict[str, dict[str, Any]]:
    """Return built-in providers merged with user-configured providers."""
    providers = dict(BUILTIN_PROVIDERS)
    providers.update(load_user_providers())
    return providers


def guess_provider_from_env() -> str:
    """Guess the provider name from the configured base_url."""
    base_url = settings.openai_base_url.rstrip("/")
    for name, cfg in get_all_providers().items():
        if cfg.get("base_url", "").rstrip("/") == base_url:
            return name
    return "custom"


def list_models(provider_name: str | None = None) -> list[str]:
    """List models for a provider or for the current environment."""
    providers = get_all_providers()
    if provider_name:
        return providers.get(provider_name, {}).get("models", [])
    name = guess_provider_from_env()
    return providers.get(name, {}).get("models", [])


def get_env_for_provider(provider_name: str) -> dict[str, str]:
    """Return a minimal env snippet for a provider."""
    cfg = get_all_providers().get(provider_name, {})
    return {
        "OPENAI_BASE_URL": cfg.get("base_url", ""),
        "MODEL": cfg.get("models", [""])[0],
        "EMBEDDING_PROVIDER": "fastembed",
        "EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
    }
