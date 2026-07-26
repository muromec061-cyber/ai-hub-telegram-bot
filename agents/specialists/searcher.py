"""Searcher agent — finds information on the web."""
from __future__ import annotations

from agents.base import AgentRole, AgentState, BaseAgent, Tool
from agents.tools import search_tools
from config.logging import get_logger

logger = get_logger("agent.searcher")

SEARCHER_SYSTEM = """You are an expert research agent.

You find, fetch, and summarize information from the web to answer questions.

Approach:
1. Identify what info you need
2. Use web_search to find relevant sources
3. Use fetch_url to read the most promising results
4. Synthesize a clear, sourced answer

Output:
- Direct answer to the question
- Key facts with source URLs
- Caveats and uncertainties
"""


class SearcherAgent(BaseAgent):
    name = "searcher"
    role = AgentRole.SEARCHER
    description = "Searches the web and synthesizes answers"
    system_prompt = SEARCHER_SYSTEM
    temperature = 0.3
    max_tokens = 4000

    def __init__(self, llm=None):
        tools = [
            Tool(
                name="web_search",
                description="Search the web for a query",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "default": 8},
                    },
                    "required": ["query"],
                },
                func=search_tools.web_search,
            ),
            Tool(
                name="fetch_url",
                description="Fetch a URL and return its text content",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "max_chars": {"type": "integer", "default": 10000},
                    },
                    "required": ["url"],
                },
                func=search_tools.fetch_url,
            ),
        ]
        super().__init__(llm=llm, tools=tools)

    async def run(self, state: AgentState) -> AgentState:
        logger.info(f"Searcher: researching for task {state.task_id}")
        content, meta = await self.think(state)
        state.context["research"] = content
        state.history.append({
            "agent": self.name,
            "input": state.input,
            "output": content,
            "meta": meta,
        })
        return state
