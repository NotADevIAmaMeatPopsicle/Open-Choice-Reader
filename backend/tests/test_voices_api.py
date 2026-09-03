from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.settings"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.api.documents"))
    reload(import_module("app.api.settings"))
    reload(import_module("app.api.voices"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_create_voice_preset_returns_created_qwen_clone_record(client: TestClient) -> None:
    response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Narrator"
    assert response.json()["engine"] == "qwen3_clone"
    assert "reference_path" not in response.json()


def test_create_voice_preset_requires_transcript(client: TestClient) -> None:
    response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator"},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )

    assert response.status_code == 422


def test_list_voice_presets_returns_saved_presets(client: TestClient) -> None:
    create_response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )
    assert create_response.status_code == 201

    response = client.get("/api/voices/presets")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": create_response.json()["id"],
            "name": "Narrator",
            "engine": "qwen3_clone",
            "transcript": "Alice reads sample text.",
        }
    ]


def test_voice_preview_returns_audio_for_selected_voice(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview_path = tmp_path / "preview.wav"
    preview_path.write_bytes(b"RIFFpreview")

    monkeypatch.setattr(
        "app.api.voices.get_voice_preview_audio_path",
        lambda voice_option_id, user_id=None: preview_path,
    )

    response = client.get("/api/voices/preview", params={"voice_option_id": "builtin:kokoro:af-sarah"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"RIFFpreview"


def test_voice_preview_returns_validation_error_for_unpreviewable_voice(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.voices.get_voice_preview_audio_path",
        lambda voice_option_id, user_id=None: (_ for _ in ()).throw(
            ValueError("Voice 'preset:11' does not support preview")
        ),
    )

    response = client.get("/api/voices/preview", params={"voice_option_id": "preset:11"})

    assert response.status_code == 422
    assert response.json() == {"detail": "Voice 'preset:11' does not support preview"}


def test_transcribe_reference_audio_route_returns_reviewable_transcript(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    voice_schema = import_module("app.schemas.voice")

    monkeypatch.setattr(
        "app.api.voices.transcribe_reference_audio",
        lambda reference_audio: voice_schema.VoiceTranscriptionRead(
            transcript="Alice reads into his own microphone.",
            language="en",
            engine="faster-whisper:base",
            segments=[
                voice_schema.VoiceTranscriptionSegmentRead(
                    start=0.0,
                    end=1.25,
                    text="Alice reads into his own microphone.",
                )
            ],
        ),
    )

    response = client.post(
        "/api/voices/transcribe-reference",
        files={"reference_audio": ("voice.wav", b"RIFFvoice", "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "transcript": "Alice reads into his own microphone.",
        "language": "en",
        "engine": "faster-whisper:base",
        "segments": [
            {
                "start": 0.0,
                "end": 1.25,
                "text": "Alice reads into his own microphone.",
            }
        ],
    }


def test_list_voice_options_includes_builtin_reader_and_saved_clone(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    piper_binary = tmp_path / "bin" / "piper"
    piper_binary.parent.mkdir(parents=True, exist_ok=True)
    piper_binary.write_text("", encoding="utf-8")

    model_path = tmp_path / "models" / "piper" / "fast-reader.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")

    monkeypatch.setattr(settings, "piper_model_path", model_path)
    monkeypatch.setattr(settings, "qwen_clone_model_name", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: str(piper_binary))
    monkeypatch.setattr("app.tts.qwen_clone_engine.import_module", lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)))
    monkeypatch.setattr("app.services.settings.platform.node", lambda: "reader-host")
    monkeypatch.setattr("app.services.settings._detect_gpu_name", lambda: "NVIDIA GeForce RTX 3080")

    create_response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )
    assert create_response.status_code == 201

    response = client.get("/api/voices/options")

    assert response.status_code == 200
    payload = response.json()

    assert payload[0] == {
        "id": "builtin:piper:fast-reader",
        "name": "Fast Reader",
        "voice_type": "built_in",
        "engine": "piper",
        "mode_label": "Fast reader",
        "description": "Local Piper voice for quick read-aloud and fallback export.",
        "availability": "available",
        "availability_detail": "Piper is ready with 1 local voice.",
        "supports_live_reading": True,
        "supports_export": True,
        "transcript_preview": None,
        "engine_family": "piper",
        "model_name": None,
    }
    assert [voice_option["id"] for voice_option in payload if voice_option["voice_type"] == "built_in"] == [
        "builtin:piper:fast-reader",
        "builtin:kokoro:af-heart",
        "builtin:kokoro:af-bella",
        "builtin:kokoro:af-nicole",
        "builtin:kokoro:af-sarah",
        "builtin:kokoro:af-sky",
        "builtin:kokoro:am-michael",
    ]
    assert payload[-1] == {
        "id": f"preset:{create_response.json()['id']}",
        "name": "Narrator",
        "voice_type": "cloned",
        "engine": "qwen3_clone",
        "mode_label": "Cloned voice",
        "description": "Saved reference voice preset for premium live reading and audiobook export.",
        "availability": "unavailable",
        "availability_detail": "Qwen3 clone runtime is not installed on this host.",
        "supports_live_reading": True,
        "supports_export": True,
        "transcript_preview": "Alice reads sample text.",
        "engine_family": "qwen3_clone",
        "model_name": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    }


def test_settings_api_persists_default_voice_choices_and_engine_health(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    piper_binary = tmp_path / "bin" / "piper"
    piper_binary.parent.mkdir(parents=True, exist_ok=True)
    piper_binary.write_text("", encoding="utf-8")

    model_path = tmp_path / "models" / "piper" / "fast-reader.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")

    monkeypatch.setattr(settings, "piper_model_path", model_path)
    monkeypatch.setattr(settings, "qwen_clone_model_name", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: str(piper_binary))
    monkeypatch.setattr("app.tts.qwen_clone_engine.import_module", lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)))
    monkeypatch.setattr("app.services.settings.platform.node", lambda: "reader-host")
    monkeypatch.setattr("app.services.settings._detect_gpu_name", lambda: "NVIDIA GeForce RTX 3080")

    create_response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )
    assert create_response.status_code == 201

    initial_response = client.get("/api/settings")

    assert initial_response.status_code == 200
    payload = initial_response.json()
    assert payload["default_live_voice_id"] == "builtin:piper:fast-reader"
    assert payload["default_export_voice_id"] == "builtin:piper:fast-reader"
    assert payload["fallback_voice_id"] == "builtin:piper:fast-reader"
    assert payload["selected_clone_model_engine"] == "qwen3_clone_0_6b"
    assert payload["engine_statuses"] == [
        {
            "engine": "kokoro",
            "display_name": "Natural reader",
            "availability": "unavailable",
            "availability_detail": "Kokoro needs its runtime, model, and voice bundle before live reading can start.",
            "supports_live_reading": True,
            "supports_export": True,
            "engine_family": "kokoro",
            "model_name": "Kokoro-82M ONNX",
            "voice_count": 6,
        },
        {
            "engine": "piper",
            "display_name": "Fast reader",
            "availability": "available",
            "availability_detail": "Piper is ready with 1 local voice.",
            "supports_live_reading": True,
            "supports_export": True,
            "engine_family": "piper",
            "model_name": None,
            "voice_count": 1,
        },
        {
            "engine": "qwen3_clone_0_6b",
            "display_name": "Premium clone 0.6B",
            "availability": "unavailable",
            "availability_detail": "Qwen3 clone runtime is not installed on this host.",
            "supports_live_reading": True,
            "supports_export": True,
            "engine_family": "qwen3_clone",
            "model_name": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "voice_count": 0,
        },
        {
            "engine": "qwen3_clone_1_7b",
            "display_name": "Premium clone 1.7B",
            "availability": "unavailable",
            "availability_detail": "Qwen3 clone runtime is not installed on this host.",
            "supports_live_reading": True,
            "supports_export": True,
            "engine_family": "qwen3_clone",
            "model_name": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "voice_count": 0,
        },
    ]
    assert payload["host_runtime"] == {
        "host_name": "reader-host",
        "runtime_label": "GPU-capable host",
        "gpu_name": "NVIDIA GeForce RTX 3080",
        "execution_summary": "This host is serving Open Choice Reader and performing audio generation here.",
    }
    assert payload["clone_runtime"] == {
        "engine": "qwen3_clone",
        "model_name": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "preset_count": 1,
        "availability": "unavailable",
        "availability_detail": "Qwen3 clone runtime is not installed on this host.",
        "usage_summary": "Saved cloned presets can be used for live reading and audiobook export when the clone runtime is available.",
        "execution_summary": "Live cloned reading and audiobook exports run on reader-host when the clone runtime is available.",
        "available_models": [
            {
                "engine": "qwen3_clone_0_6b",
                "display_name": "Premium clone 0.6B",
                "model_name": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                "availability": "unavailable",
                "availability_detail": "Qwen3 clone runtime is not installed on this host.",
            },
            {
                "engine": "qwen3_clone_1_7b",
                "display_name": "Premium clone 1.7B",
                "model_name": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                "availability": "unavailable",
                "availability_detail": "Qwen3 clone runtime is not installed on this host.",
            },
        ],
    }

    update_response = client.put(
        "/api/settings",
        json={
            "default_live_voice_id": "builtin:piper:fast-reader",
            "default_export_voice_id": f"preset:{create_response.json()['id']}",
            "fallback_voice_id": None,
            "selected_clone_model_engine": "qwen3_clone_1_7b",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["default_export_voice_id"] == f"preset:{create_response.json()['id']}"
    assert update_response.json()["fallback_voice_id"] is None
    assert update_response.json()["selected_clone_model_engine"] == "qwen3_clone_1_7b"

    persisted_response = client.get("/api/settings")

    assert persisted_response.status_code == 200
    assert persisted_response.json()["default_live_voice_id"] == "builtin:piper:fast-reader"
    assert persisted_response.json()["default_export_voice_id"] == f"preset:{create_response.json()['id']}"
    assert persisted_response.json()["fallback_voice_id"] is None
    assert persisted_response.json()["selected_clone_model_engine"] == "qwen3_clone_1_7b"
    assert persisted_response.json()["host_runtime"]["host_name"] == "reader-host"
    assert persisted_response.json()["clone_runtime"]["preset_count"] == 1
