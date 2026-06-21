"""Tests for action parsing and execution."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent2048.actions import Action, ActionExecutor, parse_action
from agent2048.memory import MemoryStore
from agent2048.toml_config import ProjectConfig


def test_parse_plain_json():
    text = '{"type": "THINK", "payload": {"thought": "ok"}}'
    action = parse_action(text)
    assert action.type == "THINK"
    assert action.payload == {"thought": "ok"}


def test_parse_markdown_fenced_json():
    text = """```json
{"type": "WRITE", "payload": {"path": "x.txt", "content": "hi"}}
```"""
    action = parse_action(text)
    assert action.type == "WRITE"
    assert action.payload["path"] == "x.txt"


def test_parse_json_with_prose():
    text = """Sure, here is the next action:

```json
{"type": "RUN", "payload": {"command": "ls", "description": "list files"}}
```

Hope that helps."""
    action = parse_action(text)
    assert action.type == "RUN"
    assert action.payload["command"] == "ls"


def test_parse_json_without_fences_with_prose():
    text = """I think the best next step is to run the tests.

{"type": "RUN", "payload": {"command": "pytest", "description": "run tests"}}

That should verify everything."""
    action = parse_action(text)
    assert action.type == "RUN"
    assert action.payload["command"] == "pytest"


def test_parse_invalid_fenced_json_falls_back_to_plain():
    text = """```json
not valid json
```

{"type": "THINK", "payload": {"thought": "fallback"}}"""
    action = parse_action(text)
    assert action.type == "THINK"
    assert action.payload["thought"] == "fallback"


def test_parse_full_text_fallback():
    text = '{"type": "DONE", "payload": {"result": "finished"}}'
    action = parse_action(text)
    assert action.type == "DONE"
    assert action.payload["result"] == "finished"


def test_parse_invalid_json_raises():
    with pytest.raises(Exception):
        parse_action("not valid json at all")


class TestResolvePath:
    def test_resolve_relative_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            executor = ActionExecutor(memory=MagicMock(), workdir=workdir)
            resolved = executor._resolve_path("sub/file.txt")
            assert resolved == (workdir / "sub" / "file.txt").resolve()

    def test_resolve_absolute_path_inside_workdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            executor = ActionExecutor(memory=MagicMock(), workdir=workdir)
            resolved = executor._resolve_path(str(workdir / "file.txt"))
            assert resolved == (workdir / "file.txt").resolve()

    def test_resolve_path_outside_workdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            executor = ActionExecutor(memory=MagicMock(), workdir=workdir)
            assert executor._resolve_path("/etc/passwd") is None

    def test_resolve_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            executor = ActionExecutor(memory=MagicMock(), workdir=workdir)
            assert executor._resolve_path("../outside.txt") is None


class TestActionExecutor:
    def test_think_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = ActionExecutor(memory=MagicMock(), workdir=Path(tmpdir))
            result = executor.execute(Action(type="THINK", payload={"thought": "plan"}), step=1)
            assert result["result"] == "plan"
            assert "plan" in result["display"]

    def test_done_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = ActionExecutor(memory=MagicMock(), workdir=Path(tmpdir))
            result = executor.execute(Action(type="DONE", payload={"result": "Done"}), step=1)
            assert result["result"] == "Done"

    def test_memory_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            memory = MemoryStore(db_path=str(db_path))
            executor = ActionExecutor(memory=memory, workdir=Path(tmpdir))
            result = executor.execute(Action(type="MEMORY", payload={"content": "fact", "level": 1, "tag": "test"}), step=1)
            assert "saved" in result["result"].lower() or "L1" in result["display"]
            memory.close()

    def test_read_outside_workdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = ActionExecutor(memory=MagicMock(), workdir=Path(tmpdir))
            result = executor.execute(Action(type="READ", payload={"path": "/etc/passwd"}), step=1)
            assert "outside workdir" in result["result"]

    def test_write_outside_workdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = ActionExecutor(memory=MagicMock(), workdir=Path(tmpdir))
            result = executor.execute(Action(type="WRITE", payload={"path": "../outside.txt", "content": "x"}), step=1)
            assert "outside workdir" in result["result"]

    def test_read_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            (workdir / "file.txt").write_text("hello")
            executor = ActionExecutor(memory=MagicMock(), workdir=workdir)
            result = executor.execute(Action(type="READ", payload={"path": "file.txt"}), step=1)
            assert result["result"] == "hello"

    def test_write_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            executor = ActionExecutor(memory=MagicMock(), workdir=workdir)
            result = executor.execute(Action(type="WRITE", payload={"path": "file.txt", "content": "hello"}), step=1)
            assert (workdir / "file.txt").read_text() == "hello"
            assert "Wrote" in result["result"]

    def test_run_empty_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = ActionExecutor(memory=MagicMock(), workdir=Path(tmpdir))
            result = executor.execute(Action(type="RUN", payload={"command": ""}), step=1)
            assert result["result"] == "No command"

    def test_run_blocked_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = ActionExecutor(memory=MagicMock(), workdir=Path(tmpdir))
            result = executor.execute(Action(type="RUN", payload={"command": "rm -rf /"}), step=1)
            assert result["result"] == "Blocked"

    def test_run_allowed_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            executor = ActionExecutor(memory=MagicMock(), workdir=workdir)
            result = executor.execute(Action(type="RUN", payload={"command": "echo hello", "description": "say hi"}), step=1)
            assert "hello" in result["result"]
            assert "exit=0" in result["result"]

    def test_denied_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            console = MagicMock()
            console.input.return_value = "n"
            executor = ActionExecutor(
                memory=MagicMock(),
                workdir=Path(tmpdir),
                console=console,
                project_cfg=ProjectConfig(),
                approve_all=False,
            )
            result = executor.execute(Action(type="RUN", payload={"command": "echo hi"}), step=1)
            assert result["result"] == "Denied by user"

    def test_approved_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            console = MagicMock()
            console.input.return_value = "y"
            executor = ActionExecutor(
                memory=MagicMock(),
                workdir=Path(tmpdir),
                console=console,
                project_cfg=ProjectConfig(),
                approve_all=False,
            )
            result = executor.execute(Action(type="RUN", payload={"command": "echo hello"}), step=1)
            assert "hello" in result["result"]

    def test_approve_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            console = MagicMock()
            console.input.return_value = "always"
            executor = ActionExecutor(
                memory=MagicMock(),
                workdir=Path(tmpdir),
                console=console,
                project_cfg=ProjectConfig(),
                approve_all=False,
            )
            result = executor.execute(Action(type="RUN", payload={"command": "echo hello"}), step=1)
            assert "hello" in result["result"]
            assert executor.approve_all is True

    def test_allowed_action_no_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            console = MagicMock()
            cfg = ProjectConfig(allowed_patterns=["echo*"])
            executor = ActionExecutor(
                memory=MagicMock(),
                workdir=Path(tmpdir),
                console=console,
                project_cfg=cfg,
                approve_all=False,
            )
            result = executor.execute(Action(type="RUN", payload={"command": "echo hello"}), step=1)
            assert "hello" in result["result"]
            console.input.assert_not_called()
