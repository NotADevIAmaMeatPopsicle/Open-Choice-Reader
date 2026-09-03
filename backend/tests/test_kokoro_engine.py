from pathlib import Path
from types import SimpleNamespace

from app.tts import kokoro_engine
from app.tts.kokoro_engine import KokoroEngine


class FakeKokoroModel:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, text: str, *, voice: str, speed: float):
        self.calls.append(
            {
                "text": text,
                "voice": voice,
                "speed": speed,
            }
        )
        return [0.1, 0.2, 0.3], 24000


def test_kokoro_engine_reports_available_with_python_runtime_and_assets_without_cli_binary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "models" / "kokoro" / "kokoro-v1.0.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")
    voices_path = model_path.parent / "voices-v1.0.bin"
    voices_path.write_bytes(b"voices")

    monkeypatch.setattr(kokoro_engine, "import_module", lambda name: SimpleNamespace(Kokoro=object()))

    engine = KokoroEngine(
        model_path=model_path,
        voices_path=voices_path,
        binary="kokoro-onnx",
    )

    engine_status = engine.get_engine_status()
    voice_options = engine.list_voice_options()

    assert engine_status.availability == "available"
    assert engine_status.availability_detail == "Kokoro is ready with 6 built-in voices."
    assert voice_options[0].availability == "available"


def test_kokoro_engine_synthesizes_with_python_runtime_without_cli_binary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "models" / "kokoro" / "kokoro-v1.0.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")
    voices_path = model_path.parent / "voices-v1.0.bin"
    voices_path.write_bytes(b"voices")

    fake_model = FakeKokoroModel()
    write_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        kokoro_engine,
        "import_module",
        lambda name: (
            SimpleNamespace(Kokoro=lambda model, voices: fake_model)
            if name == "kokoro_onnx"
            else SimpleNamespace(
                write=lambda path, samples, sample_rate, format=None: write_calls.append(
                    {
                        "path": Path(path),
                        "samples": samples,
                        "sample_rate": sample_rate,
                        "format": format,
                    }
                )
            )
        ),
    )

    output_path = tmp_path / "cache" / "chunk.wav.tmp"
    engine = KokoroEngine(
        model_path=model_path,
        voices_path=voices_path,
        binary="kokoro-onnx",
        voice_name="af_sarah",
    )

    result = engine.synthesize_to_file(text="Alice reads aloud.", output_path=output_path)

    assert result == output_path
    assert fake_model.calls == [
        {
            "text": "Alice reads aloud.",
            "voice": "af_sarah",
            "speed": 1.0,
        }
    ]
    assert write_calls == [
        {
            "path": output_path,
            "samples": [0.1, 0.2, 0.3],
            "sample_rate": 24000,
            "format": "WAV",
        }
    ]


def test_kokoro_engine_passes_narration_pace_as_native_speed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "models" / "kokoro" / "kokoro-v1.0.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")
    voices_path = model_path.parent / "voices-v1.0.bin"
    voices_path.write_bytes(b"voices")

    fake_model = FakeKokoroModel()

    monkeypatch.setattr(
        kokoro_engine,
        "import_module",
        lambda name: (
            SimpleNamespace(Kokoro=lambda model, voices: fake_model)
            if name == "kokoro_onnx"
            else SimpleNamespace(write=lambda path, samples, sample_rate, format=None: None)
        ),
    )

    engine = KokoroEngine(
        model_path=model_path,
        voices_path=voices_path,
        binary="kokoro-onnx",
        voice_name="af_sarah",
        pace=1.5,
    )

    engine.synthesize_to_file(text="Alice reads briskly.", output_path=tmp_path / "cache" / "chunk.wav")

    assert fake_model.calls == [
        {
            "text": "Alice reads briskly.",
            "voice": "af_sarah",
            "speed": 1.5,
        }
    ]
