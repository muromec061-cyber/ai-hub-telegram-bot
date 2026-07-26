"""
Orchestrator — the main agent.

It receives a high-level goal, decides which specialist agent(s) to call,
coordinates them, manages state, and can run multiple tasks in parallel.

This is a LangGraph-style state machine: nodes are agents, edges are decisions.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from agents.base import AgentRole, AgentState, BaseAgent
from agents.specialists import (
    AnalystAgent,
    CoderAgent,
    DeployerAgent,
    MemoryAgent,
    OpenClawAgent,
    PlannerAgent,
    SearcherAgent,
    TesterAgent,
)
from config.env.settings import get_settings
from config.logging import get_logger
from db.models import get_session
from db.repositories import (
    AgentRunRepository,
    MemoryRepository,
    NotificationRepository,
    ProjectRepository,
    TaskRepository,
    UserRepository,
)
from db.models.notification import NotificationType
from db.models.task import TaskStatus
from services.cloudflare.client import CloudflareService
from services.github.client import GitHubService
from services.openclaw import OpenClawClient

logger = get_logger("orchestrator")

ORCHESTRATOR_SYSTEM = """You are the Chief Orchestrator of an AI engineering team.

You decide which specialist agent should handle each part of a user's request.
You are given the goal and current state. Choose the next agent.

Available agents:
- planner: decomposes a goal into ordered steps
- analyst: analyzes requirements, code, data
- searcher: searches the web for information
- coder: writes/modifies code
- tester: writes/runs tests
- deployer: ships code to GitHub + Cloudflare
- memory: stores/retrieves long-term knowledge
- openclaw: hands off complex multi-step goals (build a startup, full project) to a heavyweight external agent (OpenClaw)

Output ONLY valid JSON:
{
  "next_agent": "planner|coder|tester|searcher|deployer|memory|analyst|openclaw|finish",
  "instruction": "specific instructions for the chosen agent",
  "reasoning": "why this agent",
  "is_parallel": false,
  "parallel_with": []
}

Rules:
- Start with "planner" for any non-trivial goal
- After planner, run the steps (coder -> tester -> deployer)
- For a full startup / complex project, use "openclaw" once
- If the user asks a question (not a build task), use "searcher" then "finish"
- Set "is_parallel": true only for clearly independent steps
"""


class Orchestrator(BaseAgent):
    name = "orchestrator"
    role = AgentRole.ORCHESTRATOR
    description = "Chief coordinator: routes work to specialist agents"
    system_prompt = ORCHESTRATOR_SYSTEM
    temperature = 0.2
    max_tokens = 1000

    def __init__(
        self,
        llm=None,
        *,
        base_dir: str = "generated",
        github: GitHubService | None = None,
        cloudflare: CloudflareService | None = None,
        notify_callback=None,
        cluster=None,
    ):
        super().__init__(llm=llm, tools=[])
        self._cluster = cluster
        self.specialists: dict[str, BaseAgent] = {
            "planner": PlannerAgent(llm=llm),
            "analyst": AnalystAgent(llm=llm),
            "searcher": SearcherAgent(llm=llm),
            "coder": CoderAgent(llm=llm, base_dir=base_dir),
            "tester": TesterAgent(llm=llm, base_dir=base_dir),
            "deployer": DeployerAgent(llm=llm, github=github, cloudflare=cloudflare),
            "memory": MemoryAgent(llm=llm),
            "openclaw": OpenClawAgent(llm=llm, cluster=cluster),
        }
        self.base_dir = base_dir
        self.github = github
        self.cloudflare = cloudflare
        self.notify_callback = notify_callback  # async def notify(telegram_id, text)

    async def _ensure_llm(self) -> None:
        """If no LLM is wired and cluster is available, pull one from it."""
        if self.llm is None and self._cluster is not None:
            llm = await self._cluster.get_llm()
            # Wire into all agents
            self.llm = llm
            for agent in self.specialists.values():
                agent.llm = llm

    def get_agent(self, name: str) -> BaseAgent | None:
        return self.specialists.get(name)

    async def decide_next(self, state: AgentState) -> dict:
        """Ask the orchestrator LLM which agent to call next."""
        content, meta = await self.think(state)
        # Parse JSON
        try:
            text = content.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:])
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1:
                return {"next_agent": "finish", "instruction": "", "reasoning": "no JSON", "is_parallel": False}
            decision = json.loads(text[start : end + 1])
        except Exception as e:
            logger.error(f"Orchestrator parse error: {e}")
            return {"next_agent": "finish", "instruction": "", "reasoning": "parse error", "is_parallel": False}
        return decision

    async def run(
        self,
        state: AgentState,
        *,
        max_iterations: int = 20,
    ) -> AgentState:
        """Main orchestration loop. Drives the team until 'finish' or max iterations."""
        logger.info(f"Orchestrator: starting task {state.task_id}")
        for i in range(max_iterations):
            if state.done:
                break
            decision = await self.decide_next(state)
            next_agent_name = decision.get("next_agent", "finish")
            instruction = decision.get("instruction", "")
            logger.info(f"[iter {i}] Next: {next_agent_name} — {decision.get('reasoning', '')}")

            if next_agent_name == "finish" or not next_agent_name:
                state.done = True
                break

            agent = self.specialists.get(next_agent_name)
            if not agent:
                state.errors.append(f"Unknown agent: {next_agent_name}")
                continue

            # Build instruction into state
            if instruction:
                state.input = instruction
            else:
                state.input = state.context.get("original_input", state.input)

            # Run with timing
            start = time.time()
            run_meta = await self._log_run_start(state, agent.name, decision)
            try:
                new_state = await asyncio.wait_for(
                    agent.run(state),
                    timeout=get_settings().task_timeout_seconds,
                )
                duration_ms = int((time.time() - start) * 1000)
                await self._log_run_finish(run_meta["run_id"], new_state, agent.name, duration_ms, success=True)
                state = new_state
            except asyncio.TimeoutError:
                duration_ms = int((time.time() - start) * 1000)
                state.errors.append(f"{agent.name} timed out")
                await self._log_run_finish(run_meta["run_id"], state, agent.name, duration_ms, success=False, error="timeout")
            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)
                state.errors.append(f"{agent.name} error: {e}")
                logger.error(f"Agent {agent.name} failed: {e}")
                await self._log_run_finish(run_meta["run_id"], state, agent.name, duration_ms, success=False, error=str(e))

        return state

    async def _log_run_start(self, state: AgentState, agent_name: str, decision: dict) -> dict:
        if not state.task_id:
            return {"run_id": None}
        async with get_session() as session:
            repo = AgentRunRepository(session)
            run = await repo.create(
                task_id=state.task_id,
                agent_name=agent_name,
                model=self.llm.__class__.__name__,
                status="running",
                input_payload={"input": state.input[:2000], "decision": decision},
            )
            return {"run_id": run.id}

    async def _log_run_finish(
        self,
        run_id: int | None,
        state: AgentState,
        agent_name: str,
        duration_ms: int,
        *,
        success: bool,
        error: str | None = None,
    ) -> None:
        if not run_id:
            return
        try:
            async with get_session() as session:
                repo = AgentRunRepository(session)
                last = next((h for h in reversed(state.history) if h.get("agent") == agent_name), {})
                await repo.finish_run(
                    run_id,
                    output={"history_step": last},
                    duration_ms=duration_ms,
                    error=error,
                    status="success" if success else "failed",
                )
        except Exception as e:
            logger.error(f"Failed to log run finish: {e}")

    async def run_for_task(
        self,
        task_id: int,
        user_id: int,
        input_text: str,
        *,
        project_id: int | None = None,
        max_iterations: int = 20,
    ) -> AgentState:
        """High-level entry: load context from DB, run, save back."""
        async with get_session() as session:
            user_repo = UserRepository(session)
            task_repo = TaskRepository(session)
            project_repo = ProjectRepository(session)
            user = await user_repo.get(user_id)
            task = await task_repo.get(task_id)
            if not user or not task:
                raise ValueError("User or task not found")

            await task_repo.set_status(task_id, TaskStatus.RUNNING)

            project = None
            if project_id or task.project_id:
                project = await project_repo.get(project_id or task.project_id)

        # Build initial state
        state = AgentState(
            task_id=task_id,
            user_id=user_id,
            project_id=project.id if project else None,
            input=input_text,
            context={
                "original_input": input_text,
                "project_type": project.project_type if project else "general",
                "project_name": project.name if project else f"project-{task_id}",
                "project_dir": f"{self.base_dir}/{project.name if project else f'project-{task_id}'}",
                "user_language": user.language_code,
                "user_role": user.role.value,
            },
        )

        # Run
        try:
            final_state = await self.run(state, max_iterations=max_iterations)
        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            async with get_session() as session:
                await TaskRepository(session).set_status(task_id, TaskStatus.FAILED, error=str(e))
            raise

        # Save results
        async with get_session() as session:
            task_repo = TaskRepository(session)
            notif_repo = NotificationRepository(session)
            memory_repo = MemoryRepository(session)
            status = TaskStatus.COMPLETED if not final_state.errors else TaskStatus.FAILED
            await task_repo.set_status(
                task_id,
                status,
                result={
                    "artifacts": final_state.artifacts,
                    "context": {k: v for k, v in final_state.context.items() if not k.startswith("_")},
                },
                error="\n".join(final_state.errors) if final_state.errors else None,
            )
            # Notification
            await notif_repo.create(
                user_id=user_id,
                type=NotificationType.TASK_COMPLETED if status == TaskStatus.COMPLETED else NotificationType.TASK_FAILED,
                title=f"Task #{task_id} {status.value}",
                message=input_text[:500],
                payload={"task_id": task_id, "artifacts": final_state.artifacts},
            )
            # Memory: store summary
            summary = self._summarize_run(final_state)
            if summary:
                await memory_repo.create(
                    user_id=user_id,
                    project_id=project.id if project else None,
                    memory_type="task_summary",
                    scope="user",
                    title=f"Task #{task_id}: {input_text[:200]}",
                    content=summary,
                    summary=summary[:500],
                    importance=0.6,
                    tags=["task"],
                )
            # Update project status
            if project and status == TaskStatus.COMPLETED:
                await ProjectRepository(session).set_status(project.id, "active")

        # Push Telegram notification
        if self.notify_callback:
            try:
                text = f"✅ Task #{task_id} done\n{input_text[:200]}\n\n"
                if final_state.artifacts.get("deployed_url"):
                    text += f"🌐 Live: {final_state.artifacts['deployed_url']}\n"
                if final_state.artifacts.get("github_url"):
                    text += f"📦 Repo: {final_state.artifacts['github_url']}\n"
                if final_state.errors:
                    text += f"\n⚠️ Errors:\n" + "\n".join(final_state.errors[:5])
                async with get_session() as session:
                    user = await UserRepository(session).get(user_id)
                if user:
                    await self.notify_callback(user.telegram_id, text)
            except Exception as e:
                logger.error(f"Notification failed: {e}")

        return final_state

    @staticmethod
    def _summarize_run(state: AgentState) -> str:
        parts = [f"Input: {state.input[:300]}"]
        for step in state.history[-5:]:
            parts.append(f"- {step.get('agent')}: {str(step.get('output', ''))[:200]}")
        if state.artifacts:
            parts.append(f"Artifacts: {json.dumps(state.artifacts, default=str)[:500]}")
        return "\n".join(parts)
