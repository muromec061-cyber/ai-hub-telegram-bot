"""Ollama provider for self-hosted open models (llama, mistral, qwen, etc.)."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import LLMProvider, LLMRequest, LLMResponse
from config.logging import get_logger

logger = get_logger("llm.ollama")


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3.1:8b"):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": request.model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.stop:
            payload["options"]["stop"] = request.stop

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        message = data.get("message", {})
        return LLMResponse(
            content=message.get("content", ""),
            model=data.get("model", self.default_model),
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            finish_reason=data.get("done_reason", "stop"),
            raw=data,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        payload = {
            "model": request.model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        delta = data.get("message", {}).get("content", "")
                        if delta:
                            yield delta
                        if data.get("done"):
                            break
                    except Exception:
                        continue

    async def embed(self, text: str) -> list[float]:
        embed_model = "nomic-embed-text"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": embed_model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json().get("embedding", [])
