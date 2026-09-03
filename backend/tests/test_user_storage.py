from pathlib import Path

import pytest

from app.config import settings


def test_user_storage_roots_are_namespaced_per_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "storage_root", tmp_path / "data")

    from app.services.user_storage import (
        ensure_user_storage_roots,
        user_cache_root,
        user_covers_root,
        user_export_root,
        user_inbox_root,
        user_root,
        user_source_root,
        user_voices_root,
    )

    roots = ensure_user_storage_roots(42)

    assert user_root(42) == tmp_path / "data" / "users" / "42"
    assert user_source_root(42) == tmp_path / "data" / "users" / "42" / "source"
    assert user_cache_root(42) == tmp_path / "data" / "users" / "42" / "cache"
    assert user_export_root(42) == tmp_path / "data" / "users" / "42" / "exports"
    assert user_inbox_root(42) == tmp_path / "data" / "users" / "42" / "inbox"
    assert user_covers_root(42) == tmp_path / "data" / "users" / "42" / "covers"
    assert user_voices_root(42) == tmp_path / "data" / "users" / "42" / "voices"

    for path in roots.values():
        assert path.is_dir()
