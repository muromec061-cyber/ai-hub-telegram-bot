"""Configuration package."""
from .env.settings import get_settings, AppSettings

__all__ = ["get_settings", "AppSettings"]
