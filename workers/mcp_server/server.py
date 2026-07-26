"""MCP server entrypoint — `python -m workers.mcp_server`."""
import asyncio

from config.logging import setup_logging, get_logger
from services.mcp import MCPServer

logger = get_logger("mcp_server")


def main():
    setup_logging()
    logger.info("Starting MCP server")
    server = MCPServer()
    asyncio.run(server.start())


if __name__ == "__main__":
    main()
