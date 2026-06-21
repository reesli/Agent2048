"""TOML configuration loader inspired by Codex CLI and Claude CLI.

Reads ~/.config/agent2048/config.toml for project-specific settings:
- model / provider
- trust_level (auto / ask / deny)
- permissions allow/deny lists
- project overrides
"""

import fnmatch
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import tomli_w


@dataclass
class ProjectConfig:
    trust_level: str = "ask"  # "auto", "ask", "deny"
    allowed_patterns: list[str] = field(default_factory=list)
    denied_patterns: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    model: str | None = None
    provider: str | None = None
    base_url: str | None = None
    reasoning_effort: str | None = None
    global_project: ProjectConfig = field(default_factory=ProjectConfig)
    projects: dict[str, ProjectConfig] = field(default_factory=dict)


def load_toml_config(path: Path | None = None) -> AgentConfig:
    """Load TOML config from ~/.config/agent2048/config.toml or given path."""
    if path is None:
        path = Path.home() / ".config" / "agent2048" / "config.toml"

    if not path.exists():
        return AgentConfig()

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return AgentConfig()

    cfg = AgentConfig(
        model=data.get("model"),
        provider=data.get("provider"),
        base_url=data.get("base_url"),
        reasoning_effort=data.get("reasoning_effort"),
    )

    if "permissions" in data:
        perm = data["permissions"]
        cfg.global_project = ProjectConfig(
            trust_level=data.get("trust_level", "ask"),
            allowed_patterns=perm.get("allow", []),
            denied_patterns=perm.get("deny", []),
        )

    for project_path, project_data in data.get("projects", {}).items():
        cfg.projects[project_path] = ProjectConfig(
            trust_level=project_data.get("trust_level", "ask"),
            allowed_patterns=project_data.get("allow", []),
            denied_patterns=project_data.get("deny", []),
        )

    return cfg


def get_project_config(workdir: Path, cfg: AgentConfig | None = None) -> ProjectConfig:
    """Get the project-specific config for a working directory."""
    if cfg is None:
        cfg = load_toml_config()
    resolved = str(workdir.resolve())
    for project_path, project_cfg in cfg.projects.items():
        if resolved == project_path or resolved.startswith(project_path + "/"):
            return project_cfg
    return cfg.global_project


def _matches(pattern: str, target: str) -> bool:
    """Match a pattern against a target. Supports glob via fnmatch."""
    if any(c in pattern for c in "*?["):
        return fnmatch.fnmatch(target, pattern)
    return pattern in target


def is_action_allowed(
    action_type: str, payload: dict[str, Any], project_cfg: ProjectConfig
) -> bool:
    """Check if an action is allowed under the project's permission rules.

    For file actions (READ/WRITE) the path is checked against allow/deny
    patterns. For RUN actions the command string is checked. Other actions
    are matched against a serialized representation.
    """
    if project_cfg.trust_level == "auto":
        return True
    if project_cfg.trust_level == "deny":
        return False

    if action_type in ("READ", "WRITE"):
        target = payload.get("path", "")
    elif action_type == "RUN":
        target = payload.get("command", "")
    else:
        target = f"{action_type}({payload})"

    for pattern in project_cfg.denied_patterns:
        if _matches(pattern, target):
            return False

    if not project_cfg.allowed_patterns:
        # ask mode: no explicit allow list means ask for everything.
        return False

    for pattern in project_cfg.allowed_patterns:
        if _matches(pattern, target):
            return True

    return False


def save_toml_config(cfg: AgentConfig, path: Path | None = None) -> None:
    """Save the current config to TOML file."""
    if path is None:
        path = Path.home() / ".config" / "agent2048" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {}
    if cfg.model:
        data["model"] = cfg.model
    if cfg.provider:
        data["provider"] = cfg.provider
    if cfg.base_url:
        data["base_url"] = cfg.base_url
    if cfg.reasoning_effort:
        data["reasoning_effort"] = cfg.reasoning_effort

    data["trust_level"] = cfg.global_project.trust_level
    data["permissions"] = {
        "allow": cfg.global_project.allowed_patterns,
        "deny": cfg.global_project.denied_patterns,
    }

    data["projects"] = {}
    for project_path, project_cfg in cfg.projects.items():
        data["projects"][project_path] = {
            "trust_level": project_cfg.trust_level,
            "allow": project_cfg.allowed_patterns,
            "deny": project_cfg.denied_patterns,
        }

    with open(path, "wb") as f:
        tomli_w.dump(data, f)


def set_project_trust_level(
    workdir: Path,
    trust_level: str,
    path: Path | None = None,
    allowed_patterns: list[str] | None = None,
    denied_patterns: list[str] | None = None,
) -> None:
    """Set or update the trust level for a specific project directory."""
    cfg = load_toml_config(path)
    resolved = str(workdir.resolve())
    existing = cfg.projects.get(resolved, ProjectConfig())
    existing.trust_level = trust_level
    if allowed_patterns is not None:
        existing.allowed_patterns = allowed_patterns
    if denied_patterns is not None:
        existing.denied_patterns = denied_patterns
    cfg.projects[resolved] = existing
    save_toml_config(cfg, path)
