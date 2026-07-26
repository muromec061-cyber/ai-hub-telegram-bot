"""
Base agent class — all agents inherit from this.
Provides: state management, tool registry, memory access, LLM calls.
"""
from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from config.logging import get_logger
from services.llm import LLMMessage, LLMProvider, LLMRequest, get_llm_provider

logger = get_logger("agent.base")


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    CODER = "coder"
    ANALYST = "analyst"
    SEARCHER = "searcher"
    TESTER = "tester"
    DEPLOYER = "deployer"
    MEMORY = "memory"


@dataclass
class AgentState:
    """Shared state passed between agents in a workflow."""
    task_id: int | None = None
    user_id: int | None = None
    project_id: int | None = None
    input: str = ""
    context: dict = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)  # steps taken
    artifacts: dict = field(default_factory=dict)  # produced files, urls, etc.
    errors: list[str] = field(default_factory=list)
    next_agent: str | None = None
    done: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "input": self.input,
            "context": self.context,
            "history": self.history,
            "artifacts": self.artifacts,
            "errors": self.errors,
            "next_agent": self.next_agent,
            "done": self.done,
            "metadata": self.metadata,
        }


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema
    func: Callable[..., Any]

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class BaseAgent(ABC):
    """Base class for all agents."""

    name: str = "base"
    role: AgentRole = AgentRole.ORCHESTRATOR
    description: str = "Base agent"
    system_prompt: str = "You are a helpful AI assistant."
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096

    def __init__(self, llm: LLMProvider | None = None, tools: list[Tool] | None = None):
        self.llm = llm or get_llm_provider()
        self.tools: dict[str, Tool] = {t.name: t for t in (tools or [])}
        self.id = str(uuid.uuid4())[:8]

    def add_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get_openai_tools(self) -> list[dict]:
        return [t.to_openai_schema() for t in self.tools.values()]

    def _build_messages(self, state: AgentState, extra_input: str | None = None) -> list[LLMMessage]:
        messages = [LLMMessage(role="system", content=self.system_prompt)]
        # Add history
        for step in state.history[-10:]:
            agent_name = step.get("agent", "agent")
            content = step.get("output", "")
            if content:
                messages.append(LLMMessage(role="assistant", content=f"[{agent_name}]: {content[:2000]}"))
        # Current input
        user_content = state.input
        if extra_input:
            user_content = f"{user_content}\n\n{extra_input}" if user_content else extra_input
        if state.context:
            user_content += f"\n\nContext:\n{json.dumps(state.context, indent=2, default=str)[:3000]}"
        messages.append(LLMMessage(role="user", content=user_content or "Proceed with the task."))
        return messages

    async def think(self, state: AgentState, extra_input: str | None = None) -> tuple[str, dict]:
        """Call LLM and return (content, response_meta)."""
        messages = self._build_messages(state, extra_input)
        request = LLMRequest(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self.get_openai_tools() if self.tools else None,
        )
        try:
            response = await self.llm.complete(request)
            return response.content, {
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
                "model": response.model,
                "tool_calls": response.tool_calls,
                "finish_reason": response.finish_reason,
            }
        except Exception as e:
            logger.error(f"LLM call failed in {self.name}: {e}")
            raise

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not registered for agent {self.name}")
        tool = self.tools[tool_name]
        try:
            if asyncio_iscoroutinefunction(tool.func):
                return await tool.func(**arguments)
            return tool.func(**arguments)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e)}

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """Execute the agent on the current state. Returns updated state."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id} role={self.role.value}>"


def asyncio_iscoroutinefunction(func) -> bool:
    import inspect
    return inspect.iscoroutinefunction(func)
