"""Synthetic compression benchmark.

Measures how much the 2048 memory reduces the token count compared to storing
raw facts. Does not require an API key.
"""

import tempfile
from unittest.mock import MagicMock, patch

from rich.console import Console
from rich.table import Table

from agent2048.memory import MemoryStore
from agent2048.tokenizer import count_tokens

console = Console()


def build_facts(n: int = 50) -> list[tuple[str, str]]:
    """Generate a set of similar facts grouped by topic."""
    topics = [
        ("architecture", "HTTP endpoints are implemented with FastAPI"),
        ("data", "Database models are defined with SQLAlchemy"),
        ("qa", "Tests are written with pytest"),
        ("ops", "Deployment is managed with Docker"),
        ("frontend", "Components are rendered with React"),
        ("auth", "Authentication uses JWT tokens"),
    ]
    facts = []
    for i in range(n):
        tag, base = topics[i % len(topics)]
        facts.append((f"{base} in module {i}", tag))
    return facts


def run_benchmark(n_facts: int = 50):
    fake_llm = MagicMock()

    # Simple deterministic embedding: group by topic.
    topic_vectors = {
        "architecture": [0.9] * 384,
        "data": [0.8] * 384,
        "qa": [0.7] * 384,
        "ops": [0.6] * 384,
        "frontend": [0.5] * 384,
        "auth": [0.4] * 384,
    }

    def fake_embed(text: str):
        text = text.lower()
        for tag, vec in topic_vectors.items():
            if tag in text:
                return vec
        # Fallback: identify merged summaries by their topic keywords.
        topic_keywords = {
            "architecture": ["fastapi", "endpoints"],
            "data": ["sqlalchemy", "database"],
            "qa": ["pytest", "tests"],
            "ops": ["docker", "deployment"],
            "frontend": ["react", "components"],
            "auth": ["jwt", "authentication"],
        }
        for tag, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                return topic_vectors[tag]
        return [0.0] * 384

    def fake_summarize(a: str, b: str, level: int):
        # Realistic compression: keep the topic, drop the specific module id.
        import re
        base = a
        for suffix in [" in module ", " for module ", " module "]:
            if suffix in base:
                base = base.split(suffix)[0]
        return base.strip()

    fake_llm.embed.side_effect = fake_embed
    fake_llm.summarize_pair.side_effect = fake_summarize

    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        store = MemoryStore(db_path=tmp.name)
        facts = build_facts(n_facts)

        raw_tokens = 0
        with patch("agent2048.memory.llm", fake_llm):
            for content, tag in facts:
                raw_tokens += count_tokens(content)
                store.add(content, tag=tag)

        memory_items = store.get_all()
        memory_tokens = sum(count_tokens(item.content) for item in memory_items)
        stats = store.stats()

        ratio = raw_tokens / memory_tokens if memory_tokens else 0

        table = Table(title=f"Synthetic Compression Benchmark ({n_facts} facts)")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")
        table.add_row("Raw facts", str(n_facts))
        table.add_row("Raw tokens", str(raw_tokens))
        table.add_row("Memory items", str(len(memory_items)))
        table.add_row("Memory tokens", str(memory_tokens))
        table.add_row("Compression ratio", f"{ratio:.2f}x")
        for level, count in sorted(stats.items()):
            table.add_row(level, str(count))

        console.print(table)
        return ratio


if __name__ == "__main__":
    run_benchmark(n_facts=500)
