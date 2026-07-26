"""LLM provider factory and singleton."""
from __future__ import annotations

from functools import lru_cache

from config.env.settings import get_settings
from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider
from .cloudflare_provider import CloudflareProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    settings = get_settings()

    if settings.llm.use_self_hosted:
        return OllamaProvider(
            base_url=settings.llm.ollama_base_url,
            default_model=settings.llm.ollama_model,
        )

    if settings.cloudflare.account_id and settings.cloudflare.api_token:
        return CloudflareProvider(
            account_id=settings.cloudflare.account_id,
            api_token=settings.cloudflare.api_token,
            default_model=settings.cloudflare.workers_ai_model,
        )

    if settings.llm.openai_api_key:
        return OpenAIProvider(
            api_key=settings.llm.openai_api_key,
            base_url=settings.llm.openai_base_url,
            default_model=settings.llm.openai_model,
        )

    # Fallback to local Ollama
    return OllamaProvider(
        base_url=settings.llm.ollama_base_url,
        default_model=settings.llm.ollama_model,
    )
