"""Obsidian vault integration — writes memories as Markdown files in a vault.

This gives the agent a long-term knowledge base that humans can browse/edit.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.env.settings import get_settings
from config.logging import get_logger

logger = get_logger("memory.obsidian")


class ObsidianMemory:
    """Two-way sync with an Obsidian vault via the local filesystem."""

    def __init__(self, vault_path: str | None = None):
        s = get_settings()
        self.vault_path = Path(vault_path or s.obsidian.vault_path or "")
        self._configured = bool(self.vault_path and self.vault_path.exists())

    def is_configured(self) -> bool:
        return self._configured

    def _ai_folder(self) -> Path:
        folder = self.vault_path / "AI-Memory"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    async def write_memory(
        self,
        title: str,
        content: str,
        *,
        tags: list[str] | None = None,
        memory_type: str = "note",
        extra: dict | None = None,
    ) -> str | None:
        """Write a memory note to the Obsidian vault. Returns file path."""
        if not self._configured:
            return None
        try:
            folder = self._ai_folder()
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:100]
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            path = folder / f"{timestamp}-{safe_title}.md"

            frontmatter = [
                "---",
                f"title: \"{title}\"",
                f"type: {memory_type}",
                f"created: {datetime.utcnow().isoformat()}Z",
                f"tags: [{', '.join(tags or [])}]",
            ]
            if extra:
                for k, v in extra.items():
                    frontmatter.append(f"{k}: {json.dumps(v, default=str)}")
            frontmatter.append("---\n")

            full = "\n".join(frontmatter) + f"# {title}\n\n{content}\n"
            path.write_text(full, encoding="utf-8")
            logger.info(f"Obsidian: wrote {path}")
            return str(path)
        except Exception as e:
            logger.error(f"Obsidian write failed: {e}")
            return None

    async def search(self, query: str, *, limit: int = 10) -> list[dict]:
        """Simple text search across memory notes."""
        if not self._configured:
            return []
        results = []
        try:
            for path in self._ai_folder().glob("*.md"):
                try:
                    text = path.read_text(encoding="utf-8")
                    if query.lower() in text.lower():
                        results.append({
                            "path": str(path),
                            "title": path.stem,
                            "snippet": text[:300],
                        })
                        if len(results) >= limit:
                            break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Obsidian search failed: {e}")
        return results

    async def list_recent(self, limit: int = 20) -> list[dict]:
        if not self._configured:
            return []
        files = sorted(self._ai_folder().glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [{"path": str(p), "title": p.stem, "modified": p.stat().st_mtime} for p in files[:limit]]
