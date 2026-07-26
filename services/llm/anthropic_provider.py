"""Anthropic Claude provider."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import LLMProvider, LLMRequest, LLMResponse
from config.logging import get_logger

logger = get_logger("llm.anthropic")


class AnthropicProvider(LLMProvider):
    BASE = "https://api.anthropic.com/v1"

    def __init__(self, api_key: str, default_model: str = "claude-3-5-sonnet-20241022"):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        self.api_key = api_key
        self.default_model = default_model

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Split system message
        system = None
        messages = []
        for m in request.messages:
            if m.role == "system":
                system = m.content
            else:
                messages.append({"role": m.role, "content": m.content})

        payload: dict = {
            "model": request.model or self.default_model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system:
            payload["system"] = system
        if request.stop:
            payload["stop_sequences"] = request.stop
        payload.update(request.extra)

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self.BASE}/messages", json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            model=data.get("model", self.default_model),
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            finish_reason=data.get("stop_reason", "stop"),
            raw=data,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        system = None
        messages = []
        for m in request.messages:
            if m.role == "system":
                system = m.content
            else:
                messages.append({"role": m.role, "content": m.content})
        payload: dict = {
            "model": request.model or self.default_model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if system:
            payload["system"] = system
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", f"{self.BASE}/messages", json=payload, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:].strip())
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {}).get("text", "")
                            if delta:
                                yield delta
                    except Exception:
                        continue

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError("Use OpenAI or Cloudflare for embeddings")
