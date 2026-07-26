"""Deploy service — high-level orchestrator for shipping code.

Combines GitHub + Cloudflare + Docker registry.
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

from config.env.settings import get_settings
from config.logging import get_logger
from services.cloudflare.client import CloudflareService
from services.github.client import GitHubService

logger = get_logger("services.deploy")


class DeployService:
    def __init__(
        self,
        github: GitHubService | None = None,
        cloudflare: CloudflareService | None = None,
    ):
        settings = get_settings()
        self.github = github or (GitHubService() if settings.github.token else None)
        self.cloudflare = cloudflare or (CloudflareService() if settings.cloudflare.account_id else None)
        self.workdir = Path("generated")
        self.workdir.mkdir(parents=True, exist_ok=True)

    def _project_dir(self, project_name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)
        p = self.workdir / safe
        p.mkdir(parents=True, exist_ok=True)
        return p

    async def push_to_github(self, project_name: str, *, description: str = "") -> str:
        if not self.github:
            return ""
        project_dir = self._project_dir(project_name)
        if not any(project_dir.iterdir()):
            logger.warning(f"Project dir empty: {project_dir}")
            return ""
        return await self.github.create_or_update_repo(
            project_name, description=description, local_dir=str(project_dir)
        )

    async def deploy_static(self, project_name: str) -> dict[str, Any]:
        if not self.cloudflare:
            return {"error": "Cloudflare not configured"}
        project_dir = self._project_dir(project_name)
        return await self.cloudflare.deploy_pages(
            project_name=project_name, directory=str(project_dir)
        )

    async def deploy_worker(self, name: str, script_path: str) -> dict[str, Any]:
        if not self.cloudflare:
            return {"error": "Cloudflare not configured"}
        script = Path(script_path).read_text(encoding="utf-8")
        return await self.cloudflare.deploy_worker(name, script)

    async def build_docker(self, project_name: str, *, tag: str | None = None) -> str:
        project_dir = self._project_dir(project_name)
        if not (project_dir / "Dockerfile").exists():
            return f"No Dockerfile in {project_dir}"
        tag = tag or f"{project_name}:latest"
        proc = await asyncio.create_subprocess_shell(
            f"docker build -t {tag} .",
            cwd=str(project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return f"✅ Built {tag}"
        return f"❌ Build failed: {stderr.decode()[:500]}"

    async def full_deploy(
        self,
        project_name: str,
        *,
        description: str = "",
        target: str = "static",
    ) -> dict[str, Any]:
        """Push to GitHub + deploy to target."""
        result: dict[str, Any] = {"github_url": "", "deployed_url": "", "logs": []}
        repo = await self.push_to_github(project_name, description=description)
        if repo:
            result["github_url"] = repo
            result["logs"].append(f"GitHub: {repo}")
        if target == "static":
            d = await self.deploy_static(project_name)
            result["deployed_url"] = d.get("url", "")
            result["deployment_id"] = d.get("id", "")
            if d.get("error"):
                result["logs"].append(f"Cloudflare: {d['error']}")
            else:
                result["logs"].append(f"Cloudflare: {d.get('url')}")
        elif target == "worker":
            # Look for index.js / index.ts
            project_dir = self._project_dir(project_name)
            for cand in ("index.js", "worker.js", "src/index.js", "src/worker.js"):
                if (project_dir / cand).exists():
                    d = await self.deploy_worker(project_name, str(project_dir / cand))
                    result["deployment_id"] = d.get("name", "")
                    if d.get("error"):
                        result["logs"].append(f"Worker: {d['error']}")
                    else:
                        result["logs"].append(f"Worker deployed: {d.get('name')}")
                    break
        return result
