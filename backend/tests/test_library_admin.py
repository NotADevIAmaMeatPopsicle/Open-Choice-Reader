from importlib import import_module, reload
from pathlib import Path

from sqlalchemy import func, select
from starlette.datastructures import Headers, UploadFile

from app.config import settings


def _load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    reload(import_module("app.models"))
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.collection"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.voice_preset"))

    db_module = reload(import_module("app.db"))
    documents_module = reload(import_module("app.services.documents"))
    admin_module = reload(import_module("app.services.library_admin"))
    settings_module = import_module("app.models.app_setting")
    voices_module = import_module("app.models.voice_preset")
    documents_module.init_database()

    return db_module, documents_module, admin_module, settings_module, voices_module


def test_reset_library_clears_documents_and_artifacts_but_preserves_settings_and_voice_presets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_module, documents_module, admin_module, settings_model, voices_model = _load_modules(tmp_path, monkeypatch)

    upload = UploadFile(
        file=(tmp_path / "sample.txt").open("w+b"),
        filename="sample.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    upload.file.write(b"hello world")
    upload.file.seek(0)
    documents_module.import_document(upload)

    (settings.storage_root / "covers").mkdir(parents=True, exist_ok=True)
    (settings.export_root).mkdir(parents=True, exist_ok=True)
    (settings.seed_download_root).mkdir(parents=True, exist_ok=True)
    (settings.cache_root / "audio").mkdir(parents=True, exist_ok=True)
    (settings.storage_root / "covers" / "cover.jpg").write_bytes(b"cover")
    (settings.export_root / "artifact.wav").write_bytes(b"artifact")
    (settings.seed_download_root / "book.epub").write_bytes(b"seed")
    (settings.cache_root / "audio" / "cached.wav").write_bytes(b"cache")

    with db_module.session_scope() as session:
        session.add(settings_model.AppSetting(key="default_live_voice_id", value="builtin:piper:default"))
        session.add(
            voices_model.VoicePreset(
                name="Warm Narrator",
                engine="qwen3_clone",
                reference_path=str(settings.storage_root / "voices" / "alice.wav"),
                transcript="hello there",
            )
        )

    admin_module.reset_library()

    with db_module.session_scope() as session:
        document_model = import_module("app.models.document").Document
        assert session.scalar(select(func.count()).select_from(document_model)) == 0
        assert (
            session.scalar(
                select(settings_model.AppSetting.key).where(
                    settings_model.AppSetting.key == "default_live_voice_id"
                )
            )
            == "default_live_voice_id"
        )
        assert session.scalar(select(voices_model.VoicePreset.name)) == "Warm Narrator"

    assert list(settings.source_root.glob("*")) == []
    assert list((settings.storage_root / "covers").glob("*")) == []
    assert list(settings.export_root.glob("*")) == []
    assert list(settings.seed_download_root.glob("*")) == []
    assert list((settings.cache_root / "audio").glob("*")) == []
