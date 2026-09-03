from importlib import import_module, reload
from pathlib import Path

import pytest

from app.config import settings


def _load_themes_module():
    reload(import_module("app.models"))
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.theme_profile"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)
    db_module.init_database()
    return reload(import_module("app.services.themes"))


@pytest.fixture()
def themes_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    return _load_themes_module()


def test_builtin_theme_seed_library_includes_house_and_inspired_packs(themes_module) -> None:
    themes = [theme for theme in themes_module.list_themes() if theme.is_builtin]

    assert len(themes) >= 12
    assert sum(theme.source_kind == "house" for theme in themes) >= 3
    assert sum(theme.source_label == "Reading-focused" for theme in themes) >= 3
    assert sum(theme.source_label == "Cinema-focused" for theme in themes) >= 3
    assert sum(theme.source_label == "Player-focused" for theme in themes) >= 3
    assert all("--color-bg" in theme.tokens and "--color-accent" in theme.tokens for theme in themes)


def test_builtin_theme_seed_library_includes_showcase_bundle(themes_module) -> None:
    themes = [theme for theme in themes_module.list_themes() if theme.is_builtin and theme.family == "showcase"]

    assert {theme.id for theme in themes} == {
        "sunlit-reading-room",
        "linen-ledger",
        "sea-glass-study",
        "garden-atlas",
        "mahogany-stacks",
        "after-hours-atrium",
        "candlewick-catalog",
        "projector-noir-library",
        "lantern-meadow-library",
        "grand-oak-observatory",
    }
    assert all(theme.background_asset_path for theme in themes)
    assert sum(theme.preview_variant == "light-airy" for theme in themes) == 4
    assert sum(theme.preview_variant == "dark-cozy" for theme in themes) == 4
    assert sum(theme.preview_variant == "showpiece" for theme in themes) == 2
