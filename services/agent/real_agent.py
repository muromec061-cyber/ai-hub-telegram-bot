"""Real multi-provider AI agent runtime.

No mock responses, fake models, or placeholder completions are used. Every
completion is sent to the selected provider's real API or to a local Ollama
server configured by the operator.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    provider: str
    env_key: str | None
    endpoint: str


class ModelRegistry:
    """Built-in model catalog; credentials remain external secrets."""

    def __init__(self) -> None:
        self.models = [
            ModelSpec(os.getenv("AGENT_OPENAI_MODEL", "gpt-5.4"), "OpenAI", "openai", "OPENAI_API_KEY", "https://api.openai.com/v1/chat/completions"),
            ModelSpec(os.getenv("AGENT_ANTHROPIC_MODEL", "claude-sonnet-4-6"), "Anthropic", "anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/messages"),
            ModelSpec(os.getenv("AGENT_GEMINI_MODEL", "gemini-2.5-flash"), "Google Gemini", "gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"),
            ModelSpec(os.getenv("AGENT_GROQ_MODEL", "llama-3.3-70b-versatile"), "Groq", "groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions"),
            ModelSpec(os.getenv("AGENT_OLLAMA_MODEL", "qwen3:8b"), "Ollama local", "ollama", None, os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/chat"),
        ]

    def get(self, model_id: str) -> ModelSpec:
        for spec in self.models:
            if spec.id == model_id:
                return spec
        raise ValueError(f"Неизвестная модель: {model_id}")

    def available(self) -> list[ModelSpec]:
        result: list[ModelSpec] = []
        for spec in self.models:
            if spec.env_key is None or os.getenv(spec.env_key):
                result.append(spec)
        return result


class RealAIAgent:
    def __init__(self, registry: ModelRegistry | None = None, timeout: float = 120.0) -> None:
        self.registry = registry or ModelRegistry()
        self.timeout = timeout

    async def complete(self, prompt: str, model_id: str | None = None, system: str | None = None) -> str:
        available = self.registry.available()
        if not available:
            raise RuntimeError("Нет доступной модели: добавьте API-ключ провайдера или запустите Ollama.")
        spec = self.registry.get(model_id) if model_id else available[0]
        if spec.env_key and not os.getenv(spec.env_key):
            raise RuntimeError(f"Для модели {spec.id} нужен {spec.env_key}.")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if spec.provider in {"openai", "groq"}:
            return await self._openai_compatible(spec, messages)
        if spec.provider == "anthropic":
            return await self._anthropic(spec, prompt, system)
        if spec.provider == "gemini":
            return await self._gemini(spec, prompt, system)
        if spec.provider == "ollama":
            return await self._ollama(spec, messages)
        raise RuntimeError(f"Провайдер {spec.provider} не поддерживается")

    async def _openai_compatible(self, spec: ModelSpec, messages: list[dict[str, str]]) -> str:
        key = os.environ[spec.env_key or ""]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(spec.endpoint, headers={"Authorization": f"Bearer {key}"}, json={"model": spec.id, "messages": messages, "temperature": 0.7})
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"].get("content") or ""

    async def _anthropic(self, spec: ModelSpec, prompt: str, system: str | None) -> str:
        key = os.environ[spec.env_key or ""]
        payload: dict[str, Any] = {"model": spec.id, "max_tokens": 4096, "messages": [{"role": "user", "content": prompt}]}
        if system:
            payload["system"] = system
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(spec.endpoint, headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, json=payload)
            response.raise_for_status()
            data = response.json()
        return "".join(item.get("text", "") for item in data.get("content", []) if item.get("type") == "text")

    async def _gemini(self, spec: ModelSpec, prompt: str, system: str | None) -> str:
        key = os.environ[spec.env_key or ""]
        url = spec.endpoint.format(model=spec.id)
        contents: list[dict[str, Any]] = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, params={"key": key}, json={"contents": contents})
            response.raise_for_status()
            data = response.json()
        return data["candidates"][0]["content"]["parts"][0].get("text", "")

    async def _ollama(self, spec: ModelSpec, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(spec.endpoint, json={"model": spec.id, "messages": messages, "stream": False})
            response.raise_for_status()
            data = response.json()
        return data.get("message", {}).get("content", "")
