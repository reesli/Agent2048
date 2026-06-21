"""Typed exceptions for Agent2048.

Replaces silent except Exception: pass with specific, loggable errors.
"""


class Agent2048Error(Exception):
    """Base exception for all Agent2048 errors."""


class MemoryError(Agent2048Error):
    """Memory store errors (DB, embedding, merge)."""


class LLMError(Agent2048Error):
    """LLM API errors (retry exhausted, invalid response)."""


class ActionError(Agent2048Error):
    """Action execution errors (parse, permission, path)."""


class ConfigError(Agent2048Error):
    """Configuration errors (missing key, invalid value)."""


class ProviderError(Agent2048Error):
    """Provider errors (unknown provider, invalid base_url)."""
