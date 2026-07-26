"""Cloudflare Workers AI provider — runs LLMs on the edge."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import LLMProvider, LLMRequest, LLMResponse
from config.logging import get_logger

logger = get_logger("llm.cloudflare")


class CloudflareProvider(LLMProvider):
    def __init__(
        self,
        account_id: str,
        api_token: str,
        default_model: str = "@cf/meta/llama-3.1-8b-instruct",
    ):
        self.account_id = account_id
        self.api_token = api_token
        self.default_model = default_model
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.stop:
            payload["stop"] = request.stop

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/{request.model or self.default_model}",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        # Cloudflare returns {success, result: {response, usage}}
        result = data.get("result", {})
        usage = result.get("usage", {})
        return LLMResponse(
            content=result.get("response", ""),
            model=request.model or self.default_model,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            finish_reason="stop",
            raw=data,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        # Cloudflare Workers AI supports streaming via SSE
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/{request.model or self.default_model}",
                json=payload,
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
                    except Exception:
                        continue

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/@cf/baai/bge-base-en-v1.5",
                json={"text": [text]},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {}).get("data", [{}])[0].get("embedding", [])
