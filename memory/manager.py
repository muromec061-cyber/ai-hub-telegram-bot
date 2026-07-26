"""Unified memory manager — combines Postgres, Vector, Obsidian."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from config.logging import get_logger
from db.models import get_session
from db.repositories import MemoryRepository
from .obsidian.client import ObsidianMemory
from .vector.store import VectorStore

logger = get_logger("memory.manager")


class MemoryManager:
    """Single entry point for storing/retrieving memories across all backends."""

    def __init__(self):
        self.obsidian = ObsidianMemory()
        self.vector = VectorStore()

    async def remember(
        self,
        *,
        user_id: int | None = None,
        project_id: int | None = None,
        title: str,
        content: str,
        memory_type: str = "fact",
        scope: str = "user",
        tags: list[str] | None = None,
        importance: float = 0.5,
        extra: dict | None = None,
    ) -> int:
        """Store a memory across all configured backends. Returns DB id."""
        async with get_session() as session:
            repo = MemoryRepository(session)
            entry = await repo.create(
                user_id=user_id,
                project_id=project_id,
                memory_type=memory_type,
                scope=scope,
                title=title,
                content=content,
                summary=content[:500],
                tags=tags or [],
                extra=extra or {},
                importance=importance,
            )
            memory_id = entry.id
            # Vector store
            if self.vector.is_configured():
                vec_id = self.vector.add(
                    f"{title}\n{content}",
                    metadata={
                        "memory_id": memory_id,
                        "user_id": user_id,
                        "project_id": project_id,
                        "type": memory_type,
                    },
                )
                if vec_id:
                    await repo.update(entry, vector_id=vec_id)
            # Obsidian
            if self.obsidian.is_configured():
                await self.obsidian.write_memory(
                    title=title, content=content, tags=tags, memory_type=memory_type, extra=extra,
                )
        return memory_id

    async def recall(self, query: str, *, user_id: int | None = None, limit: int = 5) -> list[dict]:
        """Semantic search across memories."""
        if not self.vector.is_configured():
            # Fall back to DB text search
            async with get_session() as session:
                repo = MemoryRepository(session)
                if user_id:
                    entries = await repo.list_by_user(user_id, limit=limit)
                else:
                    entries = []
                return [{"id": e.id, "title": e.title, "content": e.content} for e in entries]

        where = {"user_id": user_id} if user_id else None
        results = self.vector.query(query, n_results=limit, where=where)
        return results
