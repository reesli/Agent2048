"""Tests for the memory store."""

import tempfile
from unittest.mock import MagicMock, patch

import numpy as np

from agent2048.memory import MemoryStore


def test_add_and_search():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            fake_llm = MagicMock()
            fake_llm.embed.return_value = [0.1] * 1536
            fake_llm.summarize_pair.return_value = "merged abstraction"

            with patch("agent2048.memory.llm", fake_llm):
                item = store.add("The project uses FastAPI for HTTP endpoints", tag="architecture")
                assert item.content == "The project uses FastAPI for HTTP endpoints"
                assert item.level == 1

                items = store.search("FastAPI HTTP endpoints", top_k=1)
                assert len(items) == 1
                assert items[0].content == item.content


def test_merge_same_level():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            fake_llm = MagicMock()
            fake_llm.embed.return_value = [0.2] * 1536
            fake_llm.summarize_pair.return_value = "All endpoints are built with FastAPI"

            with patch("agent2048.memory.llm", fake_llm):
                store.add("Endpoint A uses FastAPI", tag="architecture")
                store.add("Endpoint B uses FastAPI", tag="architecture")

                active_stats = store.stats()
                assert active_stats.get("level_2", 0) == 1
                assert active_stats.get("level_1", 0) == 0

                all_stats = store.stats(include_merged=True)
                assert all_stats.get("level_1", 0) == 2


def test_no_merge_below_threshold():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            fake_llm = MagicMock()
            call_count = {"n": 0}

            def embed_side_effect(text):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return [0.9] * 1536
                return [-0.9] * 1536

            fake_llm.embed.side_effect = embed_side_effect
            fake_llm.summarize_pair.return_value = "merged"

            with patch("agent2048.memory.llm", fake_llm):
                store.add("First unrelated fact", tag="general")
                store.add("Second unrelated fact", tag="general")

                stats = store.stats()
                assert stats.get("level_1", 0) == 2


def test_soft_merge_lineage():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            fake_llm = MagicMock()
            fake_llm.embed.return_value = [0.3] * 1536
            fake_llm.summarize_pair.return_value = "merged pattern"

            with patch("agent2048.memory.llm", fake_llm):
                a = store.add("Fact A", tag="general")
                b = store.add("Fact B", tag="general")

                active = store.get_all()
                assert len(active) == 1
                parent = active[0]
                assert parent.level == 2

                children = store.get_children(parent.id)
                assert len(children) == 2
                lineage = store.get_lineage(parent.id)
                contents = {item.content for item in lineage}
                assert "Fact A" in contents
                assert "Fact B" in contents


def test_ann_index_enabled_after_insert():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            fake_llm = MagicMock()
            fake_llm.embed.return_value = [0.1] * 384
            fake_llm.summarize_pair.return_value = "merged"

            with patch("agent2048.memory.llm", fake_llm):
                store.add("ANN index test fact", tag="ann")
                assert store._vec_enabled is True
                assert store._vec_dim == 384


def test_ann_search_returns_results():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            fake_llm = MagicMock()
            counter = {"n": 0}

            def embed_side_effect(text):
                counter["n"] += 1
                vec = [0.0] * 384
                vec[counter["n"] % 384] = 1.0
                return vec

            fake_llm.embed.side_effect = embed_side_effect
            fake_llm.summarize_pair.return_value = "merged"

            with patch("agent2048.memory.llm", fake_llm):
                for i in range(10):
                    store.add(f"fact {i}", tag="ann")
                results = store.search("fact", top_k=3)
                assert len(results) == 3


def test_ann_merge_candidate_uses_same_level():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            fake_llm = MagicMock()
            fake_llm.embed.return_value = [0.5] * 384
            fake_llm.summarize_pair.return_value = "merged abstraction"

            with patch("agent2048.memory.llm", fake_llm):
                a = store.add("Level one fact A", tag="same")
                b = store.add("Level one fact B", tag="same")
                active = store.get_all()
                assert all(item.level > 1 or item.id in (a.id, b.id) for item in active)
                assert any(item.level == 2 for item in active)


def test_close_releases_connection():
    """MemoryStore.close() should close the database connection."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        store = MemoryStore(db_path=tmp.name)
        assert store._conn is not None or True  # conn is lazy
        store.conn  # Force connection
        assert store._conn is not None
        store.close()
        assert store._conn is None


def test_context_manager_closes_on_exit():
    """Context manager should close connection on exit."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            assert store._conn is not None
        assert store._conn is None


def test_context_manager_closes_on_exception():
    """Context manager should close connection even on exception."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        store = None
        try:
            with MemoryStore(db_path=tmp.name) as s:
                store = s
                raise ValueError("test error")
        except ValueError:
            pass
        assert store is not None
        assert store._conn is None


def test_get_token_counts():
    """get_token_counts should return (total, active) without loading embeddings."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        with MemoryStore(db_path=tmp.name) as store:
            fake_llm = MagicMock()
            fake_llm.embed.return_value = [0.1] * 384
            fake_llm.summarize_pair.return_value = "merged"

            with patch("agent2048.memory.llm", fake_llm):
                store.add("First fact about testing", tag="test")
                store.add("Second fact about testing", tag="test")

                total, active = store.get_token_counts()
                assert total > 0
                assert active > 0
                assert active <= total
