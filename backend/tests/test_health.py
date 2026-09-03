from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, create_storage_roots


def test_healthcheck_does_not_expose_runtime_paths(tmp_path: Path) -> None:
    create_storage_roots()
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"status": "ok"}
    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "data" / "source").is_dir()
    assert (tmp_path / "data" / "cache").is_dir()
    assert (tmp_path / "data" / "exports").is_dir()
    assert (tmp_path / "data" / "inbox").is_dir()
