from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.services.audio_cache import build_chunk_audio_cache_path
from app.tts.base import TTSEngine

SHORT_SAMPLE_TEXT = "First sentence. Second sentence."
LONG_SAMPLE_TEXT = " ".join(
    [
        "Alice reads a steady paragraph that keeps the passage coherent and easy to follow."
        for _ in range(28)
    ]
)


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.settings"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.playback"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.api.playback"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_create_playback_session_returns_first_audio_chunk(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_id"] == import_response.json()["id"]
    assert payload["current_chunk_index"] == 0
    assert payload["audio_url"].startswith("/api/playback/audio/")
    assert payload["playback_speed"] == 1.0
    assert payload["current_chunk_text"] == SHORT_SAMPLE_TEXT
    assert payload["section_chunks"][0] == {
        "chunk_index": 0,
        "text": SHORT_SAMPLE_TEXT,
        "is_current": True,
    }

    audio_response = client.get(payload["audio_url"])

    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"] == "audio/wav"
    assert audio_response.content.startswith(b"RIFF")


def test_live_narration_pace_scopes_chunk_audio_cache(client: TestClient) -> None:
    settings_response = client.get("/api/settings")
    assert settings_response.status_code == 200

    update_response = client.put(
        "/api/settings",
        json={**settings_response.json(), "live_narration_pace": 1.5},
    )
    assert update_response.status_code == 200
    assert update_response.json()["live_narration_pace"] == 1.5

    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert response.status_code == 201

    from app import db
    from app.models.playback_session import PlaybackSession

    with db.session_scope() as session:
        playback_session = session.get(PlaybackSession, response.json()["id"])
        assert playback_session is not None
        assert "pace-1-50" in playback_session.audio_path

    audio_response = client.get(response.json()["audio_url"])
    assert audio_response.status_code == 200


def test_playback_audio_serves_legacy_per_user_cache_paths(
    client: TestClient, tmp_path: Path
) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    from app import db
    from app.models.playback_session import PlaybackSession
    from app.services.user_storage import user_cache_root

    with db.session_scope() as session:
        playback_session = session.get(PlaybackSession, payload["id"])
        assert playback_session is not None
        assert playback_session.user_id is not None
        legacy_path = user_cache_root(playback_session.user_id) / "chunk-legacy.wav"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_bytes(Path(playback_session.audio_path).read_bytes())
        playback_session.audio_path = str(legacy_path)

    audio_response = client.get(payload["audio_url"])

    assert audio_response.status_code == 200
    assert audio_response.content.startswith(b"RIFF")


def test_playback_audio_rejects_paths_outside_the_audio_cache(
    client: TestClient, tmp_path: Path
) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    outside_path = tmp_path / "outside" / "not-cache-audio.wav"
    outside_path.parent.mkdir(parents=True, exist_ok=True)
    outside_path.write_bytes(b"RIFF-outside-the-cache")

    from app import db
    from app.models.playback_session import PlaybackSession

    with db.session_scope() as session:
        playback_session = session.get(PlaybackSession, payload["id"])
        assert playback_session is not None
        playback_session.audio_path = str(outside_path)

    audio_response = client.get(payload["audio_url"])

    assert audio_response.status_code == 404
    assert outside_path.exists()


def test_create_playback_session_accepts_explicit_speed_override(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"], "playback_speed": 1.4},
    )

    assert response.status_code == 201
    assert response.json()["playback_speed"] == 1.4


def test_create_playback_session_rejects_an_unavailable_voice_cleanly(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "tts_engine", "piper")

    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )

    assert response.status_code == 422
    assert "is unavailable" in response.json()["detail"]


def test_create_playback_session_does_not_run_per_request_table_ddl(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("per-request DDL should not run")

    playback_session_model = import_module("app.models.playback_session").PlaybackSession
    monkeypatch.setattr(playback_session_model.__table__, "create", fail_if_called)

    response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )

    assert response.status_code == 201


def test_update_playback_session_advances_backing_audio(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    create_response = client.post(
        "/api/playback/sessions",
        json={"document_id": document_id},
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]
    audio_url = create_response.json()["audio_url"]

    db_module = import_module("app.db")
    playback_session_model = import_module("app.models.playback_session").PlaybackSession
    section_model = import_module("app.models.section").Section
    text_chunk_model = import_module("app.models.text_chunk").TextChunk

    with db_module.session_scope() as session:
        ordered_chunks = list(
            session.scalars(
                select(text_chunk_model)
                .join(section_model, text_chunk_model.section_id == section_model.id)
                .where(section_model.document_id == document_id)
                .order_by(section_model.position, text_chunk_model.position)
            )
        )
        stored_session = session.get(playback_session_model, session_id)

        assert stored_session is not None
        assert len(ordered_chunks) >= 2
        first_chunk_id = ordered_chunks[0].id
        second_chunk_id = ordered_chunks[1].id
        first_audio_path = stored_session.audio_path
        assert stored_session.chunk_id == first_chunk_id

    first_audio_response = client.get(audio_url)
    assert first_audio_response.status_code == 200

    update_response = client.patch(
        f"/api/playback/sessions/{session_id}",
        json={"current_chunk_index": 1},
    )

    assert update_response.status_code == 200
    assert update_response.json()["current_chunk_index"] == 1

    with db_module.session_scope() as session:
        updated_session = session.get(playback_session_model, session_id)

        assert updated_session is not None
        assert updated_session.chunk_id == second_chunk_id
        assert updated_session.audio_path != first_audio_path

    second_audio_response = client.get(audio_url)
    assert second_audio_response.status_code == 200
    assert second_audio_response.headers["content-type"] == "audio/wav"
    assert second_audio_response.content.startswith(b"RIFF")


def test_prebuffer_playback_session_prepares_next_chunk(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert session_response.status_code == 201

    response = client.post(f"/api/playback/sessions/{session_response.json()['id']}/prebuffer")

    assert response.status_code == 200
    assert response.json()["session_id"] == session_response.json()["id"]
    assert response.json()["target_chunk_index"] == 1
    assert response.json()["status"] == "prepared"
    assert response.json()["audio_url"].startswith("/api/playback/audio/")


def test_create_playback_session_can_start_from_a_specific_section_and_voice(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={
            "file": (
                "book.md",
                b"# Chapter One\nFirst section opening.\n\n# Chapter Two\nSecond section opening.",
                "text/markdown",
            )
        },
    )
    assert import_response.status_code == 201

    detail_response = client.get(f"/api/documents/{import_response.json()['id']}")
    assert detail_response.status_code == 200
    second_section_id = detail_response.json()["sections"][1]["id"]
    voices_response = client.get("/api/voices/options")
    assert voices_response.status_code == 200
    live_voice_id = voices_response.json()[0]["id"]

    response = client.post(
        "/api/playback/sessions",
        json={
            "document_id": import_response.json()["id"],
            "start_section_id": second_section_id,
            "voice_option_id": live_voice_id,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_id"] == import_response.json()["id"]
    assert payload["current_chunk_index"] == 1
    assert payload["voice_option_id"] == live_voice_id
    assert payload["current_section_title"] == "Chapter Two"
    assert payload["current_chunk_text"] == "Second section opening."


def test_create_playback_session_uses_selected_kokoro_voice_family(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kokoro_binary = tmp_path / "bin" / "kokoro-onnx"
    kokoro_binary.parent.mkdir(parents=True, exist_ok=True)
    kokoro_binary.write_text("", encoding="utf-8")

    kokoro_model_path = tmp_path / "models" / "kokoro" / "kokoro-v1.0.onnx"
    kokoro_model_path.parent.mkdir(parents=True, exist_ok=True)
    kokoro_model_path.write_bytes(b"model")
    kokoro_voices_path = tmp_path / "models" / "kokoro" / "voices-v1.0.bin"
    kokoro_voices_path.write_bytes(b"voices")

    monkeypatch.setattr(settings, "tts_engine", "piper")
    monkeypatch.setattr(settings, "kokoro_binary", "kokoro-onnx")
    monkeypatch.setattr(settings, "kokoro_model_path", kokoro_model_path)
    monkeypatch.setattr(settings, "kokoro_voices_path", kokoro_voices_path)
    monkeypatch.setattr("app.tts.kokoro_engine.KokoroEngine._is_ready", lambda self: True)

    captured_engines: list[str] = []

    def fake_populate_cached_audio(*, engine: TTSEngine, text: str, output_path: Path) -> Path:
        captured_engines.append(engine.name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFFdemo")
        return output_path

    monkeypatch.setattr("app.services.playback.populate_cached_audio", fake_populate_cached_audio)

    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/playback/sessions",
        json={
            "document_id": import_response.json()["id"],
            "voice_option_id": "builtin:kokoro:af-sarah",
        },
    )

    assert response.status_code == 201
    assert response.json()["voice_option_id"] == "builtin:kokoro:af-sarah"
    assert captured_engines == ["kokoro"]

    db_module = import_module("app.db")
    playback_session_model = import_module("app.models.playback_session").PlaybackSession
    with db_module.session_scope() as session:
        playback_session = session.get(playback_session_model, response.json()["id"])
        assert playback_session is not None
        assert playback_session.engine_name == "kokoro"


def test_create_playback_session_reuses_existing_session_for_resume(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    first_response = client.post("/api/playback/sessions", json={"document_id": document_id})
    assert first_response.status_code == 201

    progress_response = client.patch(
        f"/api/playback/sessions/{first_response.json()['id']}",
        json={"current_chunk_index": 1},
    )
    assert progress_response.status_code == 200

    second_response = client.post("/api/playback/sessions", json={"document_id": document_id})

    assert second_response.status_code == 201
    assert second_response.json()["id"] == first_response.json()["id"]
    assert second_response.json()["current_chunk_index"] == 1


def test_patch_playback_session_updates_speed_and_voice(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.piper_model_path.parent.mkdir(parents=True, exist_ok=True)
    settings.piper_model_path.write_bytes(b"first-model")
    second_model_path = tmp_path / "data" / "models" / "piper" / "second-reader.onnx"
    second_model_path.parent.mkdir(parents=True, exist_ok=True)
    second_model_path.write_bytes(b"second-model")

    def fake_populate_cached_audio(*, engine: TTSEngine, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFFdemo")
        return output_path

    monkeypatch.setattr("app.services.playback.populate_cached_audio", fake_populate_cached_audio)

    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    create_response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert create_response.status_code == 201

    voices_response = client.get("/api/voices/options")
    assert voices_response.status_code == 200
    assert len(voices_response.json()) >= 2
    second_voice_id = voices_response.json()[1]["id"]

    response = client.patch(
        f"/api/playback/sessions/{create_response.json()['id']}",
        json={
            "playback_speed": 1.35,
            "voice_option_id": second_voice_id,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["playback_speed"] == 1.35
    assert payload["voice_option_id"] == second_voice_id


def test_create_playback_session_accepts_saved_cloned_voice_when_runtime_is_available(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.tts.qwen_clone_engine.import_module",
        lambda name: type(
            "FakeQwenModule",
            (),
            {"Qwen3TTSModel": type("FakeModel", (), {"from_pretrained": staticmethod(lambda *args, **kwargs: object())})},
        )(),
    )

    captured_engines: list[str] = []

    def fake_populate_cached_audio(*, engine: TTSEngine, text: str, output_path: Path) -> Path:
        captured_engines.append(engine.name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFFdemo")
        return output_path

    monkeypatch.setattr("app.services.playback.populate_cached_audio", fake_populate_cached_audio)

    create_preset_response = client.post(
        "/api/voices/presets",
        data={"name": "Warm Narrator", "transcript": "A warm sample transcript."},
        files={"reference_audio": ("warm.wav", b"RIFFdemo", "audio/wav")},
    )
    assert create_preset_response.status_code == 201
    preset_voice_id = f"preset:{create_preset_response.json()['id']}"

    settings_response = client.put(
        "/api/settings",
        json={
            "default_live_voice_id": "builtin:kokoro:af-heart",
            "default_export_voice_id": preset_voice_id,
            "fallback_voice_id": "builtin:kokoro:af-heart",
            "selected_clone_model_engine": "qwen3_clone_1_7b",
        },
    )
    assert settings_response.status_code == 200

    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/playback/sessions",
        json={
            "document_id": import_response.json()["id"],
            "voice_option_id": preset_voice_id,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["voice_option_id"] == preset_voice_id
    assert payload["engine_name"] == "qwen3_clone_1_7b"
    assert payload["voice_model_name"] == "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    assert captured_engines == ["qwen3_clone_1_7b"]


def test_failed_synthesis_does_not_leave_partial_cache_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    playback_module = import_module("app.services.playback")

    class FailingEngine(TTSEngine):
        name = "failing"

        def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"partial")
            raise RuntimeError("synthesis failed")

    monkeypatch.setattr(
        playback_module,
        "build_live_engine_for_voice_option",
        lambda voice_option_id, user_id=None, pace=1.0: FailingEngine(),
    )

    expected_cache_path = build_chunk_audio_cache_path(
        engine_name="failing",
        document_id=import_response.json()["id"],
        chunk_id=1,
        text=SHORT_SAMPLE_TEXT,
        voice_cache_key="builtin:piper:test",
    )
    expected_cache_path.unlink(missing_ok=True)

    response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The selected text-to-speech voice could not generate audio on this server."
    )

    assert not expected_cache_path.exists()
    assert list(expected_cache_path.parent.glob("*.tmp")) == []
