"""MCP (Model Context Protocol) server — exposes tools to MCP-compatible clients.

Runs over WebSocket. Provides tools the agents can call, and external clients
(like Claude Desktop) can connect to extend the system.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from agents.tools import (
    fetch_url,
    list_files,
    read_file,
    run_python,
    run_shell,
    run_tests,
    search_and_summarize,
    web_search,
    write_file,
)
from config.logging import get_logger

logger = get_logger("services.mcp")


TOOLS = [
    {"name": "web_search", "description": "Search the web", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 5}}, "required": ["query"]}},
    {"name": "fetch_url", "description": "Fetch a URL", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "write_file", "description": "Write a file", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "read_file", "description": "Read a file", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "run_python", "description": "Run Python code", "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
    {"name": "run_shell", "description": "Run a shell command", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "search_and_summarize", "description": "Search + summarize", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]


class MCPServer:
    """Minimal MCP-over-WebSocket server (JSON-RPC 2.0)."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.handlers = {
            "web_search": lambda args: web_search(args["query"], max_results=args.get("max_results", 5)),
            "fetch_url": lambda args: fetch_url(args["url"]),
            "write_file": lambda args: write_file(args["path"], args["content"]),
            "read_file": lambda args: read_file(args["path"]),
            "run_python": lambda args: run_python(args["code"]),
            "run_shell": lambda args: run_shell(args["command"]),
            "search_and_summarize": lambda args: search_and_summarize(args["query"]),
        }

    async def _handle_request(self, request: dict) -> dict:
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "ai-startup-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            handler = self.handlers.get(name)
            if not handler:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
            try:
                result = await handler(args) if asyncio.iscoroutinefunction(handler) else handler(args)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": str(result)[:10000]}]}}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

    async def start(self) -> None:
        try:
            import websockets
        except ImportError:
            logger.error("Install `websockets` to run MCP server: pip install websockets")
            return

        async def connection_handler(websocket):
            logger.info(f"MCP client connected: {websocket.remote_address}")
            try:
                async for message in websocket:
                    try:
                        request = json.loads(message)
                        response = await self._handle_request(request)
                        await websocket.send(json.dumps(response))
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}))
            except Exception as e:
                logger.error(f"MCP connection error: {e}")

        logger.info(f"MCP server starting on ws://{self.host}:{self.port}")
        async with websockets.serve(connection_handler, self.host, self.port):
            await asyncio.Future()  # run forever


if __name__ == "__main__":
    import asyncio
    asyncio.run(MCPServer().start())
