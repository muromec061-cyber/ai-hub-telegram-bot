"""
ServiceCluster — единая точка доступа ко всем внешним сервисам.

Создаётся один раз при старте бота, шарится через app-state.
Любой модуль может попросить `cluster.llm.complete(...)` или
`cluster.openclaw.run_goal(...)` без пересоздания клиентов.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from config.env.settings import get_settings
from config.logging import get_logger
from services.cloudflare.client import CloudflareService
from services.github.client import GitHubService
from services.llm import (
    AnthropicProvider,
    CloudflareProvider,
    GroqProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
)
from services.openclaw import OpenClawClient

logger = get_logger("cluster")


class ServiceCluster:
    """Lazy-initialized service container."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._llm: LLMProvider | None = None
        self._llm_name: str | None = None
        self._github: GitHubService | None = None
        self._cloudflare: CloudflareService | None = None
        self._openclaw: OpenClawClient | None = None
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, name: str) -> asyncio.Lock:
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()
        return self._locks[name]

    # ----- LLM -----
    async def get_llm(self, name: str | None = None) -> LLMProvider:
        """Return the requested (or active) LLM provider, building it on demand."""
        target = name or self._settings.llm.active_llm
        async with self._lock("llm"):
            if self._llm and self._llm_name == target:
                return self._llm
            self._llm = self._build_llm(target)
            self._llm_name = target
            logger.info(f"ServiceCluster: LLM provider = {target} ({self._llm.__class__.__name__})")
            return self._llm

    def _build_llm(self, name: str) -> LLMProvider:
        s = self._settings.llm
        if name == "groq" and s.groq_api_key:
            return GroqProvider(api_key=s.groq_api_key, default_model=s.groq_model)
        if name == "openai" and s.openai_api_key:
            return OpenAIProvider(api_key=s.openai_api_key, base_url=s.openai_base_url, default_model=s.openai_model)
        if name == "cloudflare" and self._settings.cloudflare.api_token:
            return CloudflareProvider(
                account_id=self._settings.cloudflare.account_id or "",
                api_token=self._settings.cloudflare.api_token,
                default_model=self._settings.cloudflare.workers_ai_model,
            )
        if name == "ollama":
            return OllamaProvider(base_url=s.ollama_base_url, default_model=s.ollama_model)
        if name == "anthropic" and s.anthropic_api_key:
            return AnthropicProvider(api_key=s.anthropic_api_key, default_model=s.anthropic_model)
        # Fallback chain
        if s.groq_api_key:
            return GroqProvider(api_key=s.groq_api_key, default_model=s.groq_model)
        if s.openai_api_key:
            return OpenAIProvider(api_key=s.openai_api_key, base_url=s.openai_base_url, default_model=s.openai_model)
        return OllamaProvider(base_url=s.ollama_base_url, default_model=s.ollama_model)

    async def available_llms(self) -> list[dict]:
        """List all configured LLM providers (for the model-picker UI)."""
        s = self._settings.llm
        out = []
        if s.groq_api_key:
            out.append({"id": "groq", "name": f"⚡ Groq · {s.groq_model}", "model": s.groq_model})
        if s.openai_api_key:
            out.append({"id": "openai", "name": f"🧠 OpenAI · {s.openai_model}", "model": s.openai_model})
        if self._settings.cloudflare.api_token:
            out.append({"id": "cloudflare", "name": f"☁️ Cloudflare · {self._settings.cloudflare.workers_ai_model}", "model": self._settings.cloudflare.workers_ai_model})
        if s.anthropic_api_key:
            out.append({"id": "anthropic", "name": f"🌀 Anthropic · {s.anthropic_model}", "model": s.anthropic_model})
        out.append({"id": "ollama", "name": f"🦙 Ollama · {s.ollama_model}", "model": s.ollama_model})
        return out

    # ----- Other services -----
    async def github(self) -> GitHubService | None:
        if self._github is None and self._settings.github.token:
            self._github = GitHubService()
        return self._github

    async def cloudflare(self) -> CloudflareService | None:
        if self._cloudflare is None and self._settings.cloudflare.api_token:
            self._cloudflare = CloudflareService()
        return self._cloudflare

    async def openclaw(self) -> OpenClawClient | None:
        if self._openclaw is None and self._settings.openclaw.enabled:
            self._openclaw = OpenClawClient()
            # Auto-start local sidecar if installed
            try:
                from workers.openclaw import OpenClawLauncher
                launcher = OpenClawLauncher()
                if launcher.is_installed() and not launcher.is_running():
                    started = launcher.start()
                    if started:
                        logger.info("OpenClaw sidecar launched")
                        # Give it time to boot
                        import asyncio as _aio
                        await _aio.sleep(2.0)
            except Exception as e:
                logger.warning(f"OpenClaw auto-launch skipped: {e}")
        return self._openclaw

    async def health(self) -> dict:
        """Health snapshot of all services."""
        snap: dict[str, Any] = {"llm": None, "openclaw": None, "github": False, "cloudflare": False}
        try:
            llm = await self.get_llm()
            snap["llm"] = llm.__class__.__name__
        except Exception as e:
            snap["llm"] = f"error: {e}"
        oc = await self.openclaw()
        if oc:
            snap["openclaw"] = await oc.health()
        snap["github"] = bool(await self.github())
        snap["cloudflare"] = bool(await self.cloudflare())
        return snap

    async def shutdown(self) -> None:
        if self._openclaw:
            await self._openclaw.close()


# Singleton
_cluster: ServiceCluster | None = None


def get_cluster() -> ServiceCluster:
    global _cluster
    if _cluster is None:
        _cluster = ServiceCluster()
    return _cluster
