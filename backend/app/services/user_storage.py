from pathlib import Path

from app.config import settings


def user_root(user_id: int) -> Path:
    return Path(settings.storage_root) / "users" / str(user_id)


def user_source_root(user_id: int) -> Path:
    return user_root(user_id) / "source"


def user_cache_root(user_id: int) -> Path:
    return user_root(user_id) / "cache"


def user_export_root(user_id: int) -> Path:
    return user_root(user_id) / "exports"


def user_inbox_root(user_id: int) -> Path:
    return user_root(user_id) / "inbox"


def user_covers_root(user_id: int) -> Path:
    return user_root(user_id) / "covers"


def user_voices_root(user_id: int) -> Path:
    return user_root(user_id) / "voices"


def ensure_user_storage_roots(user_id: int) -> dict[str, Path]:
    roots = {
        "root": user_root(user_id),
        "source": user_source_root(user_id),
        "cache": user_cache_root(user_id),
        "exports": user_export_root(user_id),
        "inbox": user_inbox_root(user_id),
        "covers": user_covers_root(user_id),
        "voices": user_voices_root(user_id),
    }
    for path in roots.values():
        path.mkdir(parents=True, exist_ok=True)
    return roots
