"""Smoke tests — verify the package imports and basic structure is intact."""
import pytest


def test_imports():
    """All major modules should import without error."""
    from config import get_settings
    from agents import Orchestrator, TaskQueue, PlannerAgent, CoderAgent
    from bot import setup_bot
    from memory import MemoryManager
    from services.llm import get_llm_provider
    from services.cloudflare.client import CloudflareService
    from services.github.client import GitHubService
    from services.security import SecurityService
    from services.backup import BackupService
    from services.notifications import NotificationService
    from services.subscription import SubscriptionService
    from services.search import SearchService
    from services.deploy import DeployService

    assert get_settings is not None
    assert Orchestrator is not None
    assert setup_bot is not None


def test_settings_load():
    """Settings should load with test defaults."""
    from config import get_settings
    s = get_settings()
    assert s.app_env == "test"
    assert s.telegram.bot_token.startswith("test_")


def test_security_basic():
    """Security service basic ops."""
    from services.security import SecurityService
    sec = SecurityService()
    h = sec.hash_password("hello")
    assert sec.verify_password("hello", h)
    assert not sec.verify_password("wrong", h)
    token = sec.create_jwt({"sub": "123"})
    payload = sec.verify_jwt(token)
    assert payload["sub"] == "123"


def test_security_helpers():
    from services.security import SecurityService
    sec = SecurityService()
    k = sec.generate_api_key()
    assert k.startswith("sk_")
    assert sec.sha256("test") == sec.sha256("test")
    assert sec.constant_time_compare("abc", "abc")
    assert not sec.constant_time_compare("abc", "abd")
