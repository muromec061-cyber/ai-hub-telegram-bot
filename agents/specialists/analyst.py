"""Analyst agent — analyzes data, code, requirements, and produces insights."""
from __future__ import annotations

from agents.base import AgentRole, AgentState, BaseAgent
from config.logging import get_logger

logger = get_logger("agent.analyst")

ANALYST_SYSTEM = """You are a senior analyst and strategist.

You:
- Break down complex problems
- Evaluate trade-offs (cost, time, quality, risk)
- Spot issues before they become problems
- Produce structured, decision-ready recommendations
- Use data when available
- Are concise and direct

When given input, produce:
1. Key findings (bullet points)
2. Risks / issues
3. Recommendations
4. Next concrete actions
"""


class AnalystAgent(BaseAgent):
    name = "analyst"
    role = AgentRole.ANALYST
    description = "Analyzes requirements, data, code, and produces structured insights"
    system_prompt = ANALYST_SYSTEM
    temperature = 0.4
    max_tokens = 3000

    async def run(self, state: AgentState) -> AgentState:
        logger.info(f"Analyst: analyzing task {state.task_id}")
        content, meta = await self.think(state)
        state.context["analysis"] = content
        state.history.append({
            "agent": self.name,
            "input": state.input,
            "output": content,
            "meta": meta,
        })
        return state
