"""add voice preset source metadata

Revision ID: 20260514_01
Revises: 20260512_02
Create Date: 2026-05-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_01"
down_revision = "20260512_02"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "voice_presets" not in table_names:
        return

    columns = [
        ("source_provider", sa.String(length=100)),
        ("source_url", sa.String(length=2048)),
        ("transcript_source_url", sa.String(length=2048)),
        ("license_label", sa.String(length=255)),
        ("provenance_note", sa.Text()),
    ]
    for column_name, column_type in columns:
        if not _has_column(inspector, "voice_presets", column_name):
            op.add_column("voice_presets", sa.Column(column_name, column_type, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "voice_presets" not in table_names:
        return

    for column_name in (
        "provenance_note",
        "license_label",
        "transcript_source_url",
        "source_url",
        "source_provider",
    ):
        if _has_column(inspector, "voice_presets", column_name):
            op.drop_column("voice_presets", column_name)
