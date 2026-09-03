from importlib import import_module, reload
from pathlib import Path
import wave

import pytest
from starlette.datastructures import Headers, UploadFile

from app import db
from app.config import settings
from app.tts.base import TTSEngine

SHORT_SAMPLE_TEXT = "First sentence. Second sentence."
LONG_SAMPLE_TEXT = " ".join(
    [
        "Alice reads a steady paragraph that keeps the passage coherent and easy to follow."
        for _ in range(28)
    ]
)


def _load_modules():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    documents_module = reload(import_module("app.services.documents"))
    jobs_module = reload(import_module("app.services.jobs"))
    voice_presets_module = reload(import_module("app.services.voice_presets"))
    reload(import_module("app.services.audio_cache"))
    reload(import_module("app.tts.mock_engine"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.tts.qwen_clone_engine"))
    worker_jobs_module = reload(import_module("app.worker.jobs"))
    worker_runner_module = reload(import_module("app.worker.runner"))

    return {
        "documents": documents_module,
        "jobs": jobs_module,
        "voice_presets": voice_presets_module,
        "worker_jobs": worker_jobs_module,
        "worker_runner": worker_runner_module,
    }


def _upload_file(tmp_path: Path, *, filename: str, content: bytes) -> UploadFile:
    upload = UploadFile(
        file=(tmp_path / filename).open("w+b"),
        filename=filename,
        headers=Headers({"content-type": "text/plain"}),
    )
    upload.file.write(content)
    upload.file.seek(0)
    return upload


def test_run_once_processes_queued_wav_export_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    upload = _upload_file(
        tmp_path,
        filename="sample.txt",
        content=SHORT_SAMPLE_TEXT.encode("utf-8"),
    )
    try:
        document = modules["documents"].import_document(upload)
    finally:
        upload.file.close()

    job = modules["jobs"].enqueue_export_job(
        document_id=document.id,
        voice_preset_id="default",
        format="wav",
    )

    assert modules["worker_runner"].run_once() == 1

    refreshed_job = modules["jobs"].list_jobs()[0]
    export_path = Path(settings.export_root) / f"job-{job.id}.wav"

    assert refreshed_job.status == "completed"
    assert refreshed_job.artifact_path == str(export_path)
    assert refreshed_job.failure_detail is None
    assert export_path.exists()
    assert export_path.read_bytes().startswith(b"RIFF")
    assert refreshed_job.progress_percent == 100


def test_run_once_marks_failed_jobs_with_failure_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    upload = _upload_file(
        tmp_path,
        filename="sample.txt",
        content=b"Only sentence.",
    )
    try:
        document = modules["documents"].import_document(upload)
    finally:
        upload.file.close()

    job = modules["jobs"].enqueue_export_job(
        document_id=document.id,
        voice_preset_id="default",
        format="wav",
    )

    class FailingEngine(TTSEngine):
        name = "failing"

        def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
            raise RuntimeError(f"cannot synthesize '{text}'")

    monkeypatch.setattr(modules["worker_jobs"], "get_tts_engine", lambda name=None: FailingEngine())

    assert modules["worker_runner"].run_once() == 1

    refreshed_job = modules["jobs"].list_jobs()[0]

    assert refreshed_job.status == "failed"
    assert refreshed_job.id == job.id
    assert refreshed_job.artifact_path is None
    assert refreshed_job.failure_detail == "cannot synthesize 'Only sentence.'"


def test_run_once_processes_queued_clone_export_job_with_saved_preset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    upload = _upload_file(
        tmp_path,
        filename="sample.txt",
        content=LONG_SAMPLE_TEXT.encode("utf-8"),
    )
    reference_audio = _upload_file(
        tmp_path,
        filename="narrator.wav",
        content=b"RIFFdemo",
    )
    try:
        document = modules["documents"].import_document(upload)
        preset = modules["voice_presets"].create_voice_preset(
            name="Narrator",
            reference_audio=reference_audio,
            transcript="Alice reads sample text.",
        )
    finally:
        upload.file.close()
        reference_audio.file.close()

    job = modules["jobs"].enqueue_export_job(
        document_id=document.id,
        voice_preset_id=str(preset.id),
        format="wav",
    )

    clone_calls: list[dict[str, object]] = []

    class FakeCloneEngine:
        name = "qwen3_clone"

        def __init__(self, *, model_name: str = "") -> None:
            self.model_name = model_name

        def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
            raise AssertionError("clone exports should not use synthesize_to_file")

        def clone_to_file(
            self,
            *,
            text: str,
            output_path: Path,
            reference_audio_path: Path,
            transcript: str,
        ) -> Path:
            clone_calls.append(
                {
                    "text": text,
                    "reference_audio_path": reference_audio_path,
                    "transcript": transcript,
                }
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16_000)
                wav_file.writeframes(b"\x00\x00" * 100)
            return output_path

    monkeypatch.setattr(
        modules["worker_jobs"],
        "get_tts_engine",
        lambda name=None: (_ for _ in ()).throw(AssertionError("default engine should not be used")),
    )
    monkeypatch.setattr(
        modules["worker_jobs"],
        "build_clone_engine_for_profile",
        lambda clone_engine_id: FakeCloneEngine(model_name=settings.qwen_clone_model_name),
    )

    assert modules["worker_runner"].run_once() == 1

    refreshed_job = modules["jobs"].list_jobs()[0]
    export_path = Path(settings.export_root) / f"job-{job.id}.wav"

    assert refreshed_job.status == "completed"
    assert refreshed_job.artifact_path == str(export_path)
    assert refreshed_job.failure_detail is None
    assert export_path.exists()
    assert export_path.read_bytes().startswith(b"RIFF")
    assert len(clone_calls) >= 2
    assert {call["reference_audio_path"] for call in clone_calls} == {Path(preset.reference_path)}
    assert {call["transcript"] for call in clone_calls} == {"Alice reads sample text."}
    assert " ".join(call["text"] for call in clone_calls) == LONG_SAMPLE_TEXT


def test_run_once_uses_requested_large_clone_model_for_saved_preset_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "qwen_clone_large_model_name", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    modules = _load_modules()
    modules["documents"].init_database()

    upload = _upload_file(
        tmp_path,
        filename="sample.txt",
        content=b"First sentence.",
    )
    reference_audio = _upload_file(
        tmp_path,
        filename="narrator.wav",
        content=b"RIFFdemo",
    )
    try:
        document = modules["documents"].import_document(upload)
        preset = modules["voice_presets"].create_voice_preset(
            name="Narrator",
            reference_audio=reference_audio,
            transcript="Alice reads sample text.",
        )
    finally:
        upload.file.close()
        reference_audio.file.close()

    modules["jobs"].enqueue_export_job(
        document_id=document.id,
        voice_preset_id=str(preset.id),
        clone_engine_id="qwen3_clone_1_7b",
        format="wav",
    )

    model_names: list[str] = []

    class FakeCloneEngine:
        name = "qwen3_clone"

        def __init__(self, *, model_name: str = "") -> None:
            model_names.append(model_name)

        def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
            raise AssertionError("clone exports should not use synthesize_to_file")

        def clone_to_file(
            self,
            *,
            text: str,
            output_path: Path,
            reference_audio_path: Path,
            transcript: str,
        ) -> Path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16_000)
                wav_file.writeframes(b"\x00\x00" * 100)
            return output_path

    monkeypatch.setattr(
        modules["worker_jobs"],
        "build_clone_engine_for_profile",
        lambda clone_engine_id: FakeCloneEngine(
            model_name=(
                settings.qwen_clone_large_model_name
                if clone_engine_id == "qwen3_clone_1_7b"
                else settings.qwen_clone_model_name
            )
        ),
    )

    assert modules["worker_runner"].run_once() == 1
    assert model_names == ["Qwen/Qwen3-TTS-12Hz-1.7B-Base"]


def test_run_once_processes_split_chapter_export_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    upload = _upload_file(
        tmp_path,
        filename="sample.md",
        content=b"# Chapter One\nFirst sentence.\n\n# Chapter Two\nSecond sentence.",
    )
    try:
        document = modules["documents"].import_document(upload)
    finally:
        upload.file.close()

    modules["jobs"].enqueue_export_job(
        document_id=document.id,
        voice_preset_id="default",
        format="wav",
        split_chapters=True,
        artifact_basename="Alice Split",
    )

    assert modules["worker_runner"].run_once() == 1

    refreshed_job = modules["jobs"].list_jobs()[0]

    assert refreshed_job.status == "completed"
    assert refreshed_job.artifact_path is None
    assert refreshed_job.progress_percent == 100
    assert "alice-split" in refreshed_job.artifact_basename
    assert "Chapter One" in refreshed_job.artifact_manifest
    assert "Chapter Two" in refreshed_job.artifact_manifest


def test_run_once_honors_cancel_requested_mid_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    upload = _upload_file(
        tmp_path,
        filename="sample.txt",
        content=SHORT_SAMPLE_TEXT.encode("utf-8"),
    )
    try:
        document = modules["documents"].import_document(upload)
    finally:
        upload.file.close()

    job = modules["jobs"].enqueue_export_job(
        document_id=document.id,
        voice_preset_id="default",
        format="wav",
    )

    cancellation_requested = {"value": False}

    class CancelAwareEngine(TTSEngine):
        name = "cancel-aware"

        def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
            if not cancellation_requested["value"]:
                with db.session_scope() as session:
                    stored_job = session.get(import_module("app.models.job").Job, job.id)
                    assert stored_job is not None
                    stored_job.status = "cancel_requested"
                cancellation_requested["value"] = True

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16_000)
                wav_file.writeframes(b"\x00\x00" * 10)
            return output_path

    monkeypatch.setattr(modules["worker_jobs"], "get_tts_engine", lambda name=None: CancelAwareEngine())

    assert modules["worker_runner"].run_once() == 1

    refreshed_job = modules["jobs"].list_jobs()[0]

    assert refreshed_job.status == "canceled"
    assert refreshed_job.failure_detail is None
    assert refreshed_job.artifact_path is None


def test_get_tts_engine_uses_configured_piper_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "tts_engine", "piper", raising=False)
    monkeypatch.setattr(settings, "piper_binary", "piper-bin", raising=False)
    monkeypatch.setattr(settings, "piper_model_path", tmp_path / "voices" / "default.onnx", raising=False)

    registry_module = reload(import_module("app.tts.registry"))

    engine = registry_module.get_tts_engine()

    assert engine.name == "piper"
    assert engine.binary == "piper-bin"
    assert engine.model_path == tmp_path / "voices" / "default.onnx"


def test_clone_engine_uses_configured_qwen_model_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "qwen_clone_model_name", "Qwen/Qwen3-TTS-12Hz-0.6B-Base", raising=False)

    worker_jobs_module = reload(import_module("app.worker.jobs"))

    captured: dict[str, object] = {}

    class FakeCloneEngine:
        name = "qwen3_clone"

        def __init__(self, *, model_name: str) -> None:
            captured["model_name"] = model_name

    monkeypatch.setattr(
        worker_jobs_module,
        "build_clone_engine_for_profile",
        lambda clone_engine_id: FakeCloneEngine(model_name=settings.qwen_clone_model_name),
    )

    voice_preset = type("VoicePreset", (), {"engine": "qwen3_clone"})()
    job = type("Job", (), {"clone_engine_id": None})()

    engine = worker_jobs_module._build_clone_engine(job=job, voice_preset=voice_preset)

    assert isinstance(engine, FakeCloneEngine)
    assert captured == {"model_name": "Qwen/Qwen3-TTS-12Hz-0.6B-Base"}
