from types import SimpleNamespace
from pathlib import Path

from app.config import settings
from app.tts.registry import (
    build_clone_engine_for_profile,
    build_live_engine_for_voice_option,
    list_engine_statuses,
    list_voice_options,
)


def _prepare_runtime_files(tmp_path: Path) -> dict[str, Path]:
    runtime_bin = tmp_path / "bin"
    runtime_bin.mkdir(parents=True, exist_ok=True)
    for binary_name in ("piper", "kokoro-onnx"):
        (runtime_bin / binary_name).write_text("", encoding="utf-8")

    piper_root = tmp_path / "models" / "piper"
    piper_root.mkdir(parents=True, exist_ok=True)
    for filename in (
        "en-us-lessac-medium.onnx",
        "en-us-amy-medium.onnx",
        "en-us-ryan-high.onnx",
        "narrator-default.onnx",
    ):
        (piper_root / filename).write_bytes(b"model")

    kokoro_root = tmp_path / "models" / "kokoro"
    kokoro_root.mkdir(parents=True, exist_ok=True)
    kokoro_model_path = kokoro_root / "kokoro-v1.0.onnx"
    kokoro_model_path.write_bytes(b"model")
    kokoro_voices_path = kokoro_root / "voices-v1.0.bin"
    kokoro_voices_path.write_bytes(b"voices")

    return {
        "runtime_bin": runtime_bin,
        "piper_model_path": piper_root / "en-us-lessac-medium.onnx",
        "kokoro_model_path": kokoro_model_path,
        "kokoro_voices_path": kokoro_voices_path,
    }


def _patch_kokoro_runtime_available(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tts.kokoro_engine.import_module",
        lambda name: SimpleNamespace(Kokoro=object()),
    )


def test_list_engine_statuses_exposes_four_shipped_profiles(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime_files = _prepare_runtime_files(tmp_path)

    monkeypatch.setattr(settings, "piper_model_path", runtime_files["piper_model_path"])
    monkeypatch.setattr(settings, "qwen_clone_model_name", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
    monkeypatch.setattr(settings, "qwen_clone_large_model_name", "Qwen/Qwen3-TTS-12Hz-1.7B-Base", raising=False)
    monkeypatch.setattr(settings, "kokoro_binary", "kokoro-onnx", raising=False)
    monkeypatch.setattr(settings, "kokoro_model_path", runtime_files["kokoro_model_path"], raising=False)
    monkeypatch.setattr(settings, "kokoro_voices_path", runtime_files["kokoro_voices_path"], raising=False)
    _patch_kokoro_runtime_available(monkeypatch)
    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: str(runtime_files["runtime_bin"] / binary))
    monkeypatch.setattr(
        "app.tts.qwen_clone_engine.import_module",
        lambda name: SimpleNamespace(Qwen3TTSModel=object()),
    )

    engine_statuses = list_engine_statuses()

    assert [status.engine for status in engine_statuses] == [
        "kokoro",
        "piper",
        "qwen3_clone_0_6b",
        "qwen3_clone_1_7b",
    ]
    assert [status.engine_family for status in engine_statuses] == [
        "kokoro",
        "piper",
        "qwen3_clone",
        "qwen3_clone",
    ]
    assert [status.voice_count for status in engine_statuses] == [6, 4, 0, 0]
    assert [status.model_name for status in engine_statuses] == [
        "Kokoro-82M ONNX",
        None,
        "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    ]


def test_list_voice_options_exposes_ten_built_in_voices_across_kokoro_and_piper(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime_files = _prepare_runtime_files(tmp_path)

    monkeypatch.setattr(settings, "tts_engine", "piper")
    monkeypatch.setattr(settings, "piper_model_path", runtime_files["piper_model_path"])
    monkeypatch.setattr(settings, "kokoro_binary", "kokoro-onnx", raising=False)
    monkeypatch.setattr(settings, "kokoro_model_path", runtime_files["kokoro_model_path"], raising=False)
    monkeypatch.setattr(settings, "kokoro_voices_path", runtime_files["kokoro_voices_path"], raising=False)
    _patch_kokoro_runtime_available(monkeypatch)
    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: str(runtime_files["runtime_bin"] / binary))
    monkeypatch.setattr("app.services.voice_presets.list_voice_presets", lambda owner_user_id=None: [])

    voice_options = list_voice_options()
    built_in_voices = [voice_option for voice_option in voice_options if voice_option.voice_type == "built_in"]

    assert len(built_in_voices) == 10
    assert [voice_option.id for voice_option in built_in_voices[:6]] == [
        "builtin:kokoro:af-heart",
        "builtin:kokoro:af-bella",
        "builtin:kokoro:af-nicole",
        "builtin:kokoro:af-sarah",
        "builtin:kokoro:af-sky",
        "builtin:kokoro:am-michael",
    ]
    assert [voice_option.engine_family for voice_option in built_in_voices] == [
        "kokoro",
        "kokoro",
        "kokoro",
        "kokoro",
        "kokoro",
        "kokoro",
        "piper",
        "piper",
        "piper",
        "piper",
    ]
    assert built_in_voices[0].model_name == "Kokoro-82M ONNX"
    assert built_in_voices[6].model_name is None


def test_build_live_engine_for_voice_option_returns_selected_kokoro_family(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime_files = _prepare_runtime_files(tmp_path)

    monkeypatch.setattr(settings, "tts_engine", "piper")
    monkeypatch.setattr(settings, "piper_model_path", runtime_files["piper_model_path"])
    monkeypatch.setattr(settings, "kokoro_binary", "kokoro-onnx", raising=False)
    monkeypatch.setattr(settings, "kokoro_model_path", runtime_files["kokoro_model_path"], raising=False)
    monkeypatch.setattr(settings, "kokoro_voices_path", runtime_files["kokoro_voices_path"], raising=False)
    _patch_kokoro_runtime_available(monkeypatch)
    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: str(runtime_files["runtime_bin"] / binary))
    monkeypatch.setattr("app.services.voice_presets.list_voice_presets", lambda owner_user_id=None: [])

    engine = build_live_engine_for_voice_option("builtin:kokoro:af-sarah")

    assert engine.name == "kokoro"
    assert engine.voice_name == "af_sarah"


def test_build_clone_engine_for_profile_returns_requested_large_qwen_model(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime_files = _prepare_runtime_files(tmp_path)

    monkeypatch.setattr(settings, "tts_engine", "piper")
    monkeypatch.setattr(settings, "piper_model_path", runtime_files["piper_model_path"])
    monkeypatch.setattr(settings, "qwen_clone_model_name", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
    monkeypatch.setattr(settings, "qwen_clone_large_model_name", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")

    engine = build_clone_engine_for_profile("qwen3_clone_1_7b")

    assert engine.name == "qwen3_clone_1_7b"
    assert engine.model_name == "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
