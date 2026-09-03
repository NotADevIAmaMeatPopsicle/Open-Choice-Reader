from importlib import import_module, reload
from pathlib import Path

import pytest

from app.config import settings


def _load_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'auth-service.db'}")

    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.auth_session"))
    reload(import_module("app.models.collection"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.theme_profile"))
    reload(import_module("app.models.user"))
    reload(import_module("app.models.user_invite"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    db_module = reload(db_module)
    db_module.init_database()
    return db_module


def _load_auth_service():
    return reload(import_module("app.services.auth"))


def test_hash_password_round_trip() -> None:
    auth_service = _load_auth_service()

    password_hash = auth_service.hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert auth_service.verify_password("correct horse battery staple", password_hash) is True
    assert auth_service.verify_password("tr0ub4dor", password_hash) is False


def test_issue_and_revoke_session_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_module = _load_db(tmp_path, monkeypatch)
    auth_service = _load_auth_service()

    with db_module.session_scope() as session:
        user = auth_service.create_user(
            session,
            username="admin",
            display_name="Admin User",
            password="correct horse battery staple",
            role="admin",
        )
        raw_token = auth_service.issue_session(session, user)

        resolved_user = auth_service.get_user_for_session_token(session, raw_token)
        assert resolved_user is not None
        assert resolved_user.username == "admin"

        auth_service.revoke_session(session, raw_token)
        assert auth_service.get_user_for_session_token(session, raw_token) is None
