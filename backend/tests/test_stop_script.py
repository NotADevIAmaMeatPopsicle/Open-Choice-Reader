from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


pytestmark = pytest.mark.skipif(os.name != "posix", reason="requires POSIX shell")


def _wait_for_exit(process: subprocess.Popen[str], *, timeout_seconds: float = 5.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            return True
        time.sleep(0.1)
    return process.poll() is not None


def test_stop_script_kills_orphaned_worker_loops(tmp_path: Path) -> None:
    source_script = Path(__file__).resolve().parents[2] / "scripts" / "stop.sh"
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    pid_dir = repo_root / ".runtime" / "pids"
    scripts_dir.mkdir(parents=True)
    pid_dir.mkdir(parents=True)

    stop_script = scripts_dir / "stop.sh"
    stop_script.write_text(source_script.read_text(encoding="utf-8"), encoding="utf-8")
    stop_script.chmod(0o755)

    ready_file = repo_root / ".runtime" / "worker.ready"
    ready_file.write_text("ready", encoding="utf-8")

    tracked_process = subprocess.Popen(["sleep", "300"], text=True)
    (pid_dir / "worker.pid").write_text(f"{tracked_process.pid}\n", encoding="utf-8")

    orphan_process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import time; time.sleep(300)",
            f"{repo_root}/backend",
            "app.worker.runner",
        ],
        text=True,
    )

    try:
        ps_snapshot = subprocess.run(
            ["ps", "-eo", "pid=,args="],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        result = subprocess.run(
            ["bash", str(stop_script)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert _wait_for_exit(tracked_process), "tracked worker PID should be terminated by the stop script"
        assert _wait_for_exit(orphan_process), (
            "orphaned worker loop should be terminated by the stop script\n"
            f"ps snapshot:\n{ps_snapshot}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert not ready_file.exists(), "worker readiness marker should be removed during shutdown"
        assert not (pid_dir / "worker.pid").exists(), "worker PID file should be removed during shutdown"
    finally:
        for process in (tracked_process, orphan_process):
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
