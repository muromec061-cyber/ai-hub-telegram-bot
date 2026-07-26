"""Vector store — ChromaDB-backed semantic memory.

Stores embeddings of memory entries for semantic retrieval.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from config.logging import get_logger

logger = get_logger("memory.vector")


class VectorStore:
    """Thin wrapper around ChromaDB. Falls back to no-op if unavailable."""

    def __init__(self, persist_dir: str = "data/chroma"):
        self.persist_dir = persist_dir
        self._client = None
        self._collection = None
        try:
            import chromadb
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
            self._collection = self._client.get_or_create_collection(
                name="agent_memory",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Vector store ready at {persist_dir}")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable, vector memory disabled: {e}")

    def is_configured(self) -> bool:
        return self._collection is not None

    def add(self, text: str, metadata: dict | None = None, *, doc_id: str | None = None) -> str | None:
        if not self._collection:
            return None
        doc_id = doc_id or str(uuid.uuid4())
        try:
            self._collection.add(documents=[text], metadata=[metadata or {}], ids=[doc_id])
            return doc_id
        except Exception as e:
            logger.error(f"Vector add failed: {e}")
            return None

    def query(self, text: str, *, n_results: int = 5, where: dict | None = None) -> list[dict]:
        if not self._collection:
            return []
        try:
            kwargs: dict[str, Any] = {"query_texts": [text], "n_results": n_results}
            if where:
                kwargs["where"] = where
            res = self._collection.query(**kwargs)
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            ids = res.get("ids", [[]])[0]
            distances = res.get("distances", [[]])[0]
            return [
                {"id": i, "text": d, "metadata": m, "distance": dist}
                for i, d, m, dist in zip(ids, docs, metas, distances)
            ]
        except Exception as e:
            logger.error(f"Vector query failed: {e}")
            return []

    def delete(self, doc_id: str) -> None:
        if not self._collection:
            return
        try:
            self._collection.delete(ids=[doc_id])
        except Exception as e:
            logger.error(f"Vector delete failed: {e}")
