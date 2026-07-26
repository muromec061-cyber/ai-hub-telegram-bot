#!/usr/bin/env bash
# Run a manual backup
set -e
python -c "import asyncio; from services.backup import BackupService; print(asyncio.run(BackupService.create_backup()))"
