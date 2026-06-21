"""Tests for provider registry and configuration loading."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from agent2048.providers import (
    BUILTIN_PROVIDERS,
    _extract_provider,
    _load_jsonc,
    get_all_providers,
    get_env_for_provider,
    guess_provider_from_env,
    list_models,
    load_user_providers,
)


def test_builtin_providers_have_required_fields():
    """Every built-in provider must have base_url and non-empty models."""
    for name, cfg in BUILTIN_PROVIDERS.items():
        assert "base_url" in cfg, f"{name} missing base_url"
        assert cfg["base_url"], f"{name} has empty base_url"
        assert "models" in cfg, f"{name} missing models"
        assert len(cfg["models"]) > 0, f"{name} has no models"


def test_builtin_providers_known_names():
    """Verify key providers are present."""
    expected = {"openai", "anthropic", "google", "openrouter", "groq", "fireworks", "deepseek", "nvidia"}
    present = set(BUILTIN_PROVIDERS.keys())
    missing = expected - present
    assert not missing, f"Missing expected providers: {missing}"


def test_load_jsonc_with_comments():
    """JSONC parser should strip single-line comments."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonc", delete=False) as f:
        f.write("""
        {
            // This is a comment
            "name": "test",
            "value": 42 // inline comment
        }
        """)
        f.flush()
        try:
            data = _load_jsonc(Path(f.name))
            assert data["name"] == "test"
            assert data["value"] == 42
        finally:
            Path(f.name).unlink()


def test_load_jsonc_invalid_returns_exception():
    """Invalid JSON should raise, not silently return empty."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonc", delete=False) as f:
        f.write("{invalid json}")
        f.flush()
        try:
            raised = False
            try:
                _load_jsonc(Path(f.name))
            except Exception:
                raised = True
            assert raised, "Should raise on invalid JSON"
        finally:
            Path(f.name).unlink()


def test_load_jsonc_preserves_url_strings():
    """JSONC parser must not strip // inside string literals (e.g. https://)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonc", delete=False) as f:
        f.write(json.dumps({"baseURL": "https://example.com/v1"}))
        f.flush()
        try:
            data = _load_jsonc(Path(f.name))
            assert data["baseURL"] == "https://example.com/v1"
        finally:
            Path(f.name).unlink()


def test_extract_provider_with_models():
    """_extract_provider should parse models from opencode/kilo format."""
    cfg = {
        "options": {"baseURL": "https://example.com/v1"},
        "models": {
            "model-a": {"name": "Model A"},
            "model-b": {"name": "Model B"},
        },
    }
    result = _extract_provider("test", cfg)
    assert result["base_url"] == "https://example.com/v1"
    # _extract_provider uses model_cfg["name"] if available, else model_id
    assert "Model A" in result["models"]
    assert "Model B" in result["models"]


def test_extract_provider_with_whitelist():
    """_extract_provider should use whitelist if no models dict."""
    cfg = {
        "options": {"baseURL": "https://example.com/v1"},
        "whitelist": ["model-x", "model-y"],
    }
    result = _extract_provider("test", cfg)
    assert result["base_url"] == "https://example.com/v1"
    assert "model-x" in result["models"]
    assert "model-y" in result["models"]


def test_extract_provider_empty():
    """_extract_provider should handle missing options gracefully."""
    cfg = {}
    result = _extract_provider("test", cfg)
    assert result["base_url"] == ""
    assert result["models"] == []


def test_list_models_by_provider():
    """list_models should return models for a known provider."""
    models = list_models("openai")
    assert len(models) > 0
    assert "gpt-4o-mini" in models or "gpt-4.1-mini" in models


def test_list_models_unknown_provider():
    """list_models should return empty for unknown provider."""
    models = list_models("nonexistent")
    assert models == []


def test_list_models_from_env():
    """list_models without arg should use current env base_url."""
    with patch("agent2048.providers.settings") as mock_settings:
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        models = list_models()
        assert len(models) > 0


def test_get_env_for_provider():
    """get_env_for_provider should return env snippet for a known provider."""
    env = get_env_for_provider("openai")
    assert env["OPENAI_BASE_URL"] == "https://api.openai.com/v1"
    assert env["EMBEDDING_PROVIDER"] == "fastembed"
    assert env["EMBEDDING_MODEL"] == "BAAI/bge-small-en-v1.5"
    assert env["MODEL"] in BUILTIN_PROVIDERS["openai"]["models"]


def test_guess_provider_from_env_openai():
    """guess_provider_from_env should identify provider by base_url."""
    with patch("agent2048.providers.settings") as mock_settings:
        mock_settings.openai_base_url = "https://api.openai.com/v1"
        result = guess_provider_from_env()
        assert result == "openai"


def test_guess_provider_from_env_unknown():
    """guess_provider_from_env should return 'custom' for unknown base_url."""
    with patch("agent2048.providers.settings") as mock_settings:
        mock_settings.openai_base_url = "https://unknown.example.com/v1"
        result = guess_provider_from_env()
        assert result == "custom"


def test_get_all_providers_includes_builtin():
    """get_all_providers should include all built-in providers."""
    providers = get_all_providers()
    assert "openai" in providers
    assert "anthropic" in providers
    assert len(providers) >= len(BUILTIN_PROVIDERS)


def _patch_home(tmpdir: str) -> Path:
    """Temporarily redirect Path.home to tmpdir and return the original."""
    original_home = Path.home
    Path.home = lambda: Path(tmpdir)
    return original_home


def test_load_user_providers_with_opencode_config():
    """load_user_providers should parse opencode.jsonc if it exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        opencode_dir = Path(tmpdir) / ".config" / "opencode"
        opencode_dir.mkdir(parents=True)
        config = opencode_dir / "opencode.jsonc"
        config.write_text(json.dumps({
            "provider": {
                "custom-provider": {
                    "options": {"baseURL": "https://custom.example.com/v1"},
                    "models": {"custom-model": {"name": "Custom Model"}},
                }
            }
        }))

        original_home = _patch_home(tmpdir)
        try:
            providers = load_user_providers()
            assert "custom-provider" in providers
            assert providers["custom-provider"]["base_url"] == "https://custom.example.com/v1"
        finally:
            Path.home = original_home


def test_load_user_providers_with_opencode_legacy_string_format():
    """load_user_providers should parse legacy opencode format where provider is a string."""
    with tempfile.TemporaryDirectory() as tmpdir:
        opencode_dir = Path(tmpdir) / ".config" / "opencode"
        opencode_dir.mkdir(parents=True)
        config = opencode_dir / "opencode.jsonc"
        config.write_text(json.dumps({
            "provider": "legacy-provider",
            "options": {"baseURL": "https://legacy.example.com/v1"},
        }))

        original_home = _patch_home(tmpdir)
        try:
            providers = load_user_providers()
            assert "legacy-provider" in providers
            assert providers["legacy-provider"]["base_url"] == "https://legacy.example.com/v1"
        finally:
            Path.home = original_home


def test_load_user_providers_with_kilo_config():
    """load_user_providers should parse kilo.jsonc if it exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kilo_dir = Path(tmpdir) / ".config" / "kilo"
        kilo_dir.mkdir(parents=True)
        config = kilo_dir / "kilo.jsonc"
        config.write_text(json.dumps({
            "provider": {
                "kilo-provider": {
                    "options": {"baseURL": "https://kilo.example.com/v1"},
                    "whitelist": ["kilo-model"],
                }
            }
        }))

        original_home = _patch_home(tmpdir)
        try:
            providers = load_user_providers()
            assert "kilo-provider" in providers
            assert providers["kilo-provider"]["base_url"] == "https://kilo.example.com/v1"
            assert "kilo-model" in providers["kilo-provider"]["models"]
        finally:
            Path.home = original_home


def test_load_user_providers_ignores_missing_configs():
    """load_user_providers should return empty dict when no user configs exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_home = _patch_home(tmpdir)
        try:
            providers = load_user_providers()
            assert providers == {}
        finally:
            Path.home = original_home
