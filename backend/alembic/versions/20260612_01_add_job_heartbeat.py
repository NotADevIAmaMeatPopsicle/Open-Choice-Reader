"""add job heartbeat

Revision ID: 20260612_01
Revises: 20260514_01
Create Date: 2026-06-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260612_01"
down_revision = "20260514_01"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "jobs" not in set(inspector.get_table_names()):
        return

    if not _has_column(inspector, "jobs", "heartbeat_at"):
        op.add_column("jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "jobs" not in set(inspector.get_table_names()):
        return

    if _has_column(inspector, "jobs", "heartbeat_at"):
        op.drop_column("jobs", "heartbeat_at")
