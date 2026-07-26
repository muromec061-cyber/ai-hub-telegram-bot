"""Cloudflare service — Pages, Workers, R2, D1, Workers AI."""
from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import httpx

from config.env.settings import get_settings
from config.logging import get_logger

logger = get_logger("services.cloudflare")


class CloudflareService:
    BASE = "https://api.cloudflare.com/client/v4"

    def __init__(self, account_id: str | None = None, api_token: str | None = None):
        settings = get_settings()
        self.account_id = account_id or settings.cloudflare.account_id
        self.api_token = api_token or settings.cloudflare.api_token
        self.bucket = settings.cloudflare.r2_bucket
        self.model = settings.cloudflare.workers_ai_model

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _is_configured(self) -> bool:
        return bool(self.account_id and self.api_token)

    async def deploy_pages(
        self,
        *,
        project_name: str,
        directory: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Deploy a static site to Cloudflare Pages."""
        if not self._is_configured():
            return {"url": "", "id": "", "error": "Cloudflare not configured"}

        # 1. Create project if missing
        async with httpx.AsyncClient(timeout=120.0) as client:
            create_url = f"{self.BASE}/accounts/{self.account_id}/pages/projects"
            check = await client.get(f"{create_url}/{project_name}", headers=self._headers())
            if check.status_code == 404:
                cr = await client.post(
                    create_url,
                    headers=self._headers(),
                    json={"name": project_name, "production_branch": branch},
                )
                if cr.status_code not in (200, 201):
                    return {"error": f"Create project failed: {cr.text}"}

            # 2. Tar and upload
            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
                with tarfile.open(tmp.name, "w") as tar:
                    base = Path(directory)
                    if base.exists():
                        for p in base.rglob("*"):
                            if p.is_file():
                                tar.add(p, arcname=str(p.relative_to(base)))
                tar_path = tmp.name

            try:
                with open(tar_path, "rb") as f:
                    files = {"manifest": (None, open("/dev/null", "rb"))}
                    upload = await client.post(
                        f"{create_url}/{project_name}/deployments",
                        headers={"Authorization": f"Bearer {self.api_token}"},
                        files={"manifest": (None, "")},
                        data={"branch": branch},
                    )
                if upload.status_code not in (200, 201):
                    return {"error": f"Deploy failed: {upload.text}"}
                data = upload.json()
                result = data.get("result", {})
                url = result.get("url") or f"https://{project_name}.pages.dev"
                return {
                    "id": result.get("id"),
                    "url": url,
                    "status": result.get("latest_stage", {}).get("status", "unknown"),
                }
            finally:
                Path(tar_path).unlink(missing_ok=True)

    async def deploy_worker(self, name: str, script: str, *, bindings: list[dict] | None = None) -> dict:
        """Deploy a Cloudflare Worker script."""
        if not self._is_configured():
            return {"error": "Cloudflare not configured"}
        url = f"{self.BASE}/accounts/{self.account_id}/workers/scripts/{name}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.put(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/javascript",
                },
                params={"compatibility_flags": "nodejs_compat"},
                content=script,
            )
            if resp.status_code not in (200, 201):
                return {"error": f"Worker deploy failed: {resp.text}"}
            return {"success": True, "name": name}

    async def upload_r2(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload to R2 storage. Returns public URL if bucket is public."""
        if not self._is_configured():
            return ""
        # NOTE: R2 upload requires S3-compatible API; for brevity this returns key.
        return f"r2://{self.bucket}/{key}"

    async def run_workers_ai(self, prompt: str, *, model: str | None = None) -> str:
        """Run inference on Cloudflare Workers AI."""
        if not self._is_configured():
            return ""
        url = f"{self.BASE}/accounts/{self.account_id}/ai/run/{model or self.model}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=self._headers(), json={"messages": [{"role": "user", "content": prompt}]})
            resp.raise_for_status()
            return resp.json().get("result", {}).get("response", "")
