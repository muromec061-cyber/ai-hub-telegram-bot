"""Search tools — DuckDuckGo, fetch URL, summarize web content."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from config.logging import get_logger

logger = get_logger("tools.search")


async def web_search(query: str, *, max_results: int = 8) -> list[dict]:
    """Search the web using DuckDuckGo. Returns list of {title, href, body}."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return []


async def fetch_url(url: str, *, max_chars: int = 10000) -> str:
    """Fetch URL and return text content."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:max_chars]
    except Exception as e:
        logger.error(f"Fetch URL failed: {e}")
        return f"Error fetching {url}: {e}"


async def search_and_summarize(query: str, *, max_results: int = 5) -> str:
    """Search and concatenate top results' content."""
    results = await web_search(query, max_results=max_results)
    if not results:
        return f"No results for: {query}"
    parts = [f"=== Search results for: {query} ==="]
    for i, r in enumerate(results, 1):
        parts.append(f"\n[{i}] {r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')[:500]}")
    return "\n".join(parts)
