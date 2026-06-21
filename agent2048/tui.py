"""Interactive TUI control panel for Agent2048.

A quick control panel inspired by Codex CLI / Claude Code. Uses prompt_toolkit
for command completion, history, and shortcuts. People don't like typing extra
letters.
"""

import os
from pathlib import Path

from dotenv import dotenv_values
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.table import Table

from agent2048.config import settings
from agent2048.theme import WAYBAR_THEME


COMMAND_HELP = {
    "ask": "Run a one-shot task: ask <task>",
    "chat": "Enter interactive chat mode",
    "stats": "Show memory stats: stats [--db <db>]",
    "memory": "Search memory: memory <query>",
    "dive": "Dive into memory item: dive <item_id>",
    "providers": "List providers",
    "models": "Show models: models [--provider <name>]",
    "use": "Activate provider: use <provider> [key] [--model <id>]",
    "model": "Set active model: model <id_or_number>",
    "set-key": "Save API key: set-key <key>",
    "project": "Project settings: project [--trust-level auto|ask|deny]",
    "init": "Create default config",
    "help": "Show this help",
    "exit": "Exit TUI",
}


def run_tui(db: str = "./memory.db", workdir: Path = Path(".")) -> None:
    console = Console(theme=WAYBAR_THEME)
    history_path = Path.home() / ".config" / "agent2048" / "history"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    completer = NestedCompleter.from_nested_dict(
        {
            "ask": None,
            "chat": {"--auto": None},
            "stats": {"--db": None, "--include-merged": None},
            "memory": None,
            "dive": None,
            "providers": None,
            "models": None,
            "use": {"--model": None},
            "model": None,
            "set-key": None,
            "project": {"--trust-level": {"auto": None, "ask": None, "deny": None}},
            "init": None,
            "help": None,
            "exit": None,
        }
    )

    session = PromptSession(
        "agent2048> ",
        history=FileHistory(str(history_path)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
    )

    # Track last shown model list for `model <number>` selection.
    last_models: list[str] = []

    console.print("[agent.accent]Agent2048 Control Panel[/agent.accent]")
    console.print("[agent.muted]Tab to complete, ↑↓ for history, /help for commands[/agent.muted]")

    while True:
        try:
            text = session.prompt()
        except (EOFError, KeyboardInterrupt):
            break

        text = text.strip()
        if not text:
            continue

        parts = text.split()
        cmd = parts[0]
        args = parts[1:]

        if cmd == "exit":
            break
        if cmd == "help":
            for name, desc in COMMAND_HELP.items():
                console.print(f"[agent.accent]{name:12}[/agent.accent] [agent.text]{desc}[/agent.text]")
            continue

        import subprocess
        import sys

        base_cmd = [sys.executable, "-m", "agent2048.cli"]
        cwd = str(workdir.parent if workdir != Path(".") else Path.cwd())

        if cmd == "ask":
            if not args:
                console.print("[agent.danger]Usage: ask <task> [--auto|--ask][/agent.danger]")
                continue
            # Extract flags
            auto_flag = False
            ask_flag = False
            task_parts = []
            for arg in args:
                if arg == "--auto":
                    auto_flag = True
                elif arg == "--ask":
                    ask_flag = True
                else:
                    task_parts.append(arg)
            if not task_parts:
                console.print("[agent.danger]Usage: ask <task> [--auto|--ask][/agent.danger]")
                continue
            task = " ".join(task_parts)
            cmd_args = []
            if auto_flag:
                cmd_args.append("--auto")
            if ask_flag:
                cmd_args.append("--ask")
            full = base_cmd + ["ask", task, "--db", db, "--workdir", str(workdir)] + cmd_args
        elif cmd == "chat":
            full = base_cmd + ["chat", "--db", db, "--workdir", str(workdir)]
        elif cmd == "stats":
            full = base_cmd + ["stats", "--db", db] + args
        elif cmd == "memory":
            if not args:
                console.print("[agent.danger]Usage: memory <query>[/agent.danger]")
                continue
            full = base_cmd + ["memory", " ".join(args), "--db", db]
        elif cmd == "dive":
            if not args:
                console.print("[agent.danger]Usage: dive <item_id>[/agent.danger]")
                continue
            full = base_cmd + ["dive", args[0], "--db", db]
        elif cmd == "providers":
            full = base_cmd + ["providers"] + args
        elif cmd == "models":
            full = base_cmd + ["models"] + args
            try:
                result = subprocess.run(full, cwd=cwd, capture_output=True, text=True, timeout=30)
                console.print(result.stdout)
                lines = result.stdout.strip().split("\n")
                last_models = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("•"):
                        last_models.append(stripped[1:].strip())
                continue
            except Exception as e:
                console.print(f"[agent.danger]Error: {e}[/agent.danger]")
                continue
        elif cmd == "use":
            if not args:
                console.print("[agent.danger]Usage: use <provider> [key] [--model <id>][/agent.danger]")
                continue

            provider_name = args[0]
            # Detect if second arg is a key (not --model)
            api_key = ""
            extra_args = []
            if len(args) > 1 and not args[1].startswith("--"):
                api_key = args[1]
                extra_args = args[2:]
            else:
                extra_args = args[1:]

            # If no key provided, try .env
            if not api_key:
                env_vars = dotenv_values(".env")
                api_key = env_vars.get("OPENAI_API_KEY", "")

            if not api_key or api_key.lower().startswith("sk-your") or api_key.lower().startswith("fe-your"):
                console.print("[agent.danger]No API key. Usage: use <provider> <key>[/agent.danger]")
                console.print("[agent.muted]Or run: set-key <key> first[/agent.muted]")
                continue

            # Save key first, then activate provider
            subprocess.run(base_cmd + ["set-key", api_key], cwd=cwd, capture_output=True)

            use_args = ["use", provider_name, "--key", api_key] + extra_args
            full = base_cmd + use_args
            try:
                result = subprocess.run(full, cwd=cwd, capture_output=True, text=True, timeout=30)
                console.print(result.stdout)
                # Parse models from output for `model <number>` support
                last_models = []
                for line in result.stdout.strip().split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("•"):
                        last_models.append(stripped[1:].strip())
                if last_models:
                    console.print(f"[agent.muted]→ Use: model <number> or model <id> to select[/agent.muted]")
                continue
            except Exception as e:
                console.print(f"[agent.danger]Error: {e}[/agent.danger]")
                continue
        elif cmd == "model":
            if not args:
                console.print("[agent.danger]Usage: model <id_or_number>[/agent.danger]")
                continue
            # Support `model 1`, `model 2` etc. using last shown list
            model_arg = args[0]
            if model_arg.isdigit() and last_models:
                idx = int(model_arg) - 1
                if 0 <= idx < len(last_models):
                    model_arg = last_models[idx]
                else:
                    console.print(f"[agent.danger]Invalid number. Use 1-{len(last_models)}[/agent.danger]")
                    continue
            full = base_cmd + ["model", model_arg]
        elif cmd == "set-key":
            if not args:
                console.print("[agent.danger]Usage: set-key <api_key>[/agent.danger]")
                continue
            full = base_cmd + ["set-key", args[0]]
        elif cmd == "project":
            full = base_cmd + ["project", "--workdir", str(workdir)] + args
        elif cmd == "init":
            full = base_cmd + ["init"] + args
        else:
            console.print(f"[agent.danger]Unknown command: {cmd}[/agent.danger]")
            continue

        try:
            subprocess.run(full, cwd=cwd)
        except Exception as e:
            console.print(f"[agent.danger]Error running command: {e}[/agent.danger]")

    console.print("[agent.muted]→ bye[/agent.muted]")
