from pathlib import Path


def test_bootstrap_script_provisions_optional_kokoro_and_a_configurable_piper_voice() -> None:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap.sh"
    script_text = script_path.read_text(encoding="utf-8")

    assert "kokoro-onnx" in script_text
    assert "kokoro-v1.0.onnx" in script_text
    assert "voices-v1.0.bin" in script_text

    assert "en_US-lessac-medium" in script_text
    assert "PIPER_VOICE_MATRIX" in script_text
    assert "DOWNLOAD_KOKORO_MODELS" in script_text


def test_bootstrap_script_keeps_default_piper_symlink_and_installs_frontend() -> None:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap.sh"
    script_text = script_path.read_text(encoding="utf-8")

    assert "default.onnx" in script_text
    assert "default.onnx.json" in script_text
    assert "npm ci" in script_text


def test_host_scripts_do_not_launch_privileged_systemd_units() -> None:
    scripts_root = Path(__file__).resolve().parents[2] / "scripts"

    start_script = (scripts_root / "start.sh").read_text(encoding="utf-8")
    stop_script = (scripts_root / "stop.sh").read_text(encoding="utf-8")

    assert '[[ "${EUID:-$(id -u)}" -eq 0 ]]' in start_script
    assert "Refusing to run Open Choice Reader as root" in start_script
    assert "systemd-run" not in start_script
    assert "systemctl" not in start_script
    assert "systemctl" not in stop_script
