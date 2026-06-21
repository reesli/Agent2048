"""CLI entry point."""

from pathlib import Path

import openai
import typer
from rich.console import Console
from rich.table import Table

from agent2048.agent import Agent
from agent2048.config import settings
from agent2048.llm import llm
from agent2048.memory import MemoryStore
from agent2048.prompts import AGENT_SYSTEM, CHAT_SYSTEM
from agent2048 import providers as providers_module
from agent2048.providers import get_all_providers, get_env_for_provider, list_models
from agent2048.theme import WAYBAR_THEME
from agent2048.toml_config import (
    load_toml_config,
    get_project_config,
    set_project_trust_level,
    ProjectConfig,
)
from agent2048.tui import run_tui

app = typer.Typer(help="Agent2048 — CLI for AI agents with hierarchical memory")
console = Console(theme=WAYBAR_THEME)


def _require_api_key() -> None:
    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-your"):
        console.print(
            "[red]OPENAI_API_KEY is not set. Please copy .env.example to .env and add your key.[/red]"
        )
        raise typer.Exit(1)


@app.command()
def ask(
    task: str = typer.Argument(..., help="Task for the agent"),
    workdir: Path = typer.Option(Path("."), help="Project working directory"),
    db: str = typer.Option("./memory.db", help="Path to memory database"),
    auto: bool = typer.Option(False, "--auto", help="Auto-approve all actions (trust_level=auto)"),
    ask_approve: bool = typer.Option(False, "--ask", help="Ask for approval before every action (trust_level=ask)"),
):
    """Ask the agent to perform a task."""
    _require_api_key()
    settings.reload()
    llm.reload()
    workdir.mkdir(parents=True, exist_ok=True)
    memory = MemoryStore(db_path=db)

    cfg = load_toml_config()
    project_cfg = get_project_config(workdir, cfg)
    approve_all = not ask_approve if ask_approve else (auto or project_cfg.trust_level == "auto")

    agent = Agent(memory=memory, workdir=workdir, console=console, project_cfg=project_cfg, approve_all=approve_all)
    try:
        result = agent.run(task)
        console.print(result)
    except Exception as e:
        console.print(f"[red]Agent error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats(
    db: str = typer.Option("./memory.db", help="Path to memory database"),
    include_merged: bool = typer.Option(False, "--include-merged", help="Include merged items in counts"),
):
    """Show memory statistics."""
    memory = MemoryStore(db_path=db)
    counts = memory.stats(include_merged=include_merged)
    total = sum(counts.values())

    title = "Memory Pyramid (2048)"
    if include_merged:
        title += " — including merged details"
    table = Table(title=title)
    table.add_column("Level", justify="center", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Count", justify="right", style="green")

    names = {1: "Fact", 2: "Pattern", 3: "Concept", 4: "Principle"}
    styles = {1: "agent.info", 2: "agent.accent2", 3: "agent.accent", 4: "agent.highlight"}
    for level in sorted(counts.keys()):
        num = int(level.split("_")[1])
        table.add_row(
            f"[{styles.get(num, 'agent.text')}]{num}[/]",
            f"[{styles.get(num, 'agent.text')}]{names.get(num, 'Level ' + str(num))}[/]",
            f"[{styles.get(num, 'agent.text')}]{counts[level]}[/]",
        )

    table.add_row("—", "Total", f"[agent.success]{total}[/]")
    console.print(table)


@app.command()
def clear(
    db: str = typer.Option("./memory.db", help="Path to memory database"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
):
    """Clear all memory."""
    if not yes:
        typer.confirm("Delete all memory?", abort=True)
    memory = MemoryStore(db_path=db)
    memory.clear()
    console.print("Memory cleared.")


@app.command()
def memory(
    query: str = typer.Argument(..., help="Search query"),
    db: str = typer.Option("./memory.db", help="Path to memory database"),
    top_k: int = typer.Option(5, help="Number of results"),
):
    """Search memory."""
    _require_api_key()
    store = MemoryStore(db_path=db)
    items = store.search(query, top_k=top_k)
    for item in items:
        styles = {1: "agent.info", 2: "agent.accent2", 3: "agent.accent", 4: "agent.highlight"}
        style = styles.get(item.level, "agent.text")
        console.print(f"[{style}][L{item.level}][/] ({item.tag or 'general'}) {item.content[:120]}... [agent.muted]({item.id})[/]")


@app.command()
def dive(
    item_id: str = typer.Argument(..., help="Memory item ID to explore"),
    db: str = typer.Option("./memory.db", help="Path to memory database"),
):
    """Dive into the details of a memory item (soft merge lineage)."""
    store = MemoryStore(db_path=db)
    lineage = store.get_lineage(item_id)
    if not lineage:
        console.print("[agent.danger]Item not found.[/agent.danger]")
        raise typer.Exit(1)
    styles = {1: "agent.info", 2: "agent.accent2", 3: "agent.accent", 4: "agent.highlight"}
    for item in lineage:
        status = "merged" if item.merged_into else "active"
        style = styles.get(item.level, "agent.text")
        console.print(f"[{style}][L{item.level} | {status}][/] ({item.tag or 'general'}) {item.content[:160]}...")


@app.command()
def providers(
    name: str | None = typer.Argument(None, help="Provider name to show models for"),
):
    """List available providers and their models."""
    all_providers = get_all_providers()
    if name:
        if name not in all_providers:
            console.print(f"[agent.danger]Unknown provider: {name}[/agent.danger]")
            raise typer.Exit(1)
        models = list_models(name)
        console.print(f"[agent.accent]{name}[/agent.accent]")
        for m in models:
            console.print(f"  [agent.info]• {m}[/agent.info]")
        return

    for provider_name, cfg in sorted(all_providers.items()):
        models = cfg.get("models", [])
        console.print(f"[agent.accent]{provider_name}[/agent.accent] [agent.muted]{cfg.get('base_url', '')}[/agent.muted]")
        for m in models:
            console.print(f"  [agent.info]• {m}[/agent.info]")


@app.command()
def chat(
    db: str = typer.Option("./memory.db", help="Path to memory database"),
    workdir: Path = typer.Option(Path("."), help="Project working directory"),
    auto: bool = typer.Option(False, "--auto", help="Auto-approve tool actions in chat"),
):
    """Interactive chat mode with memory, streaming, and tools (/do <task>)."""
    _require_api_key()
    settings.reload()
    llm.reload()
    workdir.mkdir(parents=True, exist_ok=True)
    memory = MemoryStore(db_path=db)

    cfg = load_toml_config()
    project_cfg = get_project_config(workdir, cfg)
    approve_all = auto or project_cfg.trust_level == "auto"

    messages: list[dict[str, str]] = [{"role": "system", "content": CHAT_SYSTEM}]
    console.print("[agent.accent]Agent2048 chat mode[/agent.accent]")
    console.print("[agent.muted]/do <task> — run agent tools, /save <fact>, /search <query>, /exit[/agent.muted]")

    while True:
        try:
            user_input = console.input("[agent.accent]❯[/agent.accent] ")
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input.strip():
            continue

        if user_input.strip() == "/exit":
            break

        if user_input.strip().startswith("/save "):
            fact = user_input.strip()[6:].strip()
            if fact:
                item = memory.add(fact, level=1, tag="chat")
                console.print(f"[agent.success]→ saved [L{item.level}]: {item.content[:80]}...[/agent.success]")
            continue

        if user_input.strip().startswith("/search "):
            query = user_input.strip()[8:].strip()
            items = memory.search(query, top_k=5)
            for item in items:
                console.print(f"[agent.info][L{item.level}][/] {item.content[:120]}...")
            continue

        if user_input.strip().startswith("/do "):
            task = user_input.strip()[4:].strip()
            agent = Agent(memory=memory, workdir=workdir, console=console, project_cfg=project_cfg, approve_all=approve_all)
            try:
                agent.run(task)
            except Exception as e:
                console.print(f"[agent.danger]Agent error: {e}[/agent.danger]")
            continue

        # Retrieve relevant memory context.
        relevant = memory.search(user_input, top_k=3)
        context = "\n".join(
            f"[L{item.level} | {item.tag or 'general'}] {item.content}"
            for item in relevant
        )
        if context:
            user_input = f"Relevant memory context:\n{context}\n\nUser: {user_input}"

        messages.append({"role": "user", "content": user_input})

        console.print("[agent.accent]→[/agent.accent] ", end="")
        response_parts = []
        try:
            for chunk in llm.chat_stream(messages):
                console.print(chunk, end="")
                response_parts.append(chunk)
        except Exception as e:
            console.print()
            console.print(f"[agent.danger]API error: {e}[/agent.danger]")
            console.print(f"[agent.muted]Check: .env has correct OPENAI_API_KEY and OPENAI_BASE_URL for your provider.[/agent.muted]")
            messages.pop()
            continue
        console.print()

        response = "".join(response_parts)
        messages.append({"role": "assistant", "content": response})

    console.print("[agent.muted]→ chat ended[/agent.muted]")


@app.command()
def init(
    path: Path = typer.Option(Path.home() / ".config" / "agent2048" / "config.toml", help="Config path to create"),
):
    """Create a default user config file (~/.config/agent2048/config.toml)."""
    if path.exists():
        console.print(f"[agent.warn]Config already exists at {path}[/agent.warn]")
        raise typer.Exit(0)
    path.parent.mkdir(parents=True, exist_ok=True)
    default = """# Agent2048 user configuration (inspired by Codex CLI and Claude CLI)

model = "gpt-4o-mini"
provider = "openai"
# base_url = "https://api.openai.com/v1"
reasoning_effort = "medium"

# Global permissions: auto, ask, or deny
trust_level = "ask"

[permissions]
allow = [
    "READ",
    "WRITE",
    "RUN(python3",
    "RUN(pytest",
    "RUN(ls",
]
deny = [
    "RUN(rm -rf",
    "RUN(sudo",
    "RUN(mkfs",
]

# Per-project overrides
[projects."/home/liskil/hackaton"]
trust_level = "ask"
allow = [
    "READ",
    "WRITE",
    "RUN(python3",
    "RUN(pytest",
]
"""
    path.write_text(default, encoding="utf-8")
    console.print(f"[agent.success]Created config at {path}[/agent.success]")


@app.command()
def project(
    trust_level: str | None = typer.Option(None, "--trust-level", help="Set trust level: auto, ask, or deny"),
    allow: list[str] = typer.Option([], "--allow", help="Allow pattern (repeatable)"),
    deny: list[str] = typer.Option([], "--deny", help="Deny pattern (repeatable)"),
    workdir: Path = typer.Option(Path("."), help="Project directory"),
    config_path: Path = typer.Option(Path.home() / ".config" / "agent2048" / "config.toml", help="Config file path"),
    show: bool = typer.Option(False, "--show", help="Show current project config"),
):
    """Manage project-specific trust settings (like Codex CLI projects)."""
    cfg = load_toml_config(config_path)
    project_cfg = get_project_config(workdir, cfg)

    if show or (trust_level is None and not allow and not deny):
        console.print(f"[agent.accent]Project:[/agent.accent] {workdir.resolve()}")
        console.print(f"[agent.info]trust_level:[/agent.info] {project_cfg.trust_level}")
        console.print(f"[agent.info]allow:[/agent.info] {project_cfg.allowed_patterns}")
        console.print(f"[agent.info]deny:[/agent.info] {project_cfg.denied_patterns}")
        return

    if trust_level is not None and trust_level not in ("auto", "ask", "deny"):
        console.print("[agent.danger]trust_level must be auto, ask, or deny[/agent.danger]")
        raise typer.Exit(1)

    new_level = trust_level or project_cfg.trust_level
    new_allow = project_cfg.allowed_patterns
    new_deny = project_cfg.denied_patterns
    if allow:
        new_allow = list(dict.fromkeys(new_allow + allow))
    if deny:
        new_deny = list(dict.fromkeys(new_deny + deny))

    set_project_trust_level(workdir, new_level, config_path, allowed_patterns=new_allow, denied_patterns=new_deny)
    console.print(f"[agent.success]Updated {workdir.resolve()} project permissions[/agent.success]")
    console.print(f"[agent.info]trust_level:[/agent.info] {new_level}")
    console.print(f"[agent.info]allow:[/agent.info] {new_allow}")
    console.print(f"[agent.info]deny:[/agent.info] {new_deny}")


@app.command()
def tui(
    db: str = typer.Option("./memory.db", help="Path to memory database"),
    workdir: Path = typer.Option(Path("."), help="Project working directory"),
):
    """Interactive control panel with completions and shortcuts."""
    _require_api_key()
    run_tui(db=db, workdir=workdir)


@app.command()
def use(
    provider_name: str = typer.Argument(..., help="Provider name to activate"),
    api_key: str = typer.Option("", "--key", help="API key (prompted if not provided)"),
    model_id: str = typer.Option("", "--model", help="Model ID to activate (default: first preset model)"),
    env_path: Path = typer.Option(Path(".env"), help="Path to .env file"),
):
    """Activate a provider by updating .env and fetching its live models."""
    providers = get_all_providers()
    if provider_name not in providers:
        console.print(f"[agent.danger]Unknown provider: {provider_name}[/agent.danger]")
        available = ", ".join(sorted(providers.keys()))
        console.print(f"[agent.muted]Available: {available}[/agent.muted]")
        raise typer.Exit(1)

    cfg = providers[provider_name]
    base_url = cfg.get("base_url", "")
    preset_models = cfg.get("models", [""])
    model = model_id or preset_models[0]

    from dotenv import dotenv_values, set_key
    env_vars = dotenv_values(env_path)

    key = api_key or env_vars.get("OPENAI_API_KEY", "")
    key_was_prompted = False
    if not key or key.lower().startswith("sk-your") or key.lower().startswith("fe-your"):
        key = typer.prompt("Enter API key", hide_input=True, default="")
        key_was_prompted = True
        if not key:
            console.print("[agent.danger]API key is required[/agent.danger]")
            raise typer.Exit(1)
    set_key(env_path, "OPENAI_API_KEY", key)

    set_key(env_path, "OPENAI_BASE_URL", base_url)
    set_key(env_path, "MODEL", model)
    settings.reload()
    llm.reload()

    console.print(f"[agent.success]Activated provider: {provider_name}[/agent.success]")
    console.print(f"[agent.info]base_url:[/agent.info] {base_url}")
    console.print(f"[agent.info]model:[/agent.info] {model}")

    console.print("")
    models(provider="", limit=50)


@app.command()
def models(
    provider: str = typer.Option("", "--provider", help="Provider name (uses current if omitted)"),
    limit: int = typer.Option(50, "--limit", help="Maximum number of models to show"),
):
    """Fetch and list available models from the current provider API."""
    _require_api_key()
    settings.reload()
    llm.reload()
    provider_name = provider or providers_module.guess_provider_from_env()
    if provider:
        available = providers_module.list_models(provider)
        console.print(f"[agent.accent]Preset models for {provider_name}[/agent.accent]")
    else:
        try:
            available = llm.list_models()
            console.print(f"[agent.accent]Live models from {settings.openai_base_url}[/agent.accent]")
        except Exception as e:
            console.print(f"[agent.warn]Live API list failed: {e}[/agent.warn]")
            available = providers_module.list_models()
            console.print(f"[agent.accent]Preset models for {provider_name}[/agent.accent]")
    for m in available[:limit]:
        marker = "[agent.success]•[/agent.success]" if m == settings.model else "[agent.info]•[/agent.info]"
        console.print(f"{marker} {m}")


@app.command()
def set_key(
    api_key: str = typer.Argument(..., help="API key to save"),
    env_path: Path = typer.Option(Path(".env"), help="Path to .env file"),
):
    """Save API key to .env."""
    from dotenv import set_key
    set_key(env_path, "OPENAI_API_KEY", api_key)
    console.print(f"[agent.success]API key saved to {env_path}[/agent.success]")


@app.command()
def model(
    model_id: str = typer.Argument(..., help="Model ID to set as default"),
    env_path: Path = typer.Option(Path(".env"), help="Path to .env file"),
):
    """Set the active model in .env."""
    from dotenv import set_key
    set_key(env_path, "MODEL", model_id)
    console.print(f"[agent.success]Active model set to {model_id}[/agent.success]")


if __name__ == "__main__":
    app()

