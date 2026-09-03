from collections.abc import Iterator
from contextlib import contextmanager
from importlib import import_module, reload
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def _sqlite_connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    settings.database_url,
    future=True,
    connect_args=_sqlite_connect_args(settings.database_url),
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def init_database() -> None:
    database_path = make_url(settings.database_url).database
    if database_path:
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    from app.models import Base

    module_tables = {
        "app.models.app_setting": {"app_settings"},
        "app.models.auth_session": {"auth_sessions"},
        "app.models.collection": {"collections", "collection_documents"},
        "app.models.document": {"documents"},
        "app.models.document_profile": {"document_profiles"},
        "app.models.document_progress": {"document_progress"},
        "app.models.friendship": {"friendships"},
        "app.models.job": {"jobs"},
        "app.models.playback_session": {"playback_sessions"},
        "app.models.section": {"sections"},
        "app.models.shared_item": {"shared_items"},
        "app.models.theme_profile": {"theme_profiles"},
        "app.models.text_chunk": {"text_chunks"},
        "app.models.user": {"users"},
        "app.models.user_invite": {"user_invites"},
        "app.models.user_setting": {"user_settings"},
        "app.models.voice_preset": {"voice_presets"},
    }

    for module_name, expected_tables in module_tables.items():
        module = import_module(module_name)
        if not expected_tables.issubset(Base.metadata.tables):
            reload(module)

    if "theme_profiles" not in Base.metadata.tables:
        reload(import_module("app.models.theme_profile"))

    Base.metadata.create_all(bind=engine)
    _ensure_runtime_columns()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_runtime_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    statements: list[str] = []

    if "playback_sessions" in table_names:
        playback_session_columns = {
            column["name"] for column in inspector.get_columns("playback_sessions")
        }

        if "user_id" not in playback_session_columns:
            statements.append("ALTER TABLE playback_sessions ADD COLUMN user_id INTEGER")
        if "voice_option_id" not in playback_session_columns:
            statements.append("ALTER TABLE playback_sessions ADD COLUMN voice_option_id VARCHAR(255)")
        if "playback_speed" not in playback_session_columns:
            statements.append(
                "ALTER TABLE playback_sessions ADD COLUMN playback_speed FLOAT NOT NULL DEFAULT 1.0"
            )

    if "jobs" in table_names:
        job_columns = {column["name"] for column in inspector.get_columns("jobs")}

        if "user_id" not in job_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN user_id INTEGER")
        if "clone_engine_id" not in job_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN clone_engine_id VARCHAR(255)")
        if "split_chapters" not in job_columns:
            statements.append(
                "ALTER TABLE jobs ADD COLUMN split_chapters BOOLEAN NOT NULL DEFAULT 0"
            )
        if "artifact_basename" not in job_columns:
            statements.append(
                "ALTER TABLE jobs ADD COLUMN artifact_basename VARCHAR(255) NOT NULL DEFAULT 'export'"
            )
        if "progress_percent" not in job_columns:
            statements.append(
                "ALTER TABLE jobs ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0"
            )
        if "status_detail" not in job_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN status_detail VARCHAR(255)")
        if "artifact_manifest" not in job_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN artifact_manifest TEXT")
        if "heartbeat_at" not in job_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN heartbeat_at DATETIME")

    if "documents" in table_names:
        document_columns = {column["name"] for column in inspector.get_columns("documents")}
        if "owner_user_id" not in document_columns:
            statements.append("ALTER TABLE documents ADD COLUMN owner_user_id INTEGER")
        if "origin_path" not in document_columns:
            statements.append("ALTER TABLE documents ADD COLUMN origin_path VARCHAR(1024)")

    if "document_progress" in table_names:
        progress_columns = {column["name"] for column in inspector.get_columns("document_progress")}
        if "bookmark_enabled" not in progress_columns:
            statements.append(
                "ALTER TABLE document_progress ADD COLUMN bookmark_enabled BOOLEAN NOT NULL DEFAULT 1"
            )
        if "has_bookmark" not in progress_columns:
            statements.append(
                "ALTER TABLE document_progress ADD COLUMN has_bookmark BOOLEAN NOT NULL DEFAULT 1"
            )
        if "is_finished" not in progress_columns:
            statements.append(
                "ALTER TABLE document_progress ADD COLUMN is_finished BOOLEAN NOT NULL DEFAULT 0"
            )
        if "finished_at" not in progress_columns:
            statements.append("ALTER TABLE document_progress ADD COLUMN finished_at DATETIME")

    if "document_profiles" in table_names:
        profile_columns = {column["name"] for column in inspector.get_columns("document_profiles")}
        if "metadata_source" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN metadata_source VARCHAR(64)")
        if "metadata_source_id" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN metadata_source_id VARCHAR(255)")
        if "source_provider" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN source_provider VARCHAR(64)")
        if "source_provider_id" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN source_provider_id VARCHAR(255)")
        if "source_provider_name" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN source_provider_name VARCHAR(255)")
        if "source_provider_url" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN source_provider_url VARCHAR(1024)")
        if "source_url" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN source_url VARCHAR(2048)")
        if "source_site_name" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN source_site_name VARCHAR(255)")
        if "import_mode" not in profile_columns:
            statements.append("ALTER TABLE document_profiles ADD COLUMN import_mode VARCHAR(64)")

    if "theme_profiles" in table_names:
        theme_columns = {column["name"] for column in inspector.get_columns("theme_profiles")}
        if "owner_user_id" not in theme_columns:
            statements.append("ALTER TABLE theme_profiles ADD COLUMN owner_user_id INTEGER")
        if "family" not in theme_columns:
            statements.append("ALTER TABLE theme_profiles ADD COLUMN family VARCHAR(64) NOT NULL DEFAULT 'house'")
        if "preview_variant" not in theme_columns:
            statements.append(
                "ALTER TABLE theme_profiles ADD COLUMN preview_variant VARCHAR(64) NOT NULL DEFAULT 'standard'"
            )
        if "background_asset_path" not in theme_columns:
            statements.append("ALTER TABLE theme_profiles ADD COLUMN background_asset_path VARCHAR(255)")
        if "background_overlay_path" not in theme_columns:
            statements.append("ALTER TABLE theme_profiles ADD COLUMN background_overlay_path VARCHAR(255)")
        if "shelf_asset_path" not in theme_columns:
            statements.append("ALTER TABLE theme_profiles ADD COLUMN shelf_asset_path VARCHAR(255)")
        if "surface_texture_asset_path" not in theme_columns:
            statements.append("ALTER TABLE theme_profiles ADD COLUMN surface_texture_asset_path VARCHAR(255)")
        if "supports_mix_and_match" not in theme_columns:
            statements.append(
                "ALTER TABLE theme_profiles ADD COLUMN supports_mix_and_match BOOLEAN NOT NULL DEFAULT 1"
            )

    if "voice_presets" in table_names:
        voice_preset_columns = {
            column["name"] for column in inspector.get_columns("voice_presets")
        }
        if "owner_user_id" not in voice_preset_columns:
            statements.append("ALTER TABLE voice_presets ADD COLUMN owner_user_id INTEGER")
        if "source_provider" not in voice_preset_columns:
            statements.append("ALTER TABLE voice_presets ADD COLUMN source_provider VARCHAR(100)")
        if "source_url" not in voice_preset_columns:
            statements.append("ALTER TABLE voice_presets ADD COLUMN source_url VARCHAR(2048)")
        if "transcript_source_url" not in voice_preset_columns:
            statements.append("ALTER TABLE voice_presets ADD COLUMN transcript_source_url VARCHAR(2048)")
        if "license_label" not in voice_preset_columns:
            statements.append("ALTER TABLE voice_presets ADD COLUMN license_label VARCHAR(255)")
        if "provenance_note" not in voice_preset_columns:
            statements.append("ALTER TABLE voice_presets ADD COLUMN provenance_note TEXT")

    if "collections" in table_names:
        collection_columns = {column["name"] for column in inspector.get_columns("collections")}
        if "owner_user_id" not in collection_columns:
            statements.append("ALTER TABLE collections ADD COLUMN owner_user_id INTEGER")

    if "user_settings" not in table_names:
        statements.append(
            "CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER NOT NULL, key VARCHAR(100) NOT NULL, value TEXT, PRIMARY KEY (user_id, key))"
        )

    if "friendships" not in table_names:
        statements.append(
            "CREATE TABLE IF NOT EXISTS friendships ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "requester_user_id INTEGER NOT NULL, "
            "addressee_user_id INTEGER NOT NULL, "
            "status VARCHAR(32) NOT NULL DEFAULT 'pending', "
            "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "responded_at DATETIME)"
        )

    if "shared_items" not in table_names:
        statements.append(
            "CREATE TABLE IF NOT EXISTS shared_items ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "sender_user_id INTEGER NOT NULL, "
            "recipient_user_id INTEGER NOT NULL, "
            "item_type VARCHAR(32) NOT NULL, "
            "source_item_id INTEGER NOT NULL, "
            "item_label VARCHAR(255) NOT NULL, "
            "message TEXT, "
            "status VARCHAR(32) NOT NULL DEFAULT 'pending', "
            "accepted_item_id INTEGER, "
            "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "responded_at DATETIME)"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
