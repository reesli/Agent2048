"""Agent actions and their execution."""

import json
import subprocess
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console

from agent2048.logging_config import logger
from agent2048.memory import MemoryStore
from agent2048.toml_config import ProjectConfig, is_action_allowed


class Action(BaseModel):
    type: Literal["THINK", "READ", "WRITE", "RUN", "MEMORY", "DONE"] = Field(..., alias="type")
    payload: dict[str, Any] = Field(default_factory=dict, alias="payload")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ActionExecutor:
    def __init__(
        self,
        memory: MemoryStore,
        workdir: Path,
        console: Console | None = None,
        project_cfg: ProjectConfig | None = None,
        approve_all: bool = False,
    ):
        self.memory = memory
        self.workdir = workdir
        self.console = console
        self.project_cfg = project_cfg or ProjectConfig()
        self.approve_all = approve_all

    def _ask_approval(self, action: Action) -> bool:
        """Ask the user for approval before executing a sensitive action."""
        if self.approve_all or self.console is None:
            return True
        if action.type in ("THINK", "MEMORY", "DONE"):
            return True
        if is_action_allowed(action.type, action.payload, self.project_cfg):
            return True

        preview = json.dumps(action.model_dump(), ensure_ascii=False, indent=2)
        self.console.print(f"[agent.warn]Approve {action.type}?[/agent.warn]")
        self.console.print(preview)
        answer = self.console.input("[agent.accent]y/n/always:[/agent.accent] ").strip().lower()
        if answer == "always":
            self.approve_all = True
            return True
        return answer in ("y", "yes", "")

    def execute(self, action: Action, step: int) -> dict[str, Any]:
        """Execute a single action and return a result dictionary."""
        if not self._ask_approval(action):
            return {
                "type": action.type,
                "display": f"[agent.danger]🚫 Denied {action.type}[/agent.danger]",
                "result": "Denied by user",
            }

        t = action.type
        p = action.payload
        if t == "THINK":
            return {"type": t, "display": f"[agent.highlight]🤔 {p.get('thought', '')}[/agent.highlight]", "result": p.get("thought", "")}
        if t == "READ":
            return self._read(p)
        if t == "WRITE":
            return self._write(p)
        if t == "RUN":
            return self._run(p)
        if t == "MEMORY":
            return self._memory(p)
        if t == "DONE":
            return {"type": t, "display": f"[agent.success]✅ {p.get('result', '')}[/agent.success]", "result": p.get("result", "")}
        return {"type": t, "display": "[agent.danger]❓ Unknown action[/agent.danger]", "result": "unknown"}

    def _read(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_path(payload.get("path", ""))
        if path is None:
            return {"type": "READ", "display": "[agent.danger]📄 Read denied: path outside workdir[/agent.danger]", "result": "Path outside workdir"}
        if not path.exists():
            return {"type": "READ", "display": f"[agent.danger]📄 Read failed: {path} not found[/agent.danger]", "result": "File not found"}
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return {"type": "READ", "display": f"[agent.info]📄 Read {path}[/agent.info]", "result": content[:2000]}
        except Exception as e:
            return {"type": "READ", "display": f"[agent.danger]📄 Read failed: {e}[/agent.danger]", "result": str(e)}

    def _write(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_path(payload.get("path", ""))
        if path is None:
            return {"type": "WRITE", "display": "[agent.danger]✏️  Write denied: path outside workdir[/agent.danger]", "result": "Path outside workdir"}
        content = payload.get("content", "")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"type": "WRITE", "display": f"[agent.accent]✏️  Wrote {path}[/agent.accent]", "result": f"Wrote {len(content)} chars"}
        except Exception as e:
            return {"type": "WRITE", "display": f"[agent.danger]✏️  Write failed: {e}[/agent.danger]", "result": str(e)}


    def _run(self, payload: dict[str, Any]) -> dict[str, Any]:
        command = payload.get("command", "")
        description = payload.get("description", command)
        if not command:
            return {"type": "RUN", "display": "[agent.warn]⚙️ Empty command[/agent.warn]", "result": "No command"}
        blocked_patterns = [
            "rm -rf /", "rm -rf ~", "rm -rf $HOME", "rm -rf --no-preserve-root",
            "rm -rf /*", "rm -fr /", "rm -fr ~",
            "mkfs", "dd if=/dev/zero", "dd if=/dev/random",
            ":(){ :|:& };:", "fork bomb",
            "chmod 000", "chmod -R 000",
            "shutdown", "reboot", "halt", "init 0",
            "mv / ", "cp /dev/null /",
        ]
        cmd_lower = command.lower()
        for b in blocked_patterns:
            if b.lower() in cmd_lower:
                return {"type": "RUN", "display": "[agent.danger]🚫 Blocked dangerous command[/agent.danger]", "result": "Blocked"}
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = f"exit={result.returncode}\n{result.stdout}\n{result.stderr}".strip()
            return {"type": "RUN", "display": f"[agent.info]⚙️ {description}[/agent.info]", "result": output[:2000]}
        except Exception as e:
            return {"type": "RUN", "display": f"[agent.danger]⚙️ Run failed: {e}[/agent.danger]", "result": str(e)}

    def _memory(self, payload: dict[str, Any]) -> dict[str, Any]:
        content = payload.get("content", "")
        tag = payload.get("tag", "general")
        item = self.memory.add(content, level=1, tag=tag)
        return {
            "type": "MEMORY",
            "display": f"[agent.accent2]🧠 Saved memory [L{item.level}] ({item.tag or 'general'}): {item.content[:80]}...[/agent.accent2]",
            "result": f"Saved as {item.id} at level {item.level}",
        }

    def _resolve_path(self, raw: str) -> Path | None:
        raw = raw.strip()
        path = Path(raw)
        if not path.is_absolute():
            path = self.workdir / path
        resolved = path.resolve()
        workdir_resolved = self.workdir.resolve()
        try:
            resolved.relative_to(workdir_resolved)
        except ValueError:
            return None
        return resolved


def parse_action(text: str) -> Action:
    """Parse the LLM output into an Action object.

    Handles plain JSON, markdown fences, and leading/trailing prose.
    """
    text = text.strip()

    # Try fenced json block first.
    if "```" in text:
        parts = text.split("```")
        for part in parts[1:]:
            candidate = part.strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            try:
                data = json.loads(candidate)
                return Action(**data)
            except Exception as e:
                logger.debug("Fenced JSON parse failed: %s", e)
                continue

    # Try to find the first JSON object in the text.
    start = text.find("{")
    if start != -1:
        # Match braces, respecting string literals and escapes.
        depth = 0
        in_string = False
        escape = False
        end = None
        for i, ch in enumerate(text[start:], start=start):
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end:
            try:
                data = json.loads(text[start:end])
                return Action(**data)
            except Exception as e:
                logger.debug("Brace-matched JSON parse failed: %s", e)

    # Fallback to full text.
    data = json.loads(text)
    return Action(**data)
