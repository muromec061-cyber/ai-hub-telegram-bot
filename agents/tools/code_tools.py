"""Tools for the coder agent — file ops, code execution, repo management."""
from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from config.logging import get_logger

logger = get_logger("tools.code")


async def write_file(path: str, content: str, *, base_dir: str = "generated") -> str:
    """Write a file to disk under the generated/ base directory."""
    full = Path(base_dir) / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return str(full)


async def read_file(path: str, *, base_dir: str = "generated") -> str:
    full = Path(base_dir) / path
    if not full.exists():
        return f"File not found: {full}"
    return full.read_text(encoding="utf-8")


async def list_files(directory: str = ".", *, base_dir: str = "generated") -> list[str]:
    full = Path(base_dir) / directory
    if not full.exists():
        return []
    return [str(p.relative_to(full)) for p in full.rglob("*") if p.is_file()]


async def run_python(code: str, *, timeout: int = 30) -> str:
    """Execute Python code in a subprocess. Returns stdout+stderr."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return "Execution timed out"
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        return f"STDOUT:\n{out}\nSTDERR:\n{err}\nReturn code: {proc.returncode}"
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


async def run_shell(command: str, *, cwd: str | None = None, timeout: int = 60) -> str:
    """Run a shell command. Returns stdout+stderr."""
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return "Command timed out"
    out = stdout.decode("utf-8", errors="replace")
    err = stderr.decode("utf-8", errors="replace")
    return f"STDOUT:\n{out}\nSTDERR:\n{err}\nReturn code: {proc.returncode}"


async def run_tests(project_dir: str, *, test_command: str = "pytest -q", base_dir: str = "generated") -> str:
    full = Path(base_dir) / project_dir
    return await run_shell(test_command, cwd=str(full), timeout=180)
