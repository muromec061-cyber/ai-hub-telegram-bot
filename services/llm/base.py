"""
LLM provider abstraction.
Supports: OpenAI-compatible APIs, Ollama (self-hosted), Cloudflare Workers AI.
All implement the same interface so the system is provider-agnostic.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config.env.settings import get_settings
from config.logging import get_logger

logger = get_logger("llm")


@dataclass
class LLMMessage:
    role: str  # system, user, assistant, tool
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    finish_reason: str = "stop"
    tool_calls: list[dict] = field(default_factory=list)
    raw: dict | None = None


@dataclass
class LLMRequest:
    messages: list[LLMMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: list[dict] | None = None
    tool_choice: str | None = None
    stop: list[str] | None = None
    response_format: dict | None = None
    extra: dict = field(default_factory=dict)


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...
