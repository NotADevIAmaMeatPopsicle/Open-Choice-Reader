import sqlite3
from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.auth_session"))
    reload(import_module("app.models.collection"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.theme_profile"))
    reload(import_module("app.models.user"))
    reload(import_module("app.models.user_invite"))
    reload(import_module("app.models.user_setting"))
    reload(import_module("app.models.voice_preset"))

    reload(import_module("app.services.auth"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.ownership_backfill"))
    reload(import_module("app.services.settings"))
    reload(import_module("app.services.themes"))
    reload(import_module("app.services.user_storage"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.api.auth"))
    reload(import_module("app.api.settings"))
    reload(import_module("app.api.themes"))

    db_module = import_module("app.db")
    reload(db_module)

    main_module = import_module("app.main")
    return reload(main_module).app, db_module


def _seed_legacy_single_user_database(
    database_path: Path,
    storage_root: Path,
    *,
    use_relative_paths: bool = False,
) -> None:
    storage_root.mkdir(parents=True, exist_ok=True)
    (storage_root / "source").mkdir(parents=True, exist_ok=True)
    (storage_root / "cache").mkdir(parents=True, exist_ok=True)
    (storage_root / "exports").mkdir(parents=True, exist_ok=True)
    (storage_root / "voices").mkdir(parents=True, exist_ok=True)
    (storage_root / "covers").mkdir(parents=True, exist_ok=True)

    legacy_source = storage_root / "source" / "legacy-book.txt"
    legacy_cache = storage_root / "cache" / "legacy-session.wav"
    legacy_export = storage_root / "exports" / "legacy-export.wav"
    legacy_voice = storage_root / "voices" / "legacy-narrator.wav"
    legacy_cover = storage_root / "covers" / "legacy-cover.jpg"

    legacy_source.write_text("legacy source", encoding="utf-8")
    legacy_cache.write_bytes(b"RIFFlegacycache")
    legacy_export.write_bytes(b"RIFFlegacyexport")
    legacy_voice.write_bytes(b"RIFFlegacyvoice")
    legacy_cover.write_bytes(b"\xff\xd8\xff\xe0")

    def stored_path(path: Path) -> str:
        if not use_relative_paths:
            return str(path)
        return str(path.relative_to(storage_root.parent))

    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE documents (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title VARCHAR(255) NOT NULL,
              format VARCHAR(50) NOT NULL,
              status VARCHAR(50) NOT NULL,
              source_path VARCHAR(1024) NOT NULL,
              origin_path VARCHAR(1024)
            );

            CREATE TABLE document_profiles (
              document_id INTEGER PRIMARY KEY,
              author VARCHAR(255),
              summary TEXT,
              cover_path VARCHAR(1024),
              metadata_source VARCHAR(64),
              metadata_source_id VARCHAR(255),
              source_provider VARCHAR(64),
              source_provider_id VARCHAR(255),
              source_provider_name VARCHAR(255),
              source_provider_url VARCHAR(1024),
              source_url VARCHAR(2048),
              source_site_name VARCHAR(255),
              import_mode VARCHAR(64),
              total_sections INTEGER NOT NULL DEFAULT 0,
              total_chunks INTEGER NOT NULL DEFAULT 0,
              estimated_duration_seconds INTEGER NOT NULL DEFAULT 0,
              imported_at DATETIME NOT NULL,
              updated_at DATETIME NOT NULL
            );

            CREATE TABLE sections (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_id INTEGER NOT NULL,
              position INTEGER NOT NULL,
              title VARCHAR(255),
              text TEXT NOT NULL
            );

            CREATE TABLE text_chunks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              position INTEGER NOT NULL,
              text TEXT NOT NULL
            );

            CREATE TABLE document_progress (
              document_id INTEGER PRIMARY KEY,
              current_chunk_index INTEGER NOT NULL DEFAULT 0,
              bookmark_enabled BOOLEAN NOT NULL DEFAULT 1,
              has_bookmark BOOLEAN NOT NULL DEFAULT 1,
              is_finished BOOLEAN NOT NULL DEFAULT 0,
              finished_at DATETIME,
              last_opened_at DATETIME NOT NULL
            );

            CREATE TABLE playback_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_id INTEGER NOT NULL,
              chunk_id INTEGER NOT NULL,
              current_chunk_index INTEGER NOT NULL DEFAULT 0,
              engine_name VARCHAR(50) NOT NULL,
              voice_option_id VARCHAR(255),
              playback_speed FLOAT NOT NULL DEFAULT 1.0,
              audio_path VARCHAR(1024) NOT NULL
            );

            CREATE TABLE collections (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name VARCHAR(255) NOT NULL,
              description TEXT
            );

            CREATE TABLE collection_documents (
              collection_id INTEGER NOT NULL,
              document_id INTEGER NOT NULL,
              PRIMARY KEY (collection_id, document_id)
            );

            CREATE TABLE jobs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_id INTEGER NOT NULL,
              voice_preset_id VARCHAR(255) NOT NULL,
              clone_engine_id VARCHAR(255),
              format VARCHAR(50) NOT NULL,
              status VARCHAR(50) NOT NULL,
              split_chapters BOOLEAN NOT NULL DEFAULT 0,
              artifact_basename VARCHAR(255) NOT NULL DEFAULT 'export',
              progress_percent INTEGER NOT NULL DEFAULT 0,
              status_detail VARCHAR(255),
              artifact_path VARCHAR(1024),
              artifact_manifest TEXT,
              failure_detail VARCHAR(1024)
            );

            CREATE TABLE voice_presets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name VARCHAR(255) NOT NULL,
              engine VARCHAR(50) NOT NULL,
              reference_path VARCHAR(1024) NOT NULL,
              transcript TEXT NOT NULL
            );

            CREATE TABLE theme_profiles (
              id VARCHAR(100) PRIMARY KEY,
              name VARCHAR(255) NOT NULL,
              description TEXT,
              source_kind VARCHAR(32) NOT NULL,
              source_label VARCHAR(255) NOT NULL,
              source_reference VARCHAR(255),
              is_builtin BOOLEAN NOT NULL DEFAULT 0,
              sort_order INTEGER NOT NULL DEFAULT 100,
              family VARCHAR(64) NOT NULL DEFAULT 'house',
              preview_variant VARCHAR(64) NOT NULL DEFAULT 'standard',
              background_asset_path VARCHAR(255),
              background_overlay_path VARCHAR(255),
              shelf_asset_path VARCHAR(255),
              surface_texture_asset_path VARCHAR(255),
              supports_mix_and_match BOOLEAN NOT NULL DEFAULT 1,
              tokens_json TEXT NOT NULL
            );

            CREATE TABLE app_settings (
              key VARCHAR(100) PRIMARY KEY,
              value TEXT
            );
            """
        )

        cursor.execute(
            """
            INSERT INTO documents (id, title, format, status, source_path, origin_path)
            VALUES (1, 'Legacy Book', 'txt', 'ready', ?, ?)
            """,
            (stored_path(legacy_source), str(Path("C:/legacy/original.txt"))),
        )
        cursor.execute(
            """
            INSERT INTO document_profiles (
              document_id, author, summary, cover_path, total_sections, total_chunks,
              estimated_duration_seconds, imported_at, updated_at
            )
            VALUES (1, 'Legacy Author', 'Legacy summary', ?, 1, 1, 120, '2026-05-12T00:00:00', '2026-05-12T00:00:00')
            """,
            (stored_path(legacy_cover),),
        )
        cursor.execute(
            "INSERT INTO sections (id, document_id, position, title, text) VALUES (1, 1, 0, 'Legacy Chapter', 'Legacy text')"
        )
        cursor.execute(
            "INSERT INTO text_chunks (id, section_id, position, text) VALUES (1, 1, 0, 'Legacy chunk')"
        )
        cursor.execute(
            """
            INSERT INTO document_progress (
              document_id, current_chunk_index, bookmark_enabled, has_bookmark, is_finished, finished_at, last_opened_at
            )
            VALUES (1, 0, 1, 1, 0, NULL, '2026-05-12T00:00:00')
            """
        )
        cursor.execute(
            """
            INSERT INTO playback_sessions (
              id, document_id, chunk_id, current_chunk_index, engine_name, voice_option_id, playback_speed, audio_path
            )
            VALUES (1, 1, 1, 0, 'kokoro', 'builtin:kokoro:heart', 1.0, ?)
            """,
            (stored_path(legacy_cache),),
        )
        cursor.execute(
            "INSERT INTO collections (id, name, description) VALUES (1, 'Legacy Collection', 'Legacy description')"
        )
        cursor.execute(
            "INSERT INTO collection_documents (collection_id, document_id) VALUES (1, 1)"
        )
        cursor.execute(
            """
            INSERT INTO jobs (
              id, document_id, voice_preset_id, clone_engine_id, format, status, split_chapters,
              artifact_basename, progress_percent, status_detail, artifact_path, artifact_manifest, failure_detail
            )
            VALUES (1, 1, 'legacy', 'qwen3_clone_0_6b', 'wav', 'completed', 0, 'legacy-export', 100, NULL, ?, NULL, NULL)
            """,
            (stored_path(legacy_export),),
        )
        cursor.execute(
            """
            INSERT INTO voice_presets (id, name, engine, reference_path, transcript)
            VALUES (1, 'Legacy Voice', 'qwen3_clone', ?, 'Legacy transcript')
            """,
            (stored_path(legacy_voice),),
        )
        cursor.execute(
            """
            INSERT INTO theme_profiles (
              id, name, description, source_kind, source_label, source_reference, is_builtin,
              sort_order, family, preview_variant, background_asset_path, background_overlay_path,
              shelf_asset_path, surface_texture_asset_path, supports_mix_and_match, tokens_json
            )
            VALUES (
              'legacy-custom', 'Legacy Custom', 'Imported custom theme', 'imported', 'Legacy import',
              'legacy.css', 0, 900, 'house', 'standard', NULL, NULL, NULL, NULL, 1, '{"--color-bg":"#111111"}'
            )
            """
        )
        cursor.execute(
            "INSERT INTO app_settings (key, value) VALUES ('default_live_voice_id', 'builtin:kokoro:heart')"
        )
        cursor.execute(
            "INSERT INTO app_settings (key, value) VALUES ('active_theme_id', 'forest')"
        )
        connection.commit()
    finally:
        connection.close()


def test_bootstrap_admin_backfills_legacy_single_user_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "data"
    database_path = tmp_path / "legacy.db"

    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    monkeypatch.setattr(settings, "storage_root", storage_root)
    monkeypatch.setattr(settings, "source_root", storage_root / "source")
    monkeypatch.setattr(settings, "cache_root", storage_root / "cache")
    monkeypatch.setattr(settings, "export_root", storage_root / "exports")
    monkeypatch.setattr(settings, "inbox_root", storage_root / "inbox")
    monkeypatch.setattr(settings, "seed_download_root", storage_root / "seed-downloads")

    _seed_legacy_single_user_database(database_path, storage_root)

    app, db_module = _load_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/bootstrap-admin",
            json={
                "username": "Admin",
                "display_name": "Admin User",
                "password": "correct horse battery staple",
            },
        )

        assert response.status_code == 201

    models = import_module("app.models")
    UserSetting = import_module("app.models.user_setting").UserSetting

    with db_module.session_scope() as session:
        document = session.get(models.Document, 1)
        assert document is not None
        assert document.owner_user_id == 1
        assert Path(document.source_path) == storage_root / "users" / "1" / "source" / "legacy-book.txt"
        assert Path(document.source_path).is_file()
        assert not (storage_root / "source" / "legacy-book.txt").exists()

        profile = session.get(models.DocumentProfile, 1)
        assert profile is not None
        assert Path(profile.cover_path) == storage_root / "users" / "1" / "covers" / "legacy-cover.jpg"
        assert Path(profile.cover_path).is_file()

        playback_session = session.get(models.PlaybackSession, 1)
        assert playback_session is not None
        assert playback_session.user_id == 1
        assert Path(playback_session.audio_path) == storage_root / "users" / "1" / "cache" / "legacy-session.wav"
        assert Path(playback_session.audio_path).is_file()

        collection = session.get(models.Collection, 1)
        assert collection is not None
        assert collection.owner_user_id == 1

        job = session.get(models.Job, 1)
        assert job is not None
        assert job.user_id == 1
        assert Path(job.artifact_path) == storage_root / "users" / "1" / "exports" / "legacy-export.wav"
        assert Path(job.artifact_path).is_file()

        voice_preset = session.get(models.VoicePreset, 1)
        assert voice_preset is not None
        assert voice_preset.owner_user_id == 1
        assert Path(voice_preset.reference_path) == storage_root / "users" / "1" / "voices" / "legacy-narrator.wav"
        assert Path(voice_preset.reference_path).is_file()

        theme = session.get(models.ThemeProfile, "legacy-custom")
        assert theme is not None
        assert theme.owner_user_id == 1

        user_setting = session.get(UserSetting, {"user_id": 1, "key": "default_live_voice_id"})
        assert user_setting is not None
        active_theme_setting = session.get(UserSetting, {"user_id": 1, "key": "active_theme_id"})
        assert active_theme_setting is not None


def test_bootstrap_admin_backfills_relative_legacy_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "data"
    database_path = tmp_path / "legacy-relative.db"

    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    monkeypatch.setattr(settings, "storage_root", storage_root)
    monkeypatch.setattr(settings, "source_root", storage_root / "source")
    monkeypatch.setattr(settings, "cache_root", storage_root / "cache")
    monkeypatch.setattr(settings, "export_root", storage_root / "exports")
    monkeypatch.setattr(settings, "inbox_root", storage_root / "inbox")
    monkeypatch.setattr(settings, "seed_download_root", storage_root / "seed-downloads")

    _seed_legacy_single_user_database(
        database_path,
        storage_root,
        use_relative_paths=True,
    )

    app, db_module = _load_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/bootstrap-admin",
            json={
                "username": "Alice",
                "display_name": "Alice",
                "password": "correct horse battery staple",
            },
        )

        assert response.status_code == 201

    models = import_module("app.models")

    with db_module.session_scope() as session:
        document = session.get(models.Document, 1)
        assert document is not None
        assert Path(document.source_path) == storage_root / "users" / "1" / "source" / "legacy-book.txt"
        assert Path(document.source_path).is_file()

        profile = session.get(models.DocumentProfile, 1)
        assert profile is not None
        assert Path(profile.cover_path) == storage_root / "users" / "1" / "covers" / "legacy-cover.jpg"
        assert Path(profile.cover_path).is_file()

        playback_session = session.get(models.PlaybackSession, 1)
        assert playback_session is not None
        assert Path(playback_session.audio_path) == storage_root / "users" / "1" / "cache" / "legacy-session.wav"
        assert Path(playback_session.audio_path).is_file()

        job = session.get(models.Job, 1)
        assert job is not None
        assert Path(job.artifact_path) == storage_root / "users" / "1" / "exports" / "legacy-export.wav"
        assert Path(job.artifact_path).is_file()

        voice_preset = session.get(models.VoicePreset, 1)
        assert voice_preset is not None
        assert Path(voice_preset.reference_path) == storage_root / "users" / "1" / "voices" / "legacy-narrator.wav"
        assert Path(voice_preset.reference_path).is_file()
