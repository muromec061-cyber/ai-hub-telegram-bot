"""Backup service — database dumps, file archives, scheduled backups."""
from __future__ import annotations

import asyncio
import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

from config.env.settings import get_settings
from config.logging import get_logger

logger = get_logger("services.backup")


class BackupService:
    BACKUP_DIR = Path("backups")
    DATA_DIRS = ["generated", "logs", "data"]
    DATA_FILES = [".env.example", "alembic.ini"]

    @classmethod
    def _ensure_dir(cls) -> Path:
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        return cls.BACKUP_DIR

    @classmethod
    async def create_backup(cls) -> str:
        s = get_settings()
        cls._ensure_dir()
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        archive_name = cls.BACKUP_DIR / f"backup-{ts}.tar.gz"

        def _pack():
            with tarfile.open(archive_name, "w:gz") as tar:
                # Database dump via pg_dump if available
                dump_file = cls.BACKUP_DIR / f"db-{ts}.sql"
                try:
                    import subprocess
                    # Use sync URL
                    sync_url = s.database.database_url_sync
                    # crude parse: postgresql+psycopg2://user:pass@host:port/db
                    url = sync_url.replace("postgresql+psycopg2://", "postgresql://")
                    subprocess.run(
                        ["pg_dump", url, "-f", str(dump_file)],
                        check=False,
                        capture_output=True,
                    )
                    if dump_file.exists() and dump_file.stat().st_size > 0:
                        tar.add(dump_file, arcname=dump_file.name)
                        dump_file.unlink()
                except Exception as e:
                    logger.warning(f"pg_dump skipped: {e}")

                for d in cls.DATA_DIRS:
                    if Path(d).exists():
                        tar.add(d, arcname=d)
                for f in cls.DATA_FILES:
                    if Path(f).exists():
                        tar.add(f, arcname=f)

        await asyncio.to_thread(_pack)
        size_mb = archive_name.stat().st_size / (1024 * 1024) if archive_name.exists() else 0
        return f"✅ Бэкап создан: `{archive_name}` ({size_mb:.2f} MB)"

    @classmethod
    async def restore_backup(cls, archive_path: str) -> str:
        archive = Path(archive_path)
        if not archive.exists():
            return f"❌ Файл не найден: {archive_path}"

        def _unpack():
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(".")
        await asyncio.to_thread(_unpack)
        return f"✅ Восстановлено из {archive_path}"

    @classmethod
    def list_backups(cls) -> list[dict]:
        cls._ensure_dir()
        files = sorted(cls.BACKUP_DIR.glob("backup-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [{"name": p.name, "size_mb": p.stat().st_size / (1024 * 1024), "modified": p.stat().st_mtime} for p in files]
