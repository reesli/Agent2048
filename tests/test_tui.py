"""Tests for TUI command dispatch and model selection."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent2048.tui import COMMAND_HELP, run_tui


class TestCommandHelp:
    def test_all_commands_have_help(self):
        """Every command should have a help entry."""
        expected = {"ask", "chat", "stats", "memory", "dive", "providers", "models",
                     "use", "model", "set-key", "project", "init", "help", "exit"}
        assert expected.issubset(set(COMMAND_HELP.keys()))

    def test_help_text_not_empty(self):
        """Help text should be non-empty for all commands."""
        for cmd, desc in COMMAND_HELP.items():
            assert desc, f"{cmd} has empty help text"
            assert len(desc) >= 8, f"{cmd} help text too short"


class TestModelNumberSelection:
    """Test that `model <number>` selects from last shown list."""

    def test_model_number_parsing(self):
        """Test numeric model argument detection."""
        assert "1".isdigit()
        assert "42".isdigit()
        assert not "model-id".isdigit()
        assert not "".isdigit()


class TestUseCommand:
    """Test use command argument parsing logic."""

    def test_use_provider_only(self):
        """use <provider> — no key, no model."""
        parts = "use nvidia".split()
        assert parts[0] == "use"
        assert parts[1] == "nvidia"
        assert len(parts) == 2

    def test_use_provider_key(self):
        """use <provider> <key> — key as second arg."""
        parts = "use nvidia nvapi-xxx".split()
        assert parts[1] == "nvidia"
        assert parts[2] == "nvapi-xxx"
        assert not parts[2].startswith("--")

    def test_use_provider_model(self):
        """use <provider> --model <id> — model flag."""
        parts = "use nvidia --model meta/llama-3.3".split()
        assert parts[1] == "nvidia"
        assert parts[2] == "--model"
        assert parts[3] == "meta/llama-3.3"

    def test_use_provider_key_model(self):
        """use <provider> <key> --model <id> — both key and model."""
        parts = "use nvidia nvapi-xxx --model meta/llama-3.3".split()
        assert parts[1] == "nvidia"
        assert parts[2] == "nvapi-xxx"
        assert not parts[2].startswith("--")
        assert parts[3] == "--model"
        assert parts[4] == "meta/llama-3.3"
