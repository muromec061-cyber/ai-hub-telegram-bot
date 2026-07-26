"""Groq provider — ultra-fast inference (LPU) for open models."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import LLMProvider, LLMRequest, LLMResponse
from config.logging import get_logger

logger = get_logger("llm.groq")


class GroqProvider(LLMProvider):
    BASE = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str, default_model: str = "llama-3.3-70b-versatile"):
        if not api_key:
            raise ValueError("GROQ_API_KEY is required")
        self.api_key = api_key
        self.default_model = default_model

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": request.model or self.default_model,
            "messages": [m.to_dict() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.stop:
            payload["stop"] = request.stop
        if request.response_format:
            payload["response_format"] = request.response_format
        payload.update(request.extra)

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self.BASE}/chat/completions", json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage", {})

        tool_calls = message.get("tool_calls") or []
        tool_calls_parsed = []
        for tc in tool_calls:
            try:
                args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
            except Exception:
                args = {}
            tool_calls_parsed.append({
                "id": tc.get("id"),
                "name": tc["function"]["name"],
                "arguments": args,
            })

        return LLMResponse(
            content=message.get("content") or "",
            model=data.get("model", self.default_model),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            tool_calls=tool_calls_parsed,
            raw=data,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        payload = {
            "model": request.model or self.default_model,
            "messages": [m.to_dict() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        payload.update(request.extra)
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", f"{self.BASE}/chat/completions", json=payload, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue

    async def embed(self, text: str) -> list[float]:
        # Groq doesn't host embeddings — use the configured fallback if any
        raise NotImplementedError("Groq does not provide embeddings; use OpenAI or Cloudflare")
