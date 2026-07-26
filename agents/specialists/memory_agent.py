"""Memory agent — manages long-term memory: store, retrieve, summarize, decay."""
from __future__ import annotations

from agents.base import AgentRole, AgentState, BaseAgent
from config.logging import get_logger

logger = get_logger("agent.memory")

MEMORY_SYSTEM = """You are the long-term memory manager.

You decide what to remember and what to forget. Given a context:
1. Identify important facts, preferences, decisions, code patterns
2. Categorize: fact, preference, project_note, code_snippet
3. Set importance (0-1) — only memorable stuff > 0.5
4. Suggest tags
"""


class MemoryAgent(BaseAgent):
    name = "memory"
    role = AgentRole.MEMORY
    description = "Stores and retrieves long-term memories"
    system_prompt = MEMORY_SYSTEM
    temperature = 0.3
    max_tokens = 2000

    async def run(self, state: AgentState) -> AgentState:
        logger.info(f"Memory: processing for task {state.task_id}")
        content, meta = await self.think(state)
        state.context["memory_summary"] = content
        state.history.append({
            "agent": self.name,
            "input": state.input,
            "output": content,
            "meta": meta,
        })
        return state
