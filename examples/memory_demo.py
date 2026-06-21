"""Standalone demo of the 2048 memory merging logic.

This demo does not require an API key. It uses a fake LLM client that produces
deterministic embeddings so you can see facts merging into patterns and concepts.
"""

import tempfile
from unittest.mock import MagicMock, patch

from rich.console import Console
from rich.rule import Rule

from agent2048.memory import MemoryStore

console = Console()


def run_demo():
    fake_llm = MagicMock()

    # Produce deterministic embeddings for a few topics.
    embeddings = {
        "fastapi": [0.9] * 1536,
        "sqlalchemy": [0.8] * 1536,
        "pytest": [0.7] * 1536,
        "docker": [0.6] * 1536,
        "ci": [0.5] * 1536,
    }

    def fake_embed(text: str):
        text = text.lower()
        if "fastapi" in text or "endpoint" in text:
            return embeddings["fastapi"]
        if "sqlalchemy" in text or "database" in text or "orm" in text:
            return embeddings["sqlalchemy"]
        if "pytest" in text or "test" in text:
            return embeddings["pytest"]
        if "docker" in text or "container" in text:
            return embeddings["docker"]
        if "ci" in text or "github actions" in text:
            return embeddings["ci"]
        return [0.0] * 1536

    fake_llm.embed.side_effect = fake_embed

    def fake_summarize(a: str, b: str, level: int):
        return f"[L{level}] {a[:50]} + {b[:50]}"

    fake_llm.summarize_pair.side_effect = fake_summarize

    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        store = MemoryStore(db_path=tmp.name)
        with patch("agent2048.memory.llm", fake_llm):
            facts = [
                ("User endpoints use FastAPI", "architecture"),
                ("Product endpoints use FastAPI", "architecture"),
                ("Order endpoints use FastAPI", "architecture"),
                ("Cart endpoints use FastAPI", "architecture"),
                ("Database models use SQLAlchemy ORM", "data"),
                ("Session management uses SQLAlchemy", "data"),
                ("Migrations use Alembic", "data"),
                ("Unit tests use pytest", "qa"),
                ("Integration tests use pytest", "qa"),
                ("Coverage checks use pytest-cov", "qa"),
                ("Deployment uses Docker", "ops"),
                ("CI runs in GitHub Actions", "ops"),
                ("Images are built with Docker Compose", "ops"),
            ]

            for content, tag in facts:
                item = store.add(content, tag=tag)
                console.print(f"Added: {content} -> [L{item.level}] {item.content}")

        console.print(Rule("Memory pyramid"))
        for level, count in sorted(store.stats().items()):
            console.print(f"{level}: {count}")


if __name__ == "__main__":
    run_demo()
