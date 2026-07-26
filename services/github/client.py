"""GitHub service — create repos, push code, manage PRs."""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import httpx

from config.env.settings import get_settings
from config.logging import get_logger

logger = get_logger("services.github")


class GitHubService:
    BASE = "https://api.github.com"

    def __init__(self, token: str | None = None, username: str | None = None):
        settings = get_settings()
        self.token = token or settings.github.token
        self.username = username or settings.github.username

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _is_configured(self) -> bool:
        return bool(self.token and self.username)

    async def create_or_update_repo(
        self,
        repo_name: str,
        *,
        description: str = "",
        private: bool = False,
        local_dir: str,
    ) -> str:
        """Create a GitHub repo and push local directory contents."""
        if not self._is_configured():
            logger.warning("GitHub not configured; skipping")
            return ""

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Create repo (idempotent: check first)
            resp = await client.get(f"{self.BASE}/repos/{self.username}/{repo_name}", headers=self._headers())
            if resp.status_code == 404:
                create_resp = await client.post(
                    f"{self.BASE}/user/repos",
                    headers=self._headers(),
                    json={
                        "name": repo_name,
                        "description": description[:300],
                        "private": private,
                        "auto_init": True,
                    },
                )
                create_resp.raise_for_status()
            elif resp.status_code != 200:
                resp.raise_for_status()

            # 2. Upload each file via the Contents API
            await self._push_directory(client, self.username, repo_name, local_dir, "main")

        return f"https://github.com/{self.username}/{repo_name}"

    async def _push_directory(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
        local_dir: str,
        branch: str,
        prefix: str = "",
    ) -> None:
        base = Path(local_dir)
        if not base.exists():
            logger.warning(f"Local dir does not exist: {local_dir}")
            return

        ignore_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build", ".next"}
        ignore_files = {".DS_Store"}

        files_to_upload: list[tuple[str, str]] = []
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(base)
            parts = rel.parts
            if any(p in ignore_dirs for p in parts):
                continue
            if path.name in ignore_files:
                continue
            if path.stat().st_size > 5 * 1024 * 1024:  # 5MB limit
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            files_to_upload.append((str(rel), content))

        for rel_path, content in files_to_upload:
            # Check if file exists to get its sha
            url = f"{self.BASE}/repos/{owner}/{repo}/contents/{prefix}{rel_path}"
            resp = await client.get(url, headers=self._headers())
            sha = None
            if resp.status_code == 200:
                sha = resp.json().get("sha")

            payload = {
                "message": f"Add {rel_path}",
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            if sha:
                payload["sha"] = sha

            r = await client.put(url, headers=self._headers(), json=payload)
            if r.status_code not in (200, 201):
                logger.warning(f"Failed to upload {rel_path}: {r.status_code} {r.text[:200]}")

    async def create_issue(self, repo: str, title: str, body: str) -> str | None:
        if not self._is_configured():
            return None
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.BASE}/repos/{self.username}/{repo}/issues",
                headers=self._headers(),
                json={"title": title, "body": body},
            )
            if resp.status_code in (200, 201):
                return resp.json().get("html_url")
        return None
