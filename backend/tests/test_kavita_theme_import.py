from importlib import import_module, reload
from pathlib import Path

import pytest

from app.config import settings


def _load_services():
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

    themes_module = reload(import_module("app.services.themes"))
    kavita_module = reload(import_module("app.services.kavita_theme_import"))

    db_module.init_database()
    return themes_module, kavita_module


@pytest.fixture()
def services(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    return _load_services()


def test_import_kavita_theme_materializes_native_theme_and_reports_mapping(services) -> None:
    themes_module, kavita_module = services

    result = kavita_module.import_kavita_theme(
        css_text="""
        :root .bg-midnight-harbor {
          --primary-color: #68b7ff;
          --primary-color-dark-shade: #245d91;
          --bs-body-bg: #0b1118;
          --body-text-color: #eef5fb;
          --text-muted-color: #9fb5c7;
          --navbar-bg-color: #162636;
          --accent-bg-color: rgba(24, 39, 55, 0.92);
          --input-border-color: rgba(104, 183, 255, 0.16);
          --error-color: #ff8f8f;
          --unsupported-token: #ffffff;
        }
        """,
        name="Midnight Harbor",
        source_reference="midnight-harbor.css",
    )

    assert result.theme.id == "midnight-harbor"
    assert result.theme.name == "Midnight Harbor"
    assert result.theme.source_kind == "imported_kavita"
    assert result.theme.source_label == "Kavita import"
    assert result.theme.source_reference == "midnight-harbor.css"
    assert result.theme.tokens["--color-bg"] == "#0b1118"
    assert result.theme.tokens["--color-accent"] == "#68b7ff"
    assert result.theme.tokens["--color-accent-strong"] == "#245d91"
    assert result.theme.tokens["--color-panel-strong"] == "#162636"
    assert result.report.detected_variable_count == 10
    assert any(
        mapping.source_variable == "--primary-color" and mapping.target_token == "--color-accent"
        for mapping in result.report.mapped_variables
    )
    assert "--unsupported-token" in result.report.ignored_variables
    assert any(
        fallback.target_token == "--color-success" and fallback.reason == "retained_default_theme_value"
        for fallback in result.report.fallback_tokens
    )

    persisted = themes_module.get_theme("midnight-harbor")
    assert persisted.source_kind == "imported_kavita"
    assert persisted.tokens["--color-bg"] == "#0b1118"


def test_import_kavita_theme_rejects_css_without_supported_variables(services) -> None:
    _, kavita_module = services

    with pytest.raises(ValueError, match="No supported Kavita theme variables were found"):
        kavita_module.import_kavita_theme(
            css_text="""
            :root .bg-empty-import {
              color: #ffffff;
              background: #000000;
            }
            """,
            name="Empty Import",
            source_reference="empty-import.css",
        )
