"""Coder agent — writes, modifies, and debugs code."""
from __future__ import annotations

import json
from datetime import datetime

from agents.base import AgentRole, AgentState, BaseAgent, Tool
from agents.tools import code_tools
from config.logging import get_logger

logger = get_logger("agent.coder")

CODER_SYSTEM = """You are an expert senior software engineer.

You write production-quality, well-structured, tested code. You:
- Choose appropriate languages and frameworks
- Follow project conventions
- Add docstrings and comments
- Write tests when relevant
- Consider security, performance, and edge cases
- Prefer clear, maintainable code over clever tricks

You can use these tools:
- write_file(path, content): create or overwrite a file
- read_file(path): read existing file
- list_files(directory): list project files
- run_python(code): execute Python code
- run_shell(command): run shell command
- run_tests(project_dir): run tests

When given a task:
1. Briefly explain your plan
2. Use tools to create/modify files
3. Verify the result (run tests, check syntax)
4. Report what you did and any artifacts produced
"""


class CoderAgent(BaseAgent):
    name = "coder"
    role = AgentRole.CODER
    description = "Writes, modifies, and debugs code in any language"
    system_prompt = CODER_SYSTEM
    temperature = 0.2
    max_tokens = 8000

    def __init__(self, llm=None, *, base_dir: str = "generated"):
        self.base_dir = base_dir
        tools = [
            Tool(
                name="write_file",
                description="Create or overwrite a file with given content. Path is relative to project.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path"},
                        "content": {"type": "string", "description": "Full file content"},
                    },
                    "required": ["path", "content"],
                },
                func=lambda path, content: code_tools.write_file(path, content, base_dir=base_dir),
            ),
            Tool(
                name="read_file",
                description="Read an existing file's content",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                func=lambda path: code_tools.read_file(path, base_dir=base_dir),
            ),
            Tool(
                name="list_files",
                description="List all files in a directory",
                parameters={
                    "type": "object",
                    "properties": {"directory": {"type": "string", "default": "."}},
                },
                func=lambda directory=".": code_tools.list_files(directory, base_dir=base_dir),
            ),
            Tool(
                name="run_python",
                description="Execute Python code and return output",
                parameters={
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                },
                func=code_tools.run_python,
            ),
            Tool(
                name="run_shell",
                description="Run a shell command in the project directory",
                parameters={
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
                func=lambda command: code_tools.run_shell(command, cwd=base_dir),
            ),
            Tool(
                name="run_tests",
                description="Run the test suite for a project",
                parameters={
                    "type": "object",
                    "properties": {"project_dir": {"type": "string"}},
                    "required": ["project_dir"],
                },
                func=lambda project_dir: code_tools.run_tests(project_dir, base_dir=base_dir),
            ),
        ]
        super().__init__(llm=llm, tools=tools)

    async def run(self, state: AgentState) -> AgentState:
        logger.info(f"Coder: working on task {state.task_id}")
        prompt = f"""Task: {state.input}

Project context: {state.context.get('project_type', 'general')}
Existing files: {state.context.get('existing_files', 'none')}

{f"Additional context: {json.dumps(state.context, default=str)[:2000]}" if state.context else ""}

Build or modify the code as needed. Use the tools. When done, summarize what you built."""

        # We loop on tool calls up to N times
        iterations = 0
        max_iter = 8
        last_response = None
        while iterations < max_iter:
            iterations += 1
            try:
                response = await self.llm.complete(
                    self._build_request(state, prompt)
                )
            except Exception as e:
                logger.error(f"Coder LLM error: {e}")
                state.errors.append(str(e))
                break

            tool_calls = response.tool_calls
            if not tool_calls:
                last_response = response
                break

            # Execute tools
            tool_results = []
            for tc in tool_calls:
                logger.info(f"Coder executing tool: {tc['name']}")
                result = await self.execute_tool(tc["name"], tc["arguments"])
                tool_results.append({
                    "tool_call_id": tc["id"],
                    "name": tc["name"],
                    "result": str(result)[:4000],
                })
                # Track artifacts
                if tc["name"] == "write_file":
                    state.artifacts.setdefault("files", []).append(tc["arguments"]["path"])

            # Add tool results to messages and loop
            state.context.setdefault("_tool_history", []).append({
                "assistant": response.content,
                "tools": tool_results,
            })

        if last_response is None:
            # build a final response from context
            state.history.append({
                "agent": self.name,
                "input": state.input,
                "output": "Coder executed tool loop without final summary",
                "meta": {},
            })
            return state

        state.history.append({
            "agent": self.name,
            "input": state.input,
            "output": last_response.content,
            "meta": {
                "tokens_in": last_response.tokens_in,
                "tokens_out": last_response.tokens_out,
                "iterations": iterations,
                "files_created": state.artifacts.get("files", []),
            },
        })
        state.context["coder_output"] = last_response.content
        state.context["coder_files"] = state.artifacts.get("files", [])
        return state

    def _build_request(self, state, prompt):
        from services.llm import LLMMessage, LLMRequest
        messages = self._build_messages(state, prompt)
        # Inject tool history
        for turn in state.context.get("_tool_history", [])[-3:]:
            messages.append({"role": "assistant", "content": turn["assistant"]})
        # Actually we need to inject as proper LLMMessage - convert last
        from services.llm import LLMMessage as LM
        full_messages = [m for m in messages if isinstance(m, LM)]
        # Append last tool turns
        for turn in state.context.get("_tool_history", [])[-3:]:
            full_messages.append(LM(role="assistant", content=turn.get("assistant") or ""))
            for tr in turn.get("tools", []):
                full_messages.append(LM(
                    role="tool",
                    name=tr["name"],
                    content=tr["result"][:3000],
                    tool_call_id=tr["tool_call_id"],
                ))
        return LLMRequest(
            messages=full_messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self.get_openai_tools(),
        )
