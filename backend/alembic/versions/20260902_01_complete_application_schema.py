"""complete the application schema for clean installations

Revision ID: 20260902_01
Revises: 20260612_02
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260902_01"
down_revision = "20260612_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collections_owner_user_id", "collections", ["owner_user_id"])
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source_path", sa.String(length=1024), nullable=False),
        sa.Column("origin_path", sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_owner_user_id", "documents", ["owner_user_id"])
    op.create_table(
        "theme_profiles",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_label", sa.String(length=255), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(length=64), nullable=False),
        sa.Column("preview_variant", sa.String(length=64), nullable=False),
        sa.Column("background_asset_path", sa.String(length=255), nullable=True),
        sa.Column("background_overlay_path", sa.String(length=255), nullable=True),
        sa.Column("shelf_asset_path", sa.String(length=255), nullable=True),
        sa.Column("surface_texture_asset_path", sa.String(length=255), nullable=True),
        sa.Column("supports_mix_and_match", sa.Boolean(), nullable=False),
        sa.Column("tokens_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_theme_profiles_owner_user_id", "theme_profiles", ["owner_user_id"])
    op.create_table(
        "voice_presets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("engine", sa.String(length=50), nullable=False),
        sa.Column("reference_path", sa.String(length=1024), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("source_provider", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("transcript_source_url", sa.String(length=2048), nullable=True),
        sa.Column("license_label", sa.String(length=255), nullable=True),
        sa.Column("provenance_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_presets_owner_user_id", "voice_presets", ["owner_user_id"])
    op.create_table(
        "collection_documents",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("collection_id", "document_id"),
    )
    op.create_table(
        "document_profiles",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("cover_path", sa.String(length=1024), nullable=True),
        sa.Column("metadata_source", sa.String(length=64), nullable=True),
        sa.Column("metadata_source_id", sa.String(length=255), nullable=True),
        sa.Column("source_provider", sa.String(length=64), nullable=True),
        sa.Column("source_provider_id", sa.String(length=255), nullable=True),
        sa.Column("source_provider_name", sa.String(length=255), nullable=True),
        sa.Column("source_provider_url", sa.String(length=1024), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("source_site_name", sa.String(length=255), nullable=True),
        sa.Column("import_mode", sa.String(length=64), nullable=True),
        sa.Column("total_sections", sa.Integer(), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_table(
        "document_progress",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("current_chunk_index", sa.Integer(), nullable=False),
        sa.Column("bookmark_enabled", sa.Boolean(), nullable=False),
        sa.Column("has_bookmark", sa.Boolean(), nullable=False),
        sa.Column("is_finished", sa.Boolean(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("voice_preset_id", sa.String(length=255), nullable=False),
        sa.Column("clone_engine_id", sa.String(length=255), nullable=True),
        sa.Column("format", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("split_chapters", sa.Boolean(), nullable=False),
        sa.Column("artifact_basename", sa.String(length=255), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("status_detail", sa.String(length=255), nullable=True),
        sa.Column("artifact_path", sa.String(length=1024), nullable=True),
        sa.Column("artifact_manifest", sa.Text(), nullable=True),
        sa.Column("failure_detail", sa.String(length=1024), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_document_id", "jobs", ["document_id"])
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sections_document_id", "sections", ["document_id"])
    op.create_table(
        "text_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_text_chunks_section_id", "text_chunks", ["section_id"])
    op.create_table(
        "playback_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("current_chunk_index", sa.Integer(), nullable=False),
        sa.Column("engine_name", sa.String(length=50), nullable=False),
        sa.Column("voice_option_id", sa.String(length=255), nullable=True),
        sa.Column("playback_speed", sa.Float(), nullable=False),
        sa.Column("audio_path", sa.String(length=1024), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["text_chunks.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playback_sessions_chunk_id", "playback_sessions", ["chunk_id"])
    op.create_index("ix_playback_sessions_document_id", "playback_sessions", ["document_id"])
    op.create_index("ix_playback_sessions_user_id", "playback_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_playback_sessions_user_id", table_name="playback_sessions")
    op.drop_index("ix_playback_sessions_document_id", table_name="playback_sessions")
    op.drop_index("ix_playback_sessions_chunk_id", table_name="playback_sessions")
    op.drop_table("playback_sessions")
    op.drop_index("ix_text_chunks_section_id", table_name="text_chunks")
    op.drop_table("text_chunks")
    op.drop_index("ix_sections_document_id", table_name="sections")
    op.drop_table("sections")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_index("ix_jobs_document_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("document_progress")
    op.drop_table("document_profiles")
    op.drop_table("collection_documents")
    op.drop_index("ix_voice_presets_owner_user_id", table_name="voice_presets")
    op.drop_table("voice_presets")
    op.drop_index("ix_theme_profiles_owner_user_id", table_name="theme_profiles")
    op.drop_table("theme_profiles")
    op.drop_index("ix_documents_owner_user_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_collections_owner_user_id", table_name="collections")
    op.drop_table("collections")
    op.drop_table("app_settings")
