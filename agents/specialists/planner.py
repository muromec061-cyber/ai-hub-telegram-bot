"""Planner agent — breaks down a goal into a sequence of subtasks."""
from __future__ import annotations

import json

from agents.base import AgentRole, AgentState, BaseAgent, Tool
from agents.tools import web_search
from config.logging import get_logger

logger = get_logger("agent.planner")

PLANNER_SYSTEM = """You are a senior technical project planner.

Your job: take a high-level goal and produce a CONCRETE, ORDERED plan
with 3-12 steps. Each step must be a clear, atomic action another agent
can execute.

Output ONLY valid JSON in this exact format:
{
  "summary": "Short description of overall approach",
  "steps": [
    {
      "id": 1,
      "title": "Step title",
      "description": "Detailed description of what to do",
      "agent": "coder|analyst|searcher|tester|deployer|memory",
      "depends_on": [],
      "estimated_minutes": 5,
      "deliverable": "What this step produces"
    }
  ]
}

Rules:
- Use realistic agents (coder writes code, analyst analyzes data, searcher finds info, tester validates, deployer ships, memory stores knowledge)
- Steps should have minimal dependencies (parallel where possible)
- Be specific: instead of "build the app", say "create FastAPI app with /api/users endpoint and SQLAlchemy model"
- Include setup, implementation, testing, and deployment steps
- If you need external info, mark a step as agent=searcher
"""


class PlannerAgent(BaseAgent):
    name = "planner"
    role = AgentRole.PLANNER
    description = "Decomposes goals into ordered, parallelizable subtasks"
    system_prompt = PLANNER_SYSTEM
    temperature = 0.3
    max_tokens = 4096

    def __init__(self, llm=None):
        tools = [
            Tool(
                name="web_search",
                description="Search the web for information",
                parameters={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                func=web_search,
            )
        ]
        super().__init__(llm=llm, tools=tools)

    async def run(self, state: AgentState) -> AgentState:
        logger.info(f"Planner: planning for task {state.task_id}")
        prompt = f"""Goal: {state.input}

Context: {json.dumps(state.context, default=str)[:2000]}

Produce a detailed plan as JSON. Be concrete and actionable."""
        content, meta = await self.think(state, extra_input=prompt)

        # Parse JSON
        plan = self._extract_json(content)
        if not plan:
            logger.error("Planner: failed to extract plan JSON")
            state.errors.append("Planner: invalid plan output")
            return state

        state.context["plan"] = plan
        state.context["plan_summary"] = plan.get("summary", "")
        state.context["plan_steps"] = plan.get("steps", [])
        state.history.append({
            "agent": self.name,
            "input": state.input,
            "output": content[:1000],
            "meta": meta,
        })
        logger.info(f"Planner: created {len(plan.get('steps', []))} steps")
        return state

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        text = text.strip()
        # Try to find JSON block
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        # Find the first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
