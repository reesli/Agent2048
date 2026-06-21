"""Tests for prompts, config, and tokenizer modules."""

import tempfile
from pathlib import Path

from agent2048.config import Settings, MutableSettings
from agent2048.prompts import AGENT_SYSTEM, CHAT_SYSTEM, build_context_prompt, build_observation_prompt
from agent2048.tokenizer import count_tokens
from agent2048.memory import MemoryItem
import numpy as np


class TestPrompts:
    def test_agent_system_not_empty(self):
        assert len(AGENT_SYSTEM) > 100
        assert "JSON" in AGENT_SYSTEM
        assert "THINK" in AGENT_SYSTEM
        assert "DONE" in AGENT_SYSTEM

    def test_chat_system_not_empty(self):
        assert len(CHAT_SYSTEM) > 50
        assert "memory" in CHAT_SYSTEM.lower()

    def test_build_context_prompt_with_memory(self):
        items = [
            MemoryItem(id="1", content="Test fact", level=1, embedding=np.array([0.1], dtype=np.float32), tag="test"),
            MemoryItem(id="2", content="Test pattern", level=2, embedding=np.array([0.2], dtype=np.float32), tag="test"),
        ]
        prompt = build_context_prompt("do something", items)
        assert "do something" in prompt
        assert "concrete fact" in prompt
        assert "pattern" in prompt

    def test_build_context_prompt_empty_memory(self):
        prompt = build_context_prompt("do something", [])
        assert "do something" in prompt
        assert "no relevant memory" in prompt

    def test_build_observation_prompt_empty_history(self):
        prompt = build_observation_prompt([])
        assert "JSON object" in prompt

    def test_build_observation_prompt_with_history(self):
        history = [
            {"step": 1, "action": {"type": "THINK"}, "result": "thinking"},
            {"step": 2, "action": {"type": "READ"}, "result": "file content"},
        ]
        prompt = build_observation_prompt(history, last_step=0)
        assert "Step 1" in prompt
        assert "Step 2" in prompt

    def test_build_observation_prompt_incremental(self):
        """Test that incremental building only appends new steps."""
        build_observation_prompt._cache = {}  # Reset cache
        history1 = [{"step": 1, "action": {"type": "THINK"}, "result": "first"}]
        prompt1 = build_observation_prompt(history1, last_step=0)

        history2 = history1 + [{"step": 2, "action": {"type": "READ"}, "result": "second"}]
        prompt2 = build_observation_prompt(history2, last_step=1)

        assert "Step 1" in prompt2
        assert "Step 2" in prompt2


class TestTokenizer:
    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_simple(self):
        tokens = count_tokens("hello world")
        assert tokens > 0
        assert tokens < 10

    def test_count_tokens_long_text(self):
        text = "word " * 1000
        tokens = count_tokens(text)
        assert tokens > 500

    def test_count_tokens_unicode(self):
        tokens = count_tokens("привет мир")
        assert tokens > 0


class TestConfig:
    def test_settings_has_required_fields(self):
        """Settings should have all required config fields."""
        import os
        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        s = Settings()
        assert hasattr(s, "openai_api_key")
        assert hasattr(s, "openai_base_url")
        assert hasattr(s, "model")
        assert hasattr(s, "max_steps")
        assert hasattr(s, "max_merge_depth")
        assert hasattr(s, "max_context_tokens")

    def test_settings_defaults(self):
        """Settings should have sensible defaults."""
        import os
        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        s = Settings()
        assert s.max_steps == 1000
        assert s.max_merge_depth == 4
        assert s.max_context_tokens == 200000
        assert s.merge_similarity_threshold == 0.82

    def test_mutable_settings_reload(self):
        """MutableSettings should reload from .env."""
        import os
        import agent2048.config as cfg
        saved = {k: os.environ.pop(k, None) for k in ["OPENAI_API_KEY", "MODEL", "OPENAI_BASE_URL"]}
        saved_candidates = cfg._ENV_CANDIDATES[:]
        try:
            # Only use local .env for this test
            cfg._ENV_CANDIDATES = [Path(".env")]
            with tempfile.TemporaryDirectory() as tmpdir:
                env_file = Path(tmpdir) / ".env"
                env_file.write_text("OPENAI_API_KEY=test1\nMODEL=model1\n")

                original_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    ms = MutableSettings()
                    assert ms.model == "model1"

                    # Change .env and reload
                    env_file.write_text("OPENAI_API_KEY=test2\nMODEL=model2\n")
                    ms.reload()
                    assert ms.model == "model2"
                finally:
                    os.chdir(original_cwd)
        finally:
            cfg._ENV_CANDIDATES = saved_candidates
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
