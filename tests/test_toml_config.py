"""Tests for TOML config loader."""

import tempfile
from pathlib import Path

from agent2048.toml_config import (
    AgentConfig,
    ProjectConfig,
    get_project_config,
    is_action_allowed,
    load_toml_config,
)


def test_load_default_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "missing.toml"
        cfg = load_toml_config(path)
        assert isinstance(cfg, AgentConfig)
        assert cfg.model is None
        assert cfg.global_project.trust_level == "ask"


def test_load_config_with_permissions():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "config.toml"
        path.write_text(
            """
model = "gpt-4o-mini"
provider = "openai"
trust_level = "auto"

[permissions]
allow = ["READ", "WRITE"]
deny = ["RUN(rm"]

[projects."/tmp/test"]
trust_level = "ask"
allow = ["READ"]
""",
            encoding="utf-8",
        )
        cfg = load_toml_config(path)
        assert cfg.model == "gpt-4o-mini"
        assert cfg.global_project.trust_level == "auto"
        assert "WRITE" in cfg.global_project.allowed_patterns
        assert "RUN(rm" in cfg.global_project.denied_patterns

        project_cfg = get_project_config(Path("/tmp/test/subdir"), cfg)
        assert project_cfg.trust_level == "ask"


def test_is_action_allowed():
    auto_cfg = ProjectConfig(trust_level="auto")
    assert is_action_allowed("WRITE", {"path": "x.py"}, auto_cfg)

    deny_cfg = ProjectConfig(trust_level="deny")
    assert not is_action_allowed("READ", {"path": "x.py"}, deny_cfg)

    ask_cfg = ProjectConfig(trust_level="ask")
    assert not is_action_allowed("WRITE", {"path": "x.py"}, ask_cfg)

    # File patterns match against the path, not the action type.
    allowed_cfg = ProjectConfig(trust_level="ask", allowed_patterns=["*.py"])
    assert is_action_allowed("WRITE", {"path": "x.py"}, allowed_cfg)
    assert not is_action_allowed("WRITE", {"path": "x.txt"}, allowed_cfg)

    # Run patterns match against the command string.
    run_cfg = ProjectConfig(trust_level="ask", allowed_patterns=["ls"], denied_patterns=["sudo"])
    assert is_action_allowed("RUN", {"command": "ls"}, run_cfg)
    assert not is_action_allowed("RUN", {"command": "sudo rm"}, run_cfg)
    assert not is_action_allowed("RUN", {"command": "cat secret.txt"}, run_cfg)
