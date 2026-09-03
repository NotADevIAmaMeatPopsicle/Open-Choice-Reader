from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_root_serves_built_frontend_index(tmp_path: Path, monkeypatch) -> None:
    dist_root = tmp_path / "dist"
    dist_root.mkdir()
    (dist_root / "index.html").write_text("<html><body>Alice Reader Shell</body></html>", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_root", dist_root, raising=False)

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Alice Reader Shell" in response.text


def test_spa_routes_fall_back_to_index_html(tmp_path: Path, monkeypatch) -> None:
    dist_root = tmp_path / "dist"
    dist_root.mkdir()
    (dist_root / "index.html").write_text("<html><body>Alice Reader Shell</body></html>", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_root", dist_root, raising=False)

    with TestClient(app) as client:
        response = client.get("/library")

    assert response.status_code == 200
    assert "Alice Reader Shell" in response.text


def test_frontend_assets_are_served_from_dist_directory(tmp_path: Path, monkeypatch) -> None:
    dist_root = tmp_path / "dist"
    asset_dir = dist_root / "assets"
    asset_dir.mkdir(parents=True)
    (dist_root / "index.html").write_text("<html><body>Alice Reader Shell</body></html>", encoding="utf-8")
    (asset_dir / "app.js").write_text("console.log('alice-reader');", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_root", dist_root, raising=False)

    with TestClient(app) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "alice-reader" in response.text
