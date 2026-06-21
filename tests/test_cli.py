"""Tests for CLI commands."""

import pytest
import typer

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from agent2048.cli import app, _require_api_key

runner = CliRunner()


def test_require_api_key_missing() -> None:
    with patch("agent2048.cli.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        with pytest.raises(typer.Exit):
            _require_api_key()


def test_set_key_updates_env(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("MODEL=old\n")
    result = runner.invoke(app, ["set-key", "sk_test_key", "--env-path", str(env_path)])
    assert result.exit_code == 0
    assert "API key saved" in result.stdout
    assert "OPENAI_API_KEY='sk_test_key'" in env_path.read_text()


def test_model_updates_env(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=old\n")
    result = runner.invoke(app, ["model", "gpt-4o", "--env-path", str(env_path)])
    assert result.exit_code == 0
    assert "Active model set to gpt-4o" in result.stdout
    assert "MODEL='gpt-4o'" in env_path.read_text()


def test_models_command_lists_models(monkeypatch: object) -> None:
    from agent2048.llm import LLMClient

    def fake_list_models(self: LLMClient) -> list[str]:
        return ["model-a", "model-b"]

    monkeypatch.setattr(LLMClient, "list_models", fake_list_models)
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "model-a" in result.stdout
    assert "model-b" in result.stdout


def test_models_command_with_provider(monkeypatch: object) -> None:
    from agent2048 import providers as providers_module

    def fake_list_models(name: str) -> list[str]:
        return ["provider-model-a"]

    monkeypatch.setattr(providers_module, "list_models", fake_list_models)
    result = runner.invoke(app, ["models", "--provider", "openai"])
    assert result.exit_code == 0
    assert "Preset models" in result.stdout
    assert "provider-model-a" in result.stdout


def test_models_command_fallback(monkeypatch: object) -> None:
    from agent2048.llm import LLMClient

    def fake_list_models(self: LLMClient) -> list[str]:
        raise RuntimeError("API down")

    monkeypatch.setattr(LLMClient, "list_models", fake_list_models)
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "Live API list failed" in result.stdout


def test_use_updates_env_and_shows_models(monkeypatch: object, tmp_path: Path) -> None:
    from agent2048.llm import LLMClient

    env_path = tmp_path / ".env"
    env_path.write_text("MODEL=old\n")

    def fake_list_models(self: LLMClient) -> list[str]:
        return ["openrouter-model-a", "openrouter-model-b"]

    monkeypatch.setattr(LLMClient, "list_models", fake_list_models)
    result = runner.invoke(app, ["use", "openrouter", "--key", "sk_test", "--env-path", str(env_path)])
    assert result.exit_code == 0
    assert "Activated provider: openrouter" in result.stdout
    assert "openrouter-model-a" in result.stdout
    env_text = env_path.read_text()
    assert "OPENAI_API_KEY='sk_test'" in env_text
    assert "OPENAI_BASE_URL" in env_text


def test_use_with_model_option(monkeypatch: object, tmp_path: Path) -> None:
    from agent2048.llm import LLMClient

    env_path = tmp_path / ".env"
    env_path.write_text("MODEL=old\n")

    def fake_list_models(self: LLMClient) -> list[str]:
        return ["nvidia-model-a", "nvidia-model-b"]

    monkeypatch.setattr(LLMClient, "list_models", fake_list_models)
    result = runner.invoke(
        app,
        ["use", "nvidia", "--key", "sk_test", "--model", "meta/llama-4-maverick", "--env-path", str(env_path)],
    )
    assert result.exit_code == 0
    assert "model: meta/llama-4-maverick" in result.stdout
    assert "MODEL='meta/llama-4-maverick'" in env_path.read_text()


def test_use_unknown_provider(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    result = runner.invoke(app, ["use", "unknown-provider", "--key", "sk_test", "--env-path", str(env_path)])
    assert result.exit_code == 1
    assert "Unknown provider" in result.stdout


def test_project_allow_deny_patterns(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    result = runner.invoke(
        app,
        [
            "project",
            "--trust-level",
            "ask",
            "--allow",
            "*.py",
            "--deny",
            "*.secret",
            "--workdir",
            str(project_dir),
            "--config-path",
            str(config_path),
        ],
    )
    assert result.exit_code == 0
    assert "Updated" in result.stdout
    assert "*.py" in result.stdout
    assert "*.secret" in result.stdout

    from agent2048.toml_config import load_toml_config, get_project_config

    cfg = load_toml_config(config_path)
    project_cfg = get_project_config(project_dir, cfg)
    assert project_cfg.trust_level == "ask"
    assert "*.py" in project_cfg.allowed_patterns
    assert "*.secret" in project_cfg.denied_patterns


def test_project_show(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    result = runner.invoke(
        app,
        [
            "project",
            "--show",
            "--workdir",
            str(project_dir),
            "--config-path",
            str(config_path),
        ],
    )
    assert result.exit_code == 0
    assert "Project:" in result.stdout
    assert "trust_level:" in result.stdout


def test_project_invalid_trust_level(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    result = runner.invoke(
        app,
        [
            "project",
            "--trust-level",
            "invalid",
            "--workdir",
            str(project_dir),
            "--config-path",
            str(config_path),
        ],
    )
    assert result.exit_code == 1
    assert "trust_level must be" in result.stdout


def test_stats_command(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    result = runner.invoke(app, ["stats", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "Memory Pyramid" in result.stdout
    assert "Total" in result.stdout


def test_stats_include_merged(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    result = runner.invoke(app, ["stats", "--db", str(db_path), "--include-merged"])
    assert result.exit_code == 0
    assert "including merged details" in result.stdout


def test_clear_command_confirms(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    result = runner.invoke(app, ["clear", "--db", str(db_path)], input="y\n")
    assert result.exit_code == 0
    assert "Memory cleared" in result.stdout


def test_clear_command_skip_confirm(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    result = runner.invoke(app, ["clear", "--db", str(db_path), "--yes"])
    assert result.exit_code == 0
    assert "Memory cleared" in result.stdout


def test_memory_command(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    result = runner.invoke(app, ["memory", "hello", "--db", str(db_path)])
    assert result.exit_code == 0


def test_dive_command_item_not_found(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    result = runner.invoke(app, ["dive", "999", "--db", str(db_path)])
    assert result.exit_code == 1
    assert "Item not found" in result.stdout


def test_providers_command_lists_all() -> None:
    result = runner.invoke(app, ["providers"])
    assert result.exit_code == 0
    assert "openai" in result.stdout


def test_providers_command_with_name() -> None:
    result = runner.invoke(app, ["providers", "openai"])
    assert result.exit_code == 0
    assert "openai" in result.stdout


def test_providers_command_unknown_provider() -> None:
    result = runner.invoke(app, ["providers", "unknown-provider"])
    assert result.exit_code == 1
    assert "Unknown provider" in result.stdout


def test_init_command(tmp_path: Path, monkeypatch: object) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("agent2048.cli.Path.home", lambda: tmp_path)
    result = runner.invoke(app, ["init", "--path", str(config_path)])
    assert result.exit_code == 0
    assert "Created config" in result.stdout
    assert config_path.exists()


def test_init_command_already_exists(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("model = \"x\"\n")
    result = runner.invoke(app, ["init", "--path", str(config_path)])
    assert result.exit_code == 0
    assert "Config already exists" in result.stdout


def test_ask_command_success(monkeypatch: object, tmp_path: Path) -> None:
    from agent2048.agent import Agent

    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    def fake_run(self: Agent, task: str) -> str:
        return f"Done: {task}"

    monkeypatch.setattr(Agent, "run", fake_run)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)
    result = runner.invoke(app, ["ask", "test task", "--workdir", str(workdir), "--db", str(db_path)])
    assert result.exit_code == 0
    assert "Done: test task" in result.stdout


def test_ask_command_error(monkeypatch: object, tmp_path: Path) -> None:
    from agent2048.agent import Agent

    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    def fake_run(self: Agent, task: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(Agent, "run", fake_run)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)
    result = runner.invoke(app, ["ask", "test task", "--workdir", str(workdir), "--db", str(db_path)])
    assert result.exit_code == 1
    assert "Agent error" in result.stdout


def test_ask_command_ask_approve(monkeypatch: object, tmp_path: Path) -> None:
    from agent2048.agent import Agent

    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    def fake_run(self: Agent, task: str) -> str:
        return f"Done: {task}"

    monkeypatch.setattr(Agent, "run", fake_run)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)
    result = runner.invoke(app, ["ask", "test task", "--workdir", str(workdir), "--db", str(db_path), "--ask"])
    assert result.exit_code == 0
    assert "Done: test task" in result.stdout


def test_chat_command_exit(monkeypatch: object, tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    fake_console = MagicMock()
    fake_console.input.side_effect = ["/exit"]
    monkeypatch.setattr("agent2048.cli.console", fake_console)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)

    result = runner.invoke(app, ["chat", "--workdir", str(workdir), "--db", str(db_path)])
    assert result.exit_code == 0


def test_chat_command_save_and_search(monkeypatch: object, tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    fake_console = MagicMock()
    fake_console.input.side_effect = ["/save test fact", "/search test", "/exit"]
    monkeypatch.setattr("agent2048.cli.console", fake_console)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)

    result = runner.invoke(app, ["chat", "--workdir", str(workdir), "--db", str(db_path)])
    assert result.exit_code == 0


def test_chat_command_do_task(monkeypatch: object, tmp_path: Path) -> None:
    from agent2048.agent import Agent

    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    fake_console = MagicMock()
    fake_console.input.side_effect = ["/do test task", "/exit"]
    monkeypatch.setattr("agent2048.cli.console", fake_console)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)
    monkeypatch.setattr(Agent, "run", lambda self, task: None)

    result = runner.invoke(app, ["chat", "--workdir", str(workdir), "--db", str(db_path)])
    assert result.exit_code == 0


def test_chat_command_streaming_response(monkeypatch: object, tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    fake_console = MagicMock()
    fake_console.input.side_effect = ["hello", "/exit"]
    monkeypatch.setattr("agent2048.cli.console", fake_console)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)

    fake_llm = MagicMock()
    fake_llm.chat_stream.return_value = iter(["Hi", " there"])
    monkeypatch.setattr("agent2048.cli.llm", fake_llm)

    result = runner.invoke(app, ["chat", "--workdir", str(workdir), "--db", str(db_path)])
    assert result.exit_code == 0


def test_chat_command_eof(monkeypatch: object, tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    fake_console = MagicMock()
    fake_console.input.side_effect = [EOFError()]
    monkeypatch.setattr("agent2048.cli.console", fake_console)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)

    result = runner.invoke(app, ["chat", "--workdir", str(workdir), "--db", str(db_path)])
    assert result.exit_code == 0


def test_tui_command(monkeypatch: object, tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    workdir = tmp_path / "project"
    workdir.mkdir()

    def fake_run_tui(*, db: str, workdir: Path) -> None:
        return None

    monkeypatch.setattr("agent2048.cli.run_tui", fake_run_tui)
    monkeypatch.setattr("agent2048.cli._require_api_key", lambda: None)
    result = runner.invoke(app, ["tui", "--workdir", str(workdir), "--db", str(db_path)])
    assert result.exit_code == 0
