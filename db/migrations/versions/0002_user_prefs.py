"""add user model preference

Revision ID: 0002_user_prefs
Revises: 0001_initial
Create Date: 2026-07-22 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_user_prefs"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("model_preference", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "model_preference")
