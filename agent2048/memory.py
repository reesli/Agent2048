"""Hierarchical memory store with 2048-style soft merging."""

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from agent2048.config import settings
from agent2048.llm import llm
from agent2048.utils import cosine_similarity

try:
    import sqlite_vec

    _SQLITE_VEC_AVAILABLE = True
except Exception:  # pragma: no cover - sqlite-vec may not be installed
    _SQLITE_VEC_AVAILABLE = False


@dataclass
class MemoryItem:
    id: str
    content: str
    level: int
    embedding: np.ndarray
    tag: str | None = None
    sources: list[str] | None = None
    merged_into: str | None = None
    meta: dict[str, Any] | None = None
    created_at: str | None = None


class MemoryStore:
    def __init__(self, db_path: str | None = None):
        if db_path is None or db_path == "":
            db_path = str(Path.cwd() / ".agent2048" / "memory.db")
        self.db_path = db_path
        # Ensure parent directory exists (for per-project .agent2048/memory.db)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._vec_enabled = False
        self._vec_dim: int | None = None
        self._init_db()
        self._migrate_db()
        self._init_vec_index()

    def close(self) -> None:
        """Close the database connection and release resources."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    @property
    def conn(self) -> sqlite3.Connection:
        """Return a reusable connection with row factory enabled."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            if _SQLITE_VEC_AVAILABLE:
                try:
                    self._conn.enable_load_extension(True)
                    sqlite_vec.load(self._conn)
                except Exception:
                    pass
        return self._conn

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    tag TEXT,
                    embedding BLOB NOT NULL,
                    sources TEXT,
                    merged_into TEXT,
                    meta TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_level ON memory(level)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_merged ON memory(merged_into)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_tag ON memory(tag)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _migrate_db(self) -> None:
        """Add merged_into column/index if missing from older databases."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute("PRAGMA table_info(memory)")
            columns = {row[1] for row in cur.fetchall()}
            if "merged_into" not in columns:
                conn.execute("ALTER TABLE memory ADD COLUMN merged_into TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_merged ON memory(merged_into)"
            )
            conn.commit()
        finally:
            conn.close()

    def _init_vec_index(self) -> None:
        """Load sqlite-vec extension and prepare the ANN virtual table.

        The vec0 table is created lazily once we know the embedding dimension.
        If sqlite-vec is unavailable, the store transparently falls back to
        full-table scans.
        """
        if not _SQLITE_VEC_AVAILABLE:
            return
        try:
            self.conn.enable_load_extension(True)
            sqlite_vec.load(self.conn)
        except Exception:
            return

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vec_rowid_map (
                memory_id TEXT PRIMARY KEY,
                vec_rowid INTEGER NOT NULL UNIQUE
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vec_rowid_map_rowid ON vec_rowid_map(vec_rowid)"
        )

        dim_row = self.conn.execute(
            "SELECT value FROM memory_meta WHERE key = 'embedding_dim'"
        ).fetchone()
        if dim_row:
            self._vec_dim = int(dim_row["value"])
            self._create_vec_table(self._vec_dim)
            self._vec_enabled = True

    def _create_vec_table(self, dim: int) -> None:
        """Create (or recreate) the vec0 virtual table for the given dimension."""
        self.conn.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_memory USING vec0(
                embedding float[{dim}],
                +level INT,
                +tag TEXT
            )
            """
        )

    def _set_vec_dim(self, dim: int) -> None:
        """Persist and apply the embedding dimension for the ANN index."""
        if self._vec_dim == dim:
            return
        self._vec_dim = dim
        self.conn.execute(
            """
            INSERT INTO memory_meta (key, value) VALUES ('embedding_dim', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (str(dim),),
        )
        self._create_vec_table(dim)
        self._vec_enabled = True

    def _reindex_vec(self) -> None:
        """Backfill the ANN index from existing memory rows."""
        if not self._vec_enabled or self._vec_dim is None:
            return
        rows = self.conn.execute(
            """
            SELECT m.id, m.level, m.tag, m.embedding
            FROM memory m
            LEFT JOIN vec_rowid_map r ON r.memory_id = m.id
            WHERE m.merged_into IS NULL AND r.vec_rowid IS NULL
            """
        ).fetchall()
        for row in rows:
            self._insert_vec_row(row["id"], row["level"], row["tag"], row["embedding"])

    def _insert_vec_row(
        self,
        memory_id: str,
        level: int,
        tag: str | None,
        embedding_blob: bytes,
    ) -> None:
        """Insert a single active memory row into the ANN index."""
        if not self._vec_enabled or self._vec_dim is None:
            return
        cur = self.conn.execute(
            "INSERT INTO vec_rowid_map (memory_id, vec_rowid) VALUES (?, ?) "
            "ON CONFLICT(memory_id) DO UPDATE SET memory_id=excluded.memory_id "
            "RETURNING vec_rowid",
            (memory_id, self._next_vec_rowid()),
        )
        vec_rowid = cur.fetchone()[0]
        # Idempotent: remove any stale vec row before inserting, so reindex
        # and normal insert paths can safely overlap.
        self.conn.execute("DELETE FROM vec_memory WHERE rowid = ?", (vec_rowid,))
        self.conn.execute(
            "INSERT INTO vec_memory(rowid, level, tag, embedding) VALUES (?, ?, ?, ?)",
            (vec_rowid, level, tag, embedding_blob),
        )

    def _next_vec_rowid(self) -> int:
        """Return the next integer rowid for the vec0 table."""
        row = self.conn.execute(
            "SELECT COALESCE(MAX(vec_rowid), 0) + 1 FROM vec_rowid_map"
        ).fetchone()
        return int(row[0])

    def _delete_vec_row(self, memory_id: str) -> None:
        """Remove a memory row from the ANN index (e.g. when merged)."""
        if not self._vec_enabled:
            return
        row = self.conn.execute(
            "SELECT vec_rowid FROM vec_rowid_map WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()
        if row is None:
            return
        vec_rowid = row["vec_rowid"]
        self.conn.execute("DELETE FROM vec_memory WHERE rowid = ?", (vec_rowid,))

    def _row_to_item(self, row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            id=row["id"],
            content=row["content"],
            level=row["level"],
            embedding=np.frombuffer(row["embedding"], dtype=np.float32),
            tag=row["tag"],
            sources=json.loads(row["sources"]) if row["sources"] else None,
            merged_into=row["merged_into"],
            meta=json.loads(row["meta"]) if row["meta"] else None,
            created_at=row["created_at"],
        )

    def _row_to_item_no_embedding(self, row: sqlite3.Row) -> MemoryItem:
        """Create a MemoryItem without deserializing the embedding.

        Used for token-counting and stats where embeddings are not needed.
        """
        return MemoryItem(
            id=row["id"],
            content=row["content"],
            level=row["level"],
            embedding=np.array([], dtype=np.float32),
            tag=row["tag"],
            sources=json.loads(row["sources"]) if row["sources"] else None,
            merged_into=row["merged_into"],
            meta=json.loads(row["meta"]) if row["meta"] else None,
            created_at=row["created_at"],
        )

    def add(
        self,
        content: str,
        level: int = 1,
        tag: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """Add a memory item and try to merge it upward (2048-style).

        Uses soft merge: old items are kept but marked as merged_into the new
        abstraction, so details can be retrieved on demand.
        """
        embedding = np.array(llm.embed(content), dtype=np.float32)
        best = self._find_merge_candidate(embedding, level, tag)

        if best is None:
            item = MemoryItem(
                id=str(uuid.uuid4()),
                content=content,
                level=level,
                embedding=embedding,
                tag=tag,
                meta=meta,
            )
            self._insert(item)
            return item

        incoming_item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            level=level,
            embedding=embedding,
            tag=tag,
            meta=meta,
        )
        self._insert(incoming_item)

        new_content = llm.summarize_pair(best.content, content, level + 1)
        new_sources = [best.id, incoming_item.id]
        if best.sources:
            new_sources.extend(best.sources)

        new_item = self._create_abstraction(
            new_content, level + 1, best.tag or tag, new_sources, meta
        )
        self._mark_merged(best.id, new_item.id)
        self._mark_merged(incoming_item.id, new_item.id)
        return self._try_merge_upward(new_item)

    def _create_abstraction(
        self,
        content: str,
        level: int,
        tag: str | None,
        sources: list[str],
        meta: dict[str, Any] | None = None,
    ) -> MemoryItem:
        embedding = np.array(llm.embed(content), dtype=np.float32)
        item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            level=level,
            embedding=embedding,
            tag=tag,
            sources=sources,
            meta=meta,
        )
        self._insert(item)
        return item

    def _try_merge_upward(
        self,
        item: MemoryItem,
        depth: int = 0,
        max_depth: int | None = None,
    ) -> MemoryItem:
        """Recursively merge the item with a similar higher-level memory."""
        if max_depth is None:
            max_depth = getattr(settings, "max_merge_depth", 10)
        if depth >= max_depth:
            return item

        best = self._find_merge_candidate(
            item.embedding, item.level, tag=item.tag, exclude_id=item.id
        )
        if best is None:
            return item

        new_content = llm.summarize_pair(best.content, item.content, item.level + 1)
        new_sources = [best.id, item.id]
        if best.sources:
            new_sources.extend(best.sources)
        if item.sources:
            new_sources.extend(item.sources)

        new_item = self._create_abstraction(
            new_content,
            level=item.level + 1,
            tag=best.tag or item.tag,
            sources=new_sources,
            meta={"merged_from": [best.id, item.id]},
        )
        self._mark_merged(best.id, new_item.id)
        self._mark_merged(item.id, new_item.id)
        return self._try_merge_upward(new_item, depth=depth + 1, max_depth=max_depth)

    def _insert(self, item: MemoryItem) -> None:
        embedding_blob = item.embedding.astype(np.float32).tobytes()
        self.conn.execute(
            """
            INSERT INTO memory (id, content, level, tag, embedding, sources, merged_into, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                item.content,
                item.level,
                item.tag,
                embedding_blob,
                json.dumps(item.sources) if item.sources else None,
                item.merged_into,
                json.dumps(item.meta) if item.meta else None,
            ),
        )
        self.conn.commit()
        if item.merged_into is None:
            self._ensure_vec_dim_and_insert(item.id, item.level, item.tag, embedding_blob)

    def _ensure_vec_dim_and_insert(
        self,
        memory_id: str,
        level: int,
        tag: str | None,
        embedding_blob: bytes,
    ) -> None:
        """Enable the ANN index once we know the embedding dimension."""
        if not _SQLITE_VEC_AVAILABLE:
            return
        dim = len(np.frombuffer(embedding_blob, dtype=np.float32))
        if self._vec_dim is None:
            self._set_vec_dim(dim)
            self._reindex_vec()
        elif self._vec_dim != dim:
            # Dimension mismatch: drop and recreate index.
            self._drop_vec_index()
            self._set_vec_dim(dim)
            self._reindex_vec()
        self._insert_vec_row(memory_id, level, tag, embedding_blob)
        self.conn.commit()

    def _drop_vec_index(self) -> None:
        """Drop the ANN index and mapping table."""
        if not self._vec_enabled:
            return
        try:
            self.conn.execute("DROP TABLE IF EXISTS vec_memory")
            self.conn.execute("DELETE FROM vec_rowid_map")
        except Exception:
            pass
        self._vec_enabled = False

    def _mark_merged(self, item_id: str, merged_into: str) -> None:
        self.conn.execute(
            "UPDATE memory SET merged_into = ? WHERE id = ?",
            (merged_into, item_id),
        )
        self.conn.commit()
        self._delete_vec_row(item_id)

    def _find_merge_candidate(
        self,
        embedding: np.ndarray,
        level: int,
        tag: str | None = None,
        exclude_id: str | None = None,
    ) -> MemoryItem | None:
        """Find the most similar active same-level memory above the threshold."""
        candidates = self._ann_candidates(
            embedding,
            level=level,
            tag=tag,
            limit=50,
        )
        if candidates is None:
            # Fallback to full-table scan when ANN is unavailable.
            rows = self._query(
                "SELECT * FROM memory WHERE level = ? AND merged_into IS NULL", (level,)
            )
            candidates = [self._row_to_item(row) for row in rows]

        best: MemoryItem | None = None
        best_score = settings.merge_similarity_threshold

        for item in candidates:
            if exclude_id is not None and item.id == exclude_id:
                continue
            if tag is not None and item.tag is not None and item.tag != tag:
                continue
            score = cosine_similarity(embedding, item.embedding)
            if score > best_score:
                best_score = score
                best = item

        return best

    def _ann_candidates(
        self,
        embedding: np.ndarray,
        level: int | None = None,
        tag: str | None = None,
        limit: int = 50,
        max_level: int | None = None,
        include_merged: bool = False,
    ) -> list[MemoryItem] | None:
        """Return approximate nearest neighbors using sqlite-vec, or None."""
        if not self._vec_enabled or self._vec_dim is None:
            return None
        query_blob = embedding.astype(np.float32).tobytes()

        params: list[Any] = [query_blob, limit]
        where_clauses: list[str] = []
        if not include_merged:
            where_clauses.append("m.merged_into IS NULL")
        if level is not None:
            where_clauses.append("v.level = ?")
            params.append(level)
        if max_level is not None:
            where_clauses.append("m.level <= ?")
            params.append(max_level)

        where_sql = " AND ".join(where_clauses)
        sql = f"""
        SELECT m.* FROM vec_memory v
        JOIN vec_rowid_map r ON r.vec_rowid = v.rowid
        JOIN memory m ON m.id = r.memory_id
        WHERE v.embedding MATCH ?
          AND {where_sql}
        ORDER BY v.distance ASC
        LIMIT ?
        """
        try:
            rows = self._query(sql, tuple(params))
        except sqlite3.OperationalError:
            # vec table may be out of sync; fall back to scan.
            return None
        return [self._row_to_item(row) for row in rows]

    def _query(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        cur = self.conn.execute(sql, params)
        return cur.fetchall()

    def search(
        self, query: str, top_k: int = 5, max_level: int | None = None, include_merged: bool = False
    ) -> list[MemoryItem]:
        """Search memory by semantic similarity to a query.

        Uses sqlite-vec ANN index when available, then re-ranks candidates with
        exact cosine similarity. Falls back to a full scan if the index is
        unavailable or out of sync.
        """
        query_embedding = np.array(llm.embed(query), dtype=np.float32)

        candidates = self._ann_candidates(
            query_embedding,
            limit=max(top_k * 5, 50),
            max_level=max_level,
            include_merged=include_merged,
        )
        if candidates is None:
            where_clauses = []
            params: list[Any] = []
            if not include_merged:
                where_clauses.append("merged_into IS NULL")
            if max_level is not None:
                where_clauses.append("level <= ?")
                params.append(max_level)

            sql = "SELECT * FROM memory"
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
            rows = self._query(sql, tuple(params))
            candidates = [self._row_to_item(row) for row in rows]

        scored: list[tuple[float, MemoryItem]] = []
        for item in candidates:
            score = cosine_similarity(query_embedding, item.embedding)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def get_all(
        self, level: int | None = None, include_merged: bool = False
    ) -> list[MemoryItem]:
        """Return memory items, optionally filtered by level and active status."""
        where = []
        params: list[Any] = []
        if level is not None:
            where.append("level = ?")
            params.append(level)
        if not include_merged:
            where.append("merged_into IS NULL")

        sql = "SELECT * FROM memory"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY level DESC, created_at DESC"

        rows = self._query(sql, tuple(params))
        return [self._row_to_item(row) for row in rows]

    def get_children(self, item_id: str) -> list[MemoryItem]:
        """Return all items that were merged into the given item (dive)."""
        rows = self._query(
            "SELECT * FROM memory WHERE merged_into = ? ORDER BY created_at DESC",
            (item_id,),
        )
        return [self._row_to_item(row) for row in rows]

    def get_lineage(self, item_id: str) -> list[MemoryItem]:
        """Return the item and all its descendants recursively.

        Uses a single recursive CTE instead of N+1 queries.
        """
        cte_sql = """
        WITH RECURSIVE lineage(id) AS (
            SELECT id FROM memory WHERE id = ?
            UNION ALL
            SELECT m.id FROM memory m
            INNER JOIN lineage l ON m.merged_into = l.id
        )
        SELECT m.* FROM memory m
        INNER JOIN lineage l ON m.id = l.id
        ORDER BY m.level DESC, m.created_at DESC
        """
        rows = self._query(cte_sql, (item_id,))
        return [self._row_to_item(row) for row in rows]

    def stats(self, include_merged: bool = False) -> dict[str, int]:
        """Return counts of memory items per level."""
        sql = "SELECT level, COUNT(*) as cnt FROM memory"
        if not include_merged:
            sql += " WHERE merged_into IS NULL"
        sql += " GROUP BY level"
        rows = self._query(sql, ())
        return {f"level_{row['level']}": row["cnt"] for row in rows}

    def get_token_counts(self) -> tuple[int, int]:
        """Return (total_tokens, active_tokens) without loading embeddings.

        More efficient than get_all() + count_tokens for metrics.
        """
        from agent2048.tokenizer import count_tokens

        total = 0
        active = 0
        rows = self._query("SELECT content, merged_into FROM memory")
        for row in rows:
            tokens = count_tokens(row["content"])
            total += tokens
            if row["merged_into"] is None:
                active += tokens
        return total, active

    def clear(self) -> None:
        """Wipe all memory."""
        self.conn.execute("DELETE FROM memory")
        if self._vec_enabled:
            try:
                self.conn.execute("DELETE FROM vec_memory")
                self.conn.execute("DELETE FROM vec_rowid_map")
            except Exception:
                pass
        self.conn.commit()
