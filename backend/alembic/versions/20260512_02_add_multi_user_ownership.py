"""add multi-user ownership columns

Revision ID: 20260512_02
Revises: 20260512_01
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260512_02"
down_revision = "20260512_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "user_settings" not in table_names:
        op.create_table(
            "user_settings",
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("user_id", "key"),
        )

    _add_column_if_missing(inspector, "documents", "owner_user_id")
    _add_column_if_missing(inspector, "playback_sessions", "user_id")
    _add_column_if_missing(inspector, "collections", "owner_user_id")
    _add_column_if_missing(inspector, "jobs", "user_id")
    _add_column_if_missing(inspector, "voice_presets", "owner_user_id")
    _add_column_if_missing(inspector, "theme_profiles", "owner_user_id")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    _drop_column_if_present(inspector, "theme_profiles", "owner_user_id")
    _drop_column_if_present(inspector, "voice_presets", "owner_user_id")
    _drop_column_if_present(inspector, "jobs", "user_id")
    _drop_column_if_present(inspector, "collections", "owner_user_id")
    _drop_column_if_present(inspector, "playback_sessions", "user_id")
    _drop_column_if_present(inspector, "documents", "owner_user_id")
    if "user_settings" in table_names:
        op.drop_table("user_settings")


def _add_column_if_missing(
    inspector: sa.Inspector,
    table_name: str,
    column_name: str,
) -> None:
    if table_name not in inspector.get_table_names():
        return
    if column_name in {column["name"] for column in inspector.get_columns(table_name)}:
        return
    op.add_column(table_name, sa.Column(column_name, sa.Integer(), nullable=True))


def _drop_column_if_present(
    inspector: sa.Inspector,
    table_name: str,
    column_name: str,
) -> None:
    if table_name not in inspector.get_table_names():
        return
    if column_name not in {column["name"] for column in inspector.get_columns(table_name)}:
        return
    op.drop_column(table_name, column_name)
