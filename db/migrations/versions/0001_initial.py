"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), unique=True, index=True, nullable=False),
        sa.Column("username", sa.String(64), nullable=True, index=True),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("language_code", sa.String(8), server_default="en"),
        sa.Column("role", sa.Enum("user", "pro", "team", "admin", "owner", name="userrole"), server_default="user", index=True),
        sa.Column("status", sa.Enum("active", "blocked", "pending", "deleted", name="userstatus"), server_default="active", index=True),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_type", sa.String(64), server_default="general", index=True),
        sa.Column("status", sa.Enum("draft", "active", "paused", "completed", "failed", "archived", name="projectstatus"), server_default="draft", index=True),
        sa.Column("github_repo_url", sa.String(500), nullable=True),
        sa.Column("github_repo_name", sa.String(200), nullable=True),
        sa.Column("deployed_url", sa.String(500), nullable=True),
        sa.Column("cloudflare_deployment_id", sa.String(200), nullable=True),
        sa.Column("tech_stack", sa.JSON(), server_default="{}"),
        sa.Column("config", sa.JSON(), server_default="{}"),
        sa.Column("tags", sa.JSON(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True),
        sa.Column("parent_task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=True),
        sa.Column("creator_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("assigned_agent", sa.String(64), index=True, nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("queued", "planning", "running", "waiting", "testing", "completed", "failed", "cancelled", "timeout", name="taskstatus"), server_default="queued", index=True),
        sa.Column("priority", sa.Enum("low", "normal", "high", "urgent", name="taskpriority"), server_default="normal", index=True),
        sa.Column("chain", sa.JSON(), server_default="[]"),
        sa.Column("current_step", sa.Integer(), server_default="0"),
        sa.Column("attempts", sa.Integer(), server_default="0"),
        sa.Column("max_attempts", sa.Integer(), server_default="3"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("artifacts", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("agent_name", sa.String(64), index=True, nullable=False),
        sa.Column("model", sa.String(128), server_default="unknown"),
        sa.Column("status", sa.Enum("started", "running", "success", "failed", "timeout", "cancelled", name="agentrunstatus"), server_default="started", index=True),
        sa.Column("input_payload", sa.JSON(), server_default="{}"),
        sa.Column("output", sa.JSON(), server_default="{}"),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), server_default="0"),
        sa.Column("tokens_out", sa.Integer(), server_default="0"),
        sa.Column("duration_ms", sa.Integer(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "memory_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True),
        sa.Column("memory_type", sa.String(64), index=True),
        sa.Column("scope", sa.String(32), server_default="user", index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=True),
        sa.Column("tags", sa.JSON(), server_default="[]"),
        sa.Column("extra", sa.JSON(), server_default="{}"),
        sa.Column("vector_id", sa.String(128), nullable=True, index=True),
        sa.Column("importance", sa.Float(), server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), server_default="0"),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        sa.Column("plan", sa.Enum("free", "pro", "team", "business", name="subscriptionplan"), server_default="free"),
        sa.Column("status", sa.Enum("active", "trial", "expired", "cancelled", "past_due", name="subscriptionstatus"), server_default="active"),
        sa.Column("monthly_tokens", sa.Integer(), server_default="100000"),
        sa.Column("tokens_used", sa.Integer(), server_default="0"),
        sa.Column("monthly_projects", sa.Integer(), server_default="3"),
        sa.Column("projects_used", sa.Integer(), server_default="0"),
        sa.Column("parallel_tasks", sa.Integer(), server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("payment_provider", sa.String(64), nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("extra", sa.JSON(), server_default="{}"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("type", sa.Enum("info", "success", "warning", "error", "task_completed", "task_failed", "deployment", "billing", name="notificationtype"), server_default="info"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), server_default="{}"),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("action", sa.String(128), index=True, nullable=False),
        sa.Column("resource", sa.String(128), nullable=True),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("details", sa.JSON(), server_default="{}"),
        sa.Column("status", sa.String(32), server_default="success", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_user_action_time", "audit_logs", ["user_id", "action", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_user_action_time", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("subscriptions")
    op.drop_table("memory_entries")
    op.drop_table("agent_runs")
    op.drop_table("tasks")
    op.drop_table("projects")
    op.drop_table("users")
