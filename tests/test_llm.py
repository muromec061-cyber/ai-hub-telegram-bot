"""LLM provider tests (no live calls)."""
import pytest


def test_factory_returns_provider():
    from services.llm import get_llm_provider
    p = get_llm_provider()
    assert p is not None


def test_message_to_dict():
    from services.llm import LLMMessage
    m = LLMMessage(role="user", content="hi")
    d = m.to_dict()
    assert d["role"] == "user"
    assert d["content"] == "hi"


def test_ollama_provider_init():
    from services.llm import OllamaProvider
    p = OllamaProvider(base_url="http://localhost:11434", default_model="llama3.1:8b")
    assert p.default_model == "llama3.1:8b"


def test_openai_provider_init():
    from services.llm import OpenAIProvider
    p = OpenAIProvider(api_key="sk-test", base_url="https://api.openai.com/v1")
    assert p.api_key == "sk-test"
