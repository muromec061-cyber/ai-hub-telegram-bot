"""Deployer agent — ships code to Cloudflare / GitHub / Docker."""
from __future__ import annotations

import json

from agents.base import AgentRole, AgentState, BaseAgent
from config.logging import get_logger
from services.cloudflare.client import CloudflareService
from services.github.client import GitHubService

logger = get_logger("agent.deployer")

DEPLOYER_SYSTEM = """You are a deployment engineer.

You take a working codebase and ship it:
- Push to GitHub
- Deploy to Cloudflare (Workers / Pages / R2)
- Build Docker image if needed
- Configure environment

You report:
- Repo URL
- Live URL
- Deployment ID
- Status (success/failure)
- Any follow-up steps
"""


class DeployerAgent(BaseAgent):
    name = "deployer"
    role = AgentRole.DEPLOYER
    description = "Deploys code to GitHub, Cloudflare, Docker"
    system_prompt = DEPLOYER_SYSTEM
    temperature = 0.2
    max_tokens = 3000

    def __init__(self, llm=None, *, github: GitHubService | None = None, cloudflare: CloudflareService | None = None):
        self.github = github
        self.cloudflare = cloudflare
        super().__init__(llm=llm, tools=[])

    async def run(self, state: AgentState) -> AgentState:
        logger.info(f"Deployer: deploying task {state.task_id}")
        result = {"github_url": None, "deployed_url": None, "deployment_id": None, "logs": []}

        # 1. Push to GitHub
        if self.github and state.context.get("project_dir"):
            try:
                project_name = state.context.get("project_name", f"project-{state.task_id}")
                repo_url = await self.github.create_or_update_repo(
                    project_name,
                    description=state.context.get("plan_summary", ""),
                    local_dir=state.context["project_dir"],
                )
                result["github_url"] = repo_url
                result["logs"].append(f"GitHub: {repo_url}")
            except Exception as e:
                result["logs"].append(f"GitHub push failed: {e}")
                logger.error(f"GitHub push failed: {e}")

        # 2. Deploy to Cloudflare (Pages / Workers)
        if self.cloudflare and state.context.get("project_type") in ("site", "static", "webapp"):
            try:
                deploy_result = await self.cloudflare.deploy_pages(
                    project_name=state.context.get("project_name", f"site-{state.task_id}"),
                    directory=state.context.get("project_dir", "."),
                )
                result["deployed_url"] = deploy_result.get("url")
                result["deployment_id"] = deploy_result.get("id")
                result["logs"].append(f"Cloudflare: {deploy_result.get('url')}")
            except Exception as e:
                result["logs"].append(f"Cloudflare deploy failed: {e}")
                logger.error(f"Cloudflare deploy failed: {e}")

        state.context["deployment"] = result
        state.artifacts["github_url"] = result.get("github_url")
        state.artifacts["deployed_url"] = result.get("deployed_url")
        state.history.append({
            "agent": self.name,
            "input": state.input,
            "output": json.dumps(result, indent=2),
            "meta": {},
        })
        return state
