from pathlib import Path
import shutil

from sqlalchemy import delete

from app import db
from app.config import settings
from app.models.collection import Collection, CollectionDocument
from app.models.document import Document
from app.models.document_profile import DocumentProfile
from app.models.document_progress import DocumentProgress
from app.models.job import Job
from app.models.playback_session import PlaybackSession
from app.models.section import Section
from app.models.text_chunk import TextChunk


def reset_library() -> None:
    with db.session_scope() as session:
        for model in (
            CollectionDocument,
            Collection,
            Job,
            PlaybackSession,
            DocumentProgress,
            TextChunk,
            Section,
            DocumentProfile,
            Document,
        ):
            session.execute(delete(model))

    for path in (
        settings.source_root,
        settings.storage_root / "covers",
        settings.export_root,
        settings.seed_download_root,
        settings.cache_root / "audio",
    ):
        _reset_directory(Path(path))

    users_root = Path(settings.storage_root) / "users"
    if users_root.is_dir():
        for user_root in users_root.iterdir():
            if not user_root.is_dir():
                continue
            for child_name in ("source", "covers", "cache", "exports"):
                _reset_directory(user_root / child_name)


def _reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
