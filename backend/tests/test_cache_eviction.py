import os
import time
from pathlib import Path

import pytest

from app.config import settings
from app.services.cache_eviction import (
    evict_stale_cached_audio,
    maybe_evict_stale_cached_audio,
    touch_cached_audio,
)


def _write_cached_file(relative_path: str, *, size: int, age_seconds: float, now: float) -> Path:
    path = Path(settings.cache_root) / "audio" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    timestamp = now - age_seconds
    os.utime(path, (timestamp, timestamp))
    return path


def test_eviction_removes_oldest_files_until_under_the_cap() -> None:
    now = time.time()
    oldest = _write_cached_file("mock/default/1/chunk-1.wav", size=400, age_seconds=6 * 3600, now=now)
    middle = _write_cached_file("mock/default/1/chunk-2.wav", size=400, age_seconds=4 * 3600, now=now)
    newest = _write_cached_file("mock/default/1/chunk-3.wav", size=400, age_seconds=2 * 3600, now=now)

    evicted = evict_stale_cached_audio(max_bytes=1000, now=now)

    assert evicted == 1
    assert not oldest.exists()
    assert middle.exists()
    assert newest.exists()


def test_eviction_is_a_noop_when_under_the_cap() -> None:
    now = time.time()
    cached = _write_cached_file("mock/default/1/chunk-1.wav", size=100, age_seconds=6 * 3600, now=now)

    evicted = evict_stale_cached_audio(max_bytes=1000, now=now)

    assert evicted == 0
    assert cached.exists()


def test_eviction_never_removes_files_inside_the_protection_window() -> None:
    now = time.time()
    recent_a = _write_cached_file("mock/default/1/chunk-1.wav", size=400, age_seconds=60, now=now)
    recent_b = _write_cached_file("mock/default/1/chunk-2.wav", size=400, age_seconds=120, now=now)

    evicted = evict_stale_cached_audio(max_bytes=100, now=now)

    assert evicted == 0
    assert recent_a.exists()
    assert recent_b.exists()


def test_touch_cached_audio_protects_recently_played_files() -> None:
    now = time.time()
    replayed = _write_cached_file("mock/default/1/chunk-1.wav", size=400, age_seconds=6 * 3600, now=now)
    idle = _write_cached_file("mock/default/1/chunk-2.wav", size=400, age_seconds=4 * 3600, now=now)

    touch_cached_audio(replayed)

    evicted = evict_stale_cached_audio(max_bytes=500, now=now)

    assert evicted == 1
    assert replayed.exists()
    assert not idle.exists()


def test_maybe_eviction_honors_the_marker_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    now = time.time()
    monkeypatch.setattr(settings, "audio_cache_eviction_minutes", 30, raising=False)
    monkeypatch.setattr(settings, "audio_cache_max_gb", 100 / (1024**3), raising=False)

    first_old = _write_cached_file("mock/default/1/chunk-1.wav", size=400, age_seconds=6 * 3600, now=now)
    assert maybe_evict_stale_cached_audio(now=now) == 1
    assert not first_old.exists()

    second_old = _write_cached_file("mock/default/1/chunk-2.wav", size=400, age_seconds=6 * 3600, now=now)
    assert maybe_evict_stale_cached_audio(now=now + 60) == 0
    assert second_old.exists()

    assert maybe_evict_stale_cached_audio(now=now + 31 * 60) == 1
    assert not second_old.exists()


def test_maybe_eviction_is_disabled_when_interval_is_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    now = time.time()
    monkeypatch.setattr(settings, "audio_cache_eviction_minutes", 0, raising=False)
    monkeypatch.setattr(settings, "audio_cache_max_gb", 100 / (1024**3), raising=False)

    cached = _write_cached_file("mock/default/1/chunk-1.wav", size=400, age_seconds=6 * 3600, now=now)

    assert maybe_evict_stale_cached_audio(now=now) == 0
    assert cached.exists()
