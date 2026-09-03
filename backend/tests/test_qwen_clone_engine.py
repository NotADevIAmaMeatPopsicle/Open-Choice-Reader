from pathlib import Path
from types import SimpleNamespace

import pytest

from app.tts import qwen_clone_engine
from app.tts.qwen_clone_engine import Qwen3CloneEngine


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_voice_clone(
        self,
        *,
        text: str,
        language: str,
        ref_audio: str,
        ref_text: str,
    ):
        self.calls.append(
            {
                "text": text,
                "language": language,
                "ref_audio": ref_audio,
                "ref_text": ref_text,
            }
        )
        return [[0.1, 0.2, 0.3]], 24000


def test_clone_to_file_uses_qwen_generate_voice_clone_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_model = FakeModel()
    from_pretrained_calls: list[dict[str, object]] = []
    write_calls: list[dict[str, object]] = []

    def fake_from_pretrained(model_name: str, **kwargs):
        from_pretrained_calls.append({"model_name": model_name, "kwargs": kwargs})
        return fake_model

    monkeypatch.setattr(
        qwen_clone_engine,
        "import_module",
        lambda name: SimpleNamespace(
            Qwen3TTSModel=SimpleNamespace(from_pretrained=fake_from_pretrained),
        ),
    )
    monkeypatch.setattr(
        qwen_clone_engine,
        "_soundfile",
        lambda: SimpleNamespace(
            write=lambda path, samples, sample_rate, **kwargs: write_calls.append(
                {
                    "path": Path(path),
                    "samples": samples,
                    "sample_rate": sample_rate,
                    "kwargs": kwargs,
                }
            )
        ),
    )

    output_path = tmp_path / "clone.wav"
    reference_audio_path = tmp_path / "reference.wav"
    reference_audio_path.write_bytes(b"RIFFdemo")

    engine = Qwen3CloneEngine(model_name="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    result = engine.clone_to_file(
        text="Hello there",
        output_path=output_path,
        reference_audio_path=reference_audio_path,
        transcript="Transcript text",
    )

    assert result == output_path
    assert from_pretrained_calls == [
        {
            "model_name": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "kwargs": {},
        }
    ]
    assert fake_model.calls == [
        {
            "text": "Hello there",
            "language": "English",
            "ref_audio": str(reference_audio_path),
            "ref_text": "Transcript text",
        }
    ]
    assert write_calls == [
        {
            "path": output_path,
            "samples": [0.1, 0.2, 0.3],
            "sample_rate": 24000,
            "kwargs": {"format": "WAV"},
        }
    ]


def test_clone_to_file_forces_wav_format_for_temp_cache_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_model = FakeModel()
    write_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        qwen_clone_engine,
        "import_module",
        lambda name: SimpleNamespace(
            Qwen3TTSModel=SimpleNamespace(from_pretrained=lambda *args, **kwargs: fake_model),
        ),
    )
    monkeypatch.setattr(
        qwen_clone_engine,
        "_soundfile",
        lambda: SimpleNamespace(
            write=lambda path, samples, sample_rate, **kwargs: write_calls.append(
                {
                    "path": Path(path),
                    "samples": samples,
                    "sample_rate": sample_rate,
                    "kwargs": kwargs,
                }
            )
        ),
    )

    output_path = tmp_path / "clone.wav.deadbeef.tmp"
    reference_audio_path = tmp_path / "reference.wav"
    reference_audio_path.write_bytes(b"RIFFdemo")

    engine = Qwen3CloneEngine(model_name="Qwen/Qwen3-TTS-12Hz-0.6B-Base")
    engine.clone_to_file(
        text="Live clone cache test",
        output_path=output_path,
        reference_audio_path=reference_audio_path,
        transcript="Reference transcript",
    )

    assert write_calls == [
        {
            "path": output_path,
            "samples": [0.1, 0.2, 0.3],
            "sample_rate": 24000,
            "kwargs": {"format": "WAV"},
        }
    ]


def test_clone_to_file_requires_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    import_attempted = False

    def fake_import_module(name: str):
        nonlocal import_attempted
        import_attempted = True
        raise AssertionError("runtime should not load when transcript is missing")

    monkeypatch.setattr(qwen_clone_engine, "import_module", fake_import_module)

    engine = Qwen3CloneEngine()

    with pytest.raises(ValueError, match="transcript"):
        engine.clone_to_file(
            text="Hello there",
            output_path=Path("clone.wav"),
            reference_audio_path=Path("reference.wav"),
            transcript="",
        )

    assert import_attempted is False


def test_qwen_engine_reports_runtime_missing_as_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        qwen_clone_engine,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
    )

    engine = Qwen3CloneEngine()
    engine_status = engine.get_engine_status()

    assert engine_status.availability == "unavailable"
    assert engine_status.availability_detail == "Qwen3 clone runtime is not installed on this host."
    assert engine_status.supports_live_reading is True
    assert engine_status.supports_export is True


def test_qwen_engine_reports_available_when_runtime_import_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        qwen_clone_engine,
        "import_module",
        lambda name: SimpleNamespace(Qwen3TTSModel=SimpleNamespace(from_pretrained=lambda *args, **kwargs: object())),
    )

    engine = Qwen3CloneEngine()
    engine_status = engine.get_engine_status()

    assert engine_status.availability == "available"
    assert (
        engine_status.availability_detail
        == "Qwen3 clone live reading and exports are ready when a saved preset is selected."
    )
    assert engine_status.supports_live_reading is True
    assert engine_status.supports_export is True


def test_synthesize_to_file_uses_embedded_reference_voice_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clone_calls: list[dict[str, object]] = []
    reference_audio_path = tmp_path / "reference.wav"
    reference_audio_path.write_bytes(b"RIFFdemo")
    output_path = tmp_path / "output.wav"

    engine = Qwen3CloneEngine(
        model_name="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        reference_audio_path=reference_audio_path,
        transcript="Reference transcript",
    )

    def fake_clone_to_file(*, text: str, output_path: Path, reference_audio_path: Path, transcript: str) -> Path:
        clone_calls.append(
            {
                "text": text,
                "output_path": output_path,
                "reference_audio_path": reference_audio_path,
                "transcript": transcript,
            }
        )
        return output_path

    monkeypatch.setattr(engine, "clone_to_file", fake_clone_to_file)

    result = engine.synthesize_to_file(text="Hello there", output_path=output_path)

    assert result == output_path
    assert clone_calls == [
        {
            "text": "Hello there",
            "output_path": output_path,
            "reference_audio_path": reference_audio_path,
            "transcript": "Reference transcript",
        }
    ]
