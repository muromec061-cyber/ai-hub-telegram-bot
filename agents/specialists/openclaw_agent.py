"""
OpenClaw Agent — hands off complex goals to a running OpenClaw sidecar.

OpenClaw (github.com/openclaw/openclaw) is a heavy-weight personal AI agent
that handles full-stack projects: code, test, deploy, build startups, etc.
We call it via HTTP and stream progress back.
"""
from __future__ import annotations

from agents.base import AgentRole, AgentState, BaseAgent
from config.logging import get_logger

logger = get_logger("agent.openclaw")

OPENCLAW_SYSTEM = """You are the OpenClaw bridge agent.

When the user wants a complex project (full startup, multi-component app,
Telegram bot, SaaS, etc.), you delegate the goal to OpenClaw, which runs
autonomously, writes code, tests, and deploys. You receive a final report
and summarize it for the user.

Output: a short, structured report of what OpenClaw did and any artifacts."""


class OpenClawAgent(BaseAgent):
    name = "openclaw"
    role = AgentRole.ORCHESTRATOR  # coordinator role
    description = "Delegates complex projects to OpenClaw (external sidecar)"
    system_prompt = OPENCLAW_SYSTEM
    temperature = 0.3
    max_tokens = 1500

    def __init__(self, llm=None, *, cluster=None):
        super().__init__(llm=llm, tools=[])
        self._cluster = cluster

    async def run(self, state: AgentState) -> AgentState:
        if not self._cluster:
            state.errors.append("OpenClaw: cluster not configured")
            return state

        client = await self._cluster.openclaw()
        if not client:
            state.errors.append("OpenClaw: not enabled in settings (set OPENCLAW_ENABLED=true and OPENCLAW_GATEWAY_URL)")
            state.context["openclaw_output"] = "⚠️ OpenClaw не подключен. Запустите OpenClaw sidecar и поставьте OPENCLAW_ENABLED=true в .env"
            return state

        logger.info(f"OpenClaw: delegating goal to {client.gateway_url}")
        result = await client.run_goal(
            goal=state.input,
            context=state.context,
            channel="telegram",
            user_id=str(state.user_id) if state.user_id else None,
            timeout=600,
        )

        state.context["openclaw_output"] = str(result)[:5000]
        if result.get("ok") is False:
            state.errors.append(f"OpenClaw: {result.get('error', 'unknown error')}")

        # Pick out artifacts
        for key in ("github_url", "deployed_url", "files", "artifacts"):
            if isinstance(result, dict) and key in result:
                state.artifacts[key] = result[key]

        # Summary via our LLM
        if self.llm:
            try:
                content, meta = await self.think(state, extra_input=f"OpenClaw result:\n{str(result)[:2000]}")
                state.context["openclaw_summary"] = content
            except Exception as e:
                logger.warning(f"OpenClaw summary LLM call failed: {e}")

        state.history.append({
            "agent": self.name,
            "input": state.input,
            "output": str(result)[:1000],
            "meta": {},
        })
        return state
