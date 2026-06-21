"""Real compression benchmark using the live agent.

Runs a sequence of similar tasks and compares:
- the raw token log of all agent interactions
- the compressed hierarchical memory

Requires a configured API key in .env.
"""

import tempfile
from pathlib import Path

from rich.console import Console
from rich.table import Table

from agent2048.agent import Agent
from agent2048.memory import MemoryStore

console = Console()


def run_benchmark(n_tasks: int = 4):
    tasks = [
        "Create a simple Python CLI habit tracker with add, list, and done commands. Use a JSON file for storage.",
        "Create a simple Python CLI todo list app with add, list, and done commands. Store tasks in a JSON file.",
        "Create a simple Python CLI notes app with add, list, and delete commands. Store notes in a JSON file.",
        "Create a simple Python CLI expense tracker with add, list, and total commands. Store expenses in a JSON file.",
        "Create a simple Python CLI bookmark manager with add, list, and delete commands. Store bookmarks in a JSON file.",
        "Create a simple Python CLI recipe book with add, list, and search commands. Store recipes in a JSON file.",
    ][:n_tasks]

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "bench.db"
        workdir = Path(tmpdir) / "project"
        workdir.mkdir()
        memory = MemoryStore(db_path=str(db_path))
        agent = Agent(memory=memory, workdir=workdir, console=console)

        total_log_tokens = 0
        for i, task in enumerate(tasks, 1):
            console.print(f"\nTask {i}/{len(tasks)}: {task}")
            agent.run(task)
            total_log_tokens += agent.last_log_tokens

        memory_items = memory.get_all()
        memory_tokens = sum(len(item.content.split()) for item in memory_items)
        # Use tiktoken for accurate count.
        from agent2048.tokenizer import count_tokens
        memory_tokens = sum(count_tokens(item.content) for item in memory_items)

        ratio = total_log_tokens / memory_tokens if memory_tokens else 0

        table = Table(title=f"Real Compression Benchmark ({len(tasks)} tasks)")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")
        table.add_row("Tasks", str(len(tasks)))
        table.add_row("Total log tokens", str(total_log_tokens))
        table.add_row("Memory items", str(len(memory_items)))
        table.add_row("Memory tokens", str(memory_tokens))
        table.add_row("Compression ratio", f"{ratio:.2f}x")
        for level, count in sorted(memory.stats().items()):
            table.add_row(level, str(count))

        console.print(table)


if __name__ == "__main__":
    run_benchmark()
