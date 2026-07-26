"""Supabase integration — uses PostgREST + Storage on top of Postgres."""
from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from config.env.settings import get_settings
from config.logging import get_logger

logger = get_logger("memory.supabase")


class SupabaseService:
    def __init__(self):
        s = get_settings()
        if not s.database.supabase_url or not s.database.supabase_key:
            self.client: Client | None = None
            logger.warning("Supabase not configured; using direct DB only")
        else:
            try:
                self.client = create_client(s.database.supabase_url, s.database.supabase_key)
            except Exception as e:
                logger.error(f"Supabase init failed: {e}")
                self.client = None

    def is_configured(self) -> bool:
        return self.client is not None

    async def upload_file(self, bucket: str, path: str, content: bytes, content_type: str = "text/plain") -> str | None:
        if not self.client:
            return None
        try:
            res = self.client.storage.from_(bucket).upload(path, content, {"content-type": content_type})
            return res.path if hasattr(res, "path") else path
        except Exception as e:
            logger.error(f"Supabase upload failed: {e}")
            return None

    async def get_file_url(self, bucket: str, path: str) -> str | None:
        if not self.client:
            return None
        try:
            res = self.client.storage.from_(bucket).get_public_url(path)
            return res
        except Exception as e:
            logger.error(f"Supabase URL failed: {e}")
            return None

    async def rpc(self, function_name: str, params: dict) -> Any:
        if not self.client:
            return None
        try:
            return self.client.rpc(function_name, params).execute()
        except Exception as e:
            logger.error(f"Supabase RPC failed: {e}")
            return None
