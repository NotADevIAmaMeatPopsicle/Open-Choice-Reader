from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def _long_passage_text() -> bytes:
    sentence = "Alice studies the shoreline and notes each glimmering detail carefully."
    return " ".join(sentence for _ in range(36)).encode("utf-8")


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


def test_populate_cached_clone_audio_uses_clone_engine_contract(tmp_path: Path) -> None:
    from app.services.audio_cache import populate_cached_clone_audio

    calls: list[dict[str, object]] = []

    class FakeCloneEngine:
        def clone_to_file(
            self,
            *,
            text: str,
            output_path: Path,
            reference_audio_path: Path,
            transcript: str,
        ) -> Path:
            calls.append(
                {
                    "text": text,
                    "reference_audio_path": reference_audio_path,
                    "transcript": transcript,
                    "suffix": output_path.suffix,
                }
            )
            output_path.write_bytes(b"RIFFclone")
            return output_path

    output_path = tmp_path / "chunk.wav"
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"RIFFref")

    result = populate_cached_clone_audio(
        engine=FakeCloneEngine(),
        text="Hello cloned reader.",
        output_path=output_path,
        reference_audio_path=reference_path,
        transcript="Reference transcript.",
    )

    assert result == output_path
    assert output_path.read_bytes() == b"RIFFclone"
    assert calls == [
        {
            "text": "Hello cloned reader.",
            "reference_audio_path": reference_path,
            "transcript": "Reference transcript.",
            "suffix": ".tmp",
        }
    ]


def test_populate_cached_clone_audio_reuses_existing_file(tmp_path: Path) -> None:
    from app.services.audio_cache import populate_cached_clone_audio

    class FailingCloneEngine:
        def clone_to_file(self, **kwargs):
            raise AssertionError("cached file should be reused")

    output_path = tmp_path / "chunk.wav"
    output_path.write_bytes(b"RIFFcached")
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"RIFFref")

    result = populate_cached_clone_audio(
        engine=FailingCloneEngine(),
        text="Hello cloned reader.",
        output_path=output_path,
        reference_audio_path=reference_path,
        transcript="Reference transcript.",
    )

    assert result == output_path
    assert output_path.read_bytes() == b"RIFFcached"


def test_create_playback_session_can_render_cloned_voice(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"First sentence. Second sentence.", "text/plain")},
    )
    assert import_response.status_code == 201

    preset_response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )
    assert preset_response.status_code == 201

    class FakeQwenModule:
        class Qwen3TTSModel:
            pass

    monkeypatch.setattr("app.tts.qwen_clone_engine.import_module", lambda name: FakeQwenModule)

    clone_calls: list[dict[str, object]] = []

    playback_module = import_module("app.services.playback")

    def fake_populate_cached_audio(*, engine, text: str, output_path: Path) -> Path:
        clone_calls.append(
            {
                "text": text,
                "engine_name": engine.name,
                "reference_audio_path": getattr(engine, "_reference_audio_path", None),
                "transcript": getattr(engine, "_transcript", None),
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFFclone")
        return output_path

    monkeypatch.setattr(playback_module, "populate_cached_audio", fake_populate_cached_audio)

    response = client.post(
        "/api/playback/sessions",
        json={
            "document_id": import_response.json()["id"],
            "voice_option_id": f"preset:{preset_response.json()['id']}",
        },
    )

    assert response.status_code == 201
    assert response.json()["voice_option_id"] == f"preset:{preset_response.json()['id']}"
    assert response.json()["audio_url"].startswith("/api/playback/audio/")
    assert clone_calls[0]["text"] == response.json()["current_chunk_text"]
    assert clone_calls[0]["engine_name"] == "qwen3_clone_0_6b"
    assert clone_calls[0]["transcript"] == "Alice reads sample text."


def test_prebuffer_playback_session_prepares_next_chunk(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", _long_passage_text(), "text/plain")},
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
    assert response.json()["status"] in {"cached", "prepared"}
    assert response.json()["audio_url"].startswith("/api/playback/audio/")
