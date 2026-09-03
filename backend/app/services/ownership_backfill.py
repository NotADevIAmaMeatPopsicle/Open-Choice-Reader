from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
import app.models.app_setting as app_setting_model
import app.models.collection as collection_model
import app.models.document as document_model
import app.models.document_profile as document_profile_model
import app.models.job as job_model
import app.models.playback_session as playback_session_model
import app.models.theme_profile as theme_profile_model
import app.models.user as user_model
import app.models.user_setting as user_setting_model
import app.models.voice_preset as voice_preset_model
from app.services.user_storage import (
    ensure_user_storage_roots,
    user_cache_root,
    user_covers_root,
    user_export_root,
    user_source_root,
    user_voices_root,
)


def backfill_legacy_single_user_data(session: Session, user: "user_model.User") -> None:
    ensure_user_storage_roots(user.id)
    moved_paths: dict[tuple[str, str], str] = {}

    for document in session.scalars(
        select(document_model.Document)
        .where(document_model.Document.owner_user_id.is_(None))
        .order_by(document_model.Document.id)
    ):
        document.owner_user_id = user.id
        document.source_path = _adopt_path(
            moved_paths,
            source_path=document.source_path,
            destination_root=user_source_root(user.id),
            legacy_root=Path(settings.source_root),
        )

        profile = session.get(document_profile_model.DocumentProfile, document.id)
        if profile is not None and profile.cover_path:
            profile.cover_path = _adopt_path(
                moved_paths,
                source_path=profile.cover_path,
                destination_root=user_covers_root(user.id),
                legacy_root=Path(settings.storage_root) / "covers",
            )

    for playback_session in session.scalars(
        select(playback_session_model.PlaybackSession)
        .where(playback_session_model.PlaybackSession.user_id.is_(None))
        .order_by(playback_session_model.PlaybackSession.id)
    ):
        playback_session.user_id = user.id
        playback_session.audio_path = _adopt_path(
            moved_paths,
            source_path=playback_session.audio_path,
            destination_root=user_cache_root(user.id),
            legacy_root=Path(settings.cache_root),
        )

    for collection in session.scalars(
        select(collection_model.Collection)
        .where(collection_model.Collection.owner_user_id.is_(None))
        .order_by(collection_model.Collection.id)
    ):
        collection.owner_user_id = user.id

    for job in session.scalars(
        select(job_model.Job).where(job_model.Job.user_id.is_(None)).order_by(job_model.Job.id)
    ):
        job.user_id = user.id
        if job.artifact_path:
            job.artifact_path = _adopt_path(
                moved_paths,
                source_path=job.artifact_path,
                destination_root=user_export_root(user.id),
                legacy_root=Path(settings.export_root),
            )

    for preset in session.scalars(
        select(voice_preset_model.VoicePreset)
        .where(voice_preset_model.VoicePreset.owner_user_id.is_(None))
        .order_by(voice_preset_model.VoicePreset.id)
    ):
        preset.owner_user_id = user.id
        preset.reference_path = _adopt_path(
            moved_paths,
            source_path=preset.reference_path,
            destination_root=user_voices_root(user.id),
            legacy_root=Path(settings.storage_root) / "voices",
        )

    for theme in session.scalars(
        select(theme_profile_model.ThemeProfile).where(
            theme_profile_model.ThemeProfile.is_builtin.is_(False),
            theme_profile_model.ThemeProfile.owner_user_id.is_(None),
        )
    ):
        theme.owner_user_id = user.id

    for setting in session.scalars(select(app_setting_model.AppSetting)):
        if (
            session.get(
                user_setting_model.UserSetting, {"user_id": user.id, "key": setting.key}
            )
            is None
        ):
            session.add(
                user_setting_model.UserSetting(
                    user_id=user.id, key=setting.key, value=setting.value
                )
            )

    session.flush()


def _adopt_path(
    moved_paths: dict[tuple[str, str], str],
    *,
    source_path: str,
    destination_root: Path,
    legacy_root: Path,
) -> str:
    source = _resolve_legacy_path(source_path, legacy_root=legacy_root)
    if not source_path or source is None or not source.exists():
        return source_path

    cache_key = (str(source.resolve()), str(destination_root.resolve()))
    cached = moved_paths.get(cache_key)
    if cached is not None:
        return cached

    try:
        source.relative_to(legacy_root)
    except ValueError:
        return source_path

    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / source.name
    if destination.exists():
        destination = destination_root / f"{source.stem}-{source.stat().st_mtime_ns}{source.suffix}"

    source.replace(destination)
    moved_paths[cache_key] = str(destination)
    return str(destination)


def _resolve_legacy_path(source_path: str, *, legacy_root: Path) -> Path | None:
    if not source_path:
        return None

    configured_path = Path(source_path)
    candidates = [configured_path]

    if not configured_path.is_absolute():
        candidates.extend(
            [
                legacy_root.parent.parent / configured_path,
                legacy_root.parent / configured_path,
                legacy_root / configured_path.name,
            ]
        )

    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        if candidate.exists():
            return candidate

    return configured_path
