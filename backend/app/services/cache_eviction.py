import os
import time
from pathlib import Path

from app.config import settings

PROTECTED_FILE_AGE_SECONDS = 60 * 60
EVICTION_TARGET_RATIO = 0.9
EVICTION_MARKER_FILENAME = ".audio-eviction-marker"


def touch_cached_audio(path: Path) -> None:
    try:
        os.utime(path, None)
    except OSError:
        pass


def maybe_evict_stale_cached_audio(*, now: float | None = None) -> int:
    interval_seconds = settings.audio_cache_eviction_minutes * 60
    if interval_seconds <= 0:
        return 0

    current_time = now if now is not None else time.time()
    marker_path = Path(settings.cache_root) / EVICTION_MARKER_FILENAME

    try:
        marker_age = current_time - marker_path.stat().st_mtime
        if marker_age < interval_seconds:
            return 0
    except OSError:
        pass

    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.touch()
        os.utime(marker_path, (current_time, current_time))
    except OSError:
        return 0

    return evict_stale_cached_audio(now=current_time)


def evict_stale_cached_audio(*, max_bytes: int | None = None, now: float | None = None) -> int:
    cap_bytes = max_bytes if max_bytes is not None else int(settings.audio_cache_max_gb * 1024**3)
    if cap_bytes <= 0:
        return 0

    audio_root = Path(settings.cache_root) / "audio"
    if not audio_root.exists():
        return 0

    current_time = now if now is not None else time.time()

    cached_files: list[tuple[float, int, Path]] = []
    total_size = 0
    for path in audio_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            stat_result = path.stat()
        except OSError:
            continue
        total_size += stat_result.st_size
        cached_files.append((stat_result.st_mtime, stat_result.st_size, path))

    if total_size <= cap_bytes:
        return 0

    target_bytes = int(cap_bytes * EVICTION_TARGET_RATIO)
    evicted_count = 0
    for mtime, size, path in sorted(cached_files):
        if total_size <= target_bytes:
            break
        if current_time - mtime < PROTECTED_FILE_AGE_SECONDS:
            continue
        try:
            path.unlink()
        except OSError:
            continue
        total_size -= size
        evicted_count += 1

    return evicted_count
