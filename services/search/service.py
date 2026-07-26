"""Search service — aggregated web search, summarization, knowledge lookup."""
from __future__ import annotations

from typing import Any

from agents.tools import search_tools
from config.logging import get_logger

logger = get_logger("services.search")


class SearchService:
    """High-level search wrapper with caching and post-processing."""

    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, Any]] = {}

    def _cache_key(self, query: str, n: int) -> str:
        return f"{query.strip().lower()}::{n}"

    def _cache_get(self, key: str) -> Any | None:
        import time
        v = self._cache.get(key)
        if not v:
            return None
        ts, val = v
        if time.time() - ts > self.cache_ttl:
            self._cache.pop(key, None)
            return None
        return val

    def _cache_set(self, key: str, val: Any) -> None:
        import time
        self._cache[key] = (time.time(), val)

    async def search(self, query: str, *, max_results: int = 8) -> list[dict]:
        key = self._cache_key(query, max_results)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        results = await search_tools.web_search(query, max_results=max_results)
        self._cache_set(key, results)
        return results

    async def fetch(self, url: str, *, max_chars: int = 10000) -> str:
        return await search_tools.fetch_url(url, max_chars=max_chars)

    async def deep_research(self, query: str, *, max_results: int = 6, follow_up: int = 2) -> str:
        """Multi-step research: search -> fetch top results -> synthesize."""
        results = await self.search(query, max_results=max_results)
        if not results:
            return f"No results for: {query}"
        parts = [f"# Research: {query}\n"]
        for i, r in enumerate(results[:follow_up], 1):
            url = r.get("href", "")
            if not url:
                continue
            content = await self.fetch(url, max_chars=3000)
            parts.append(f"\n## Source {i}: {r.get('title', url)}\n{url}\n{content[:2500]}")
        return "\n\n".join(parts)
