"""Tests for the agent loop."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import openai
import pytest
from rich.console import Console

from agent2048.agent import Agent
from agent2048.memory import MemoryStore
from agent2048.theme import WAYBAR_THEME


def test_agent_writes_and_finishes():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workdir = Path(tmpdir) / "project"
        workdir.mkdir()
        with MemoryStore(db_path=str(db_path)) as memory:
            agent = Agent(memory=memory, workdir=workdir, console=Console(theme=WAYBAR_THEME), approve_all=True)

            fake_llm = MagicMock()
            fake_llm.embed.return_value = [0.1] * 384
            responses = [
                '{"type": "WRITE", "payload": {"path": "hello.txt", "content": "Hello, Agent2048!"}}',
                '{"type": "DONE", "payload": {"result": "Done"}}',
            ]
            fake_llm.chat.side_effect = responses

            with patch("agent2048.agent.llm", fake_llm), patch("agent2048.memory.llm", fake_llm):
                result = agent.run("Create a hello.txt file")

            assert result == "Done"
            assert (workdir / "hello.txt").read_text() == "Hello, Agent2048!"


class TestChatWithRetry:
    def test_chat_success_no_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=Path(tmpdir), console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.chat.return_value = "ok"
                with patch("agent2048.agent.llm", fake_llm):
                    result = agent._chat_with_retry([{"role": "user", "content": "hi"}])
                assert result == "ok"
                assert fake_llm.chat.call_count == 1

    def test_chat_rate_limit_retries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=Path(tmpdir), console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.chat.side_effect = [
                    openai.RateLimitError("rate limited", response=MagicMock(), body=None),
                    "ok",
                ]
                with patch("agent2048.agent.llm", fake_llm), patch("agent2048.agent.time.sleep"):
                    result = agent._chat_with_retry([{"role": "user", "content": "hi"}], max_retries=2)
                assert result == "ok"
                assert fake_llm.chat.call_count == 2

    def test_chat_api_error_retries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=Path(tmpdir), console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.chat.side_effect = [
                    openai.APIConnectionError(message="connection failed", request=MagicMock()),
                    "ok",
                ]
                with patch("agent2048.agent.llm", fake_llm), patch("agent2048.agent.time.sleep"):
                    result = agent._chat_with_retry([{"role": "user", "content": "hi"}], max_retries=2)
                assert result == "ok"
                assert fake_llm.chat.call_count == 2

    def test_chat_max_retries_exceeded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=Path(tmpdir), console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.chat.side_effect = openai.RateLimitError("rate limited", response=MagicMock(), body=None)
                with patch("agent2048.agent.llm", fake_llm), patch("agent2048.agent.time.sleep"):
                    with pytest.raises(RuntimeError, match="LLM request failed after"):
                        agent._chat_with_retry([{"role": "user", "content": "hi"}], max_retries=2)
                assert fake_llm.chat.call_count == 2

    def test_chat_unexpected_error_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=Path(tmpdir), console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.chat.side_effect = ValueError("boom")
                with patch("agent2048.agent.llm", fake_llm):
                    with pytest.raises(ValueError, match="boom"):
                        agent._chat_with_retry([{"role": "user", "content": "hi"}])


class TestAgentRun:
    def test_run_parse_error_recovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            workdir = Path(tmpdir) / "project"
            workdir.mkdir()
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=workdir, console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.embed.return_value = [0.1] * 384
                fake_llm.chat.side_effect = [
                    "not valid json",
                    '{"type": "DONE", "payload": {"result": "Done"}}',
                ]
                with patch("agent2048.agent.llm", fake_llm), patch("agent2048.memory.llm", fake_llm):
                    result = agent.run("task")
                assert result == "Done"

    def test_run_llm_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            workdir = Path(tmpdir) / "project"
            workdir.mkdir()
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=workdir, console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.embed.return_value = [0.1] * 384
                fake_llm.chat.side_effect = RuntimeError("LLM failed")
                with patch("agent2048.agent.llm", fake_llm), patch("agent2048.memory.llm", fake_llm):
                    result = agent.run("task")
                assert "Agent stopped" in result

    def test_run_max_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            workdir = Path(tmpdir) / "project"
            workdir.mkdir()
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=workdir, console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.embed.return_value = [0.1] * 384
                # Always return THINK so agent never DONE
                fake_llm.chat.return_value = '{"type": "THINK", "payload": {"thought": "thinking"}}'
                with patch("agent2048.agent.llm", fake_llm), patch("agent2048.memory.llm", fake_llm):
                    from agent2048.config import settings
                    with patch.object(settings, "max_steps", 2):
                        result = agent.run("task")
                assert "max steps" in result

    def test_run_memory_add_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            workdir = Path(tmpdir) / "project"
            workdir.mkdir()
            with MemoryStore(db_path=str(db_path)) as memory:
                agent = Agent(memory=memory, workdir=workdir, console=Console(theme=WAYBAR_THEME), approve_all=True)
                fake_llm = MagicMock()
                fake_llm.embed.return_value = [0.1] * 384
                fake_llm.chat.return_value = '{"type": "DONE", "payload": {"result": "Done"}}'
                with patch("agent2048.agent.llm", fake_llm), patch("agent2048.memory.llm", fake_llm):
                    with patch.object(memory, "add", side_effect=RuntimeError("DB locked")):
                        result = agent.run("task")
                assert result == "Done"
