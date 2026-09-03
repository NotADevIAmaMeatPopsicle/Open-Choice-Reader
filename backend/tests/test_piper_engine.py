from pathlib import Path
import sys

from app.tts.piper_engine import PiperEngine


def test_piper_engine_falls_back_to_current_python_directory_for_binary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "voices" / "default.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")

    venv_bin_dir = tmp_path / ".venv" / "bin"
    venv_bin_dir.mkdir(parents=True, exist_ok=True)
    python_executable = venv_bin_dir / "python"
    python_executable.write_text("", encoding="utf-8")
    bundled_piper = venv_bin_dir / "piper"
    bundled_piper.write_text("", encoding="utf-8")

    run_calls: list[dict[str, object]] = []

    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: None)
    monkeypatch.setattr(sys, "executable", str(python_executable))
    monkeypatch.setattr(
        "app.tts.piper_engine.subprocess.run",
        lambda args, input, check: run_calls.append(
            {
                "args": args,
                "input": input,
                "check": check,
            }
        ),
    )

    output_path = tmp_path / "cache" / "chunk.wav"
    engine = PiperEngine(model_path=model_path, binary="piper")

    result = engine.synthesize_to_file(text="Alice reads aloud.", output_path=output_path)

    assert result == output_path
    assert run_calls == [
        {
            "args": [
                str(bundled_piper),
                "--model",
                str(model_path),
                "--output_file",
                str(output_path),
            ],
            "input": b"Alice reads aloud.",
            "check": True,
        }
    ]


def test_piper_engine_passes_narration_pace_as_inverse_length_scale(
    monkeypatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "voices" / "default.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")

    venv_bin_dir = tmp_path / ".venv" / "bin"
    venv_bin_dir.mkdir(parents=True, exist_ok=True)
    python_executable = venv_bin_dir / "python"
    python_executable.write_text("", encoding="utf-8")
    bundled_piper = venv_bin_dir / "piper"
    bundled_piper.write_text("", encoding="utf-8")

    run_calls: list[dict[str, object]] = []

    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: None)
    monkeypatch.setattr(sys, "executable", str(python_executable))
    monkeypatch.setattr(
        "app.tts.piper_engine.subprocess.run",
        lambda args, input, check: run_calls.append(
            {
                "args": args,
                "input": input,
                "check": check,
            }
        ),
    )

    output_path = tmp_path / "cache" / "chunk.wav"
    engine = PiperEngine(model_path=model_path, binary="piper", pace=1.25)

    engine.synthesize_to_file(text="Alice reads briskly.", output_path=output_path)

    assert run_calls == [
        {
            "args": [
                str(bundled_piper),
                "--model",
                str(model_path),
                "--output_file",
                str(output_path),
                "--length_scale",
                "0.800",
            ],
            "input": b"Alice reads briskly.",
            "check": True,
        }
    ]


def test_piper_engine_lists_builtin_voices_from_the_model_directory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    model_dir = tmp_path / "models" / "piper"
    model_dir.mkdir(parents=True, exist_ok=True)
    default_model = model_dir / "fast-reader.onnx"
    extra_model = model_dir / "warm-reader.onnx"
    default_model.write_bytes(b"default")
    extra_model.write_bytes(b"extra")

    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: str(tmp_path / "bin" / binary))

    engine = PiperEngine(model_path=default_model, binary="piper")

    voice_options = engine.list_voice_options()
    engine_status = engine.get_engine_status()

    assert [voice_option.id for voice_option in voice_options] == [
        "builtin:piper:fast-reader",
        "builtin:piper:warm-reader",
    ]
    assert [voice_option.name for voice_option in voice_options] == ["Fast Reader", "Warm Reader"]
    assert engine_status.availability == "available"
    assert engine_status.availability_detail == "Piper is ready with 2 local voices."


def test_piper_engine_reports_unavailable_when_the_configured_model_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    missing_model = tmp_path / "models" / "piper" / "fast-reader.onnx"

    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: None)

    engine = PiperEngine(model_path=missing_model, binary="piper")

    voice_options = engine.list_voice_options()
    engine_status = engine.get_engine_status()

    assert voice_options == [
        engine.list_voice_options()[0]
    ]
    assert voice_options[0].availability == "unavailable"
    assert voice_options[0].availability_detail == "Piper needs a model file and binary before this voice can run."
    assert engine_status.availability == "unavailable"
    assert engine_status.availability_detail == "Piper needs a model file and binary before live reading can start."


def test_piper_engine_falls_back_to_python_module_when_cli_is_not_discoverable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "voices" / "default.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")

    venv_bin_dir = tmp_path / ".venv" / "bin"
    venv_bin_dir.mkdir(parents=True, exist_ok=True)
    python_executable = venv_bin_dir / "python"
    python_executable.write_text("", encoding="utf-8")

    run_calls: list[dict[str, object]] = []

    monkeypatch.setattr("app.tts.piper_engine.shutil.which", lambda binary: None)
    monkeypatch.setattr(sys, "executable", str(python_executable))
    monkeypatch.setattr(
        "app.tts.piper_engine.subprocess.run",
        lambda args, input, check: run_calls.append(
            {
                "args": args,
                "input": input,
                "check": check,
            }
        ),
    )

    engine = PiperEngine(model_path=model_path, binary="piper")

    assert engine.get_engine_status().availability == "available"

    output_path = tmp_path / "cache" / "chunk.wav"
    result = engine.synthesize_to_file(text="Alice reads aloud.", output_path=output_path)

    assert result == output_path
    assert run_calls == [
        {
            "args": [
                str(python_executable),
                "-m",
                "piper",
                "--model",
                str(model_path),
                "--output_file",
                str(output_path),
            ],
            "input": b"Alice reads aloud.",
            "check": True,
        }
    ]
