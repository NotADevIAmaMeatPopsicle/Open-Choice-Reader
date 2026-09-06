from pathlib import Path

from app.config import settings
from app.services.storage_permissions import ensure_private_directory


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
        ensure_private_directory(path)
    return roots


def user_storage_usage_bytes(user_id: int) -> int:
    root = user_root(user_id)
    if not root.exists():
        return 0

    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def ensure_user_storage_capacity(user_id: int, additional_bytes: int) -> None:
    if additional_bytes < 0:
        raise ValueError("additional_bytes must not be negative")
    maximum = settings.user_storage_max_bytes
    if maximum <= 0:
        return
    usage = user_storage_usage_bytes(user_id)
    if usage + additional_bytes > maximum:
        raise ValueError(
            "Storage limit reached; remove library items, voice presets, or exports before retrying"
        )
