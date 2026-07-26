"""Tester agent — runs and writes tests, validates code."""
from __future__ import annotations

import json

from agents.base import AgentRole, AgentState, BaseAgent, Tool
from agents.tools import code_tools
from config.logging import get_logger

logger = get_logger("agent.tester")

TESTER_SYSTEM = """You are a senior QA engineer.

You:
- Write comprehensive test suites (unit, integration)
- Run tests and report results
- Identify edge cases and bugs
- Suggest fixes
- Verify code quality

Given code and a goal, produce or run tests, then return:
- PASS / FAIL summary
- Detailed test output
- Specific failures with file:line and suggested fix
"""


class TesterAgent(BaseAgent):
    name = "tester"
    role = AgentRole.TESTER
    description = "Writes and runs tests, validates implementations"
    system_prompt = TESTER_SYSTEM
    temperature = 0.2
    max_tokens = 4000

    def __init__(self, llm=None, *, base_dir: str = "generated"):
        self.base_dir = base_dir
        tools = [
            Tool(
                name="run_tests",
                description="Run pytest in a project",
                parameters={
                    "type": "object",
                    "properties": {"project_dir": {"type": "string"}},
                    "required": ["project_dir"],
                },
                func=lambda project_dir: code_tools.run_tests(project_dir, base_dir=base_dir),
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
                name="write_file",
                description="Write a file (e.g. test file)",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
                func=lambda path, content: code_tools.write_file(path, content, base_dir=base_dir),
            ),
            Tool(
                name="read_file",
                description="Read a file",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                func=lambda path: code_tools.read_file(path, base_dir=base_dir),
            ),
        ]
        super().__init__(llm=llm, tools=tools)

    async def run(self, state: AgentState) -> AgentState:
        logger.info(f"Tester: validating task {state.task_id}")
        project_dir = state.context.get("project_dir", ".")
        prompt = f"""Task: {state.input}

Project: {project_dir}
Context: {json.dumps(state.context, default=str)[:2000]}

Run tests, analyze results, and report."""
        content, meta = await self.think(state, extra_input=prompt)
        state.context["test_results"] = content
        state.history.append({
            "agent": self.name,
            "input": state.input,
            "output": content,
            "meta": meta,
        })
        # Mark pass/fail
        if "PASS" in content.upper() and "FAIL" not in content.upper():
            state.context["tests_passed"] = True
        else:
            state.context["tests_passed"] = False
        return state
