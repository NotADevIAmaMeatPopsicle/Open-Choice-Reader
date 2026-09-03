from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from app import db
import app.models.document as document_model
import app.models.document_profile as document_profile_model
import app.models.document_progress as document_progress_model
import app.models.section as section_model
import app.models.text_chunk as text_chunk_model
from app.services.covers import write_cover_asset
from app.services.user_storage import user_covers_root


@dataclass(slots=True)
class LibraryDocumentRecord:
    id: int
    title: str
    format: str
    status: str
    author: str | None
    cover_url: str
    summary: str | None
    total_sections: int
    total_chunks: int
    estimated_duration_seconds: int
    current_chunk_index: int | None
    progress_percent: float
    bookmark_enabled: bool
    is_finished: bool
    finished_at: datetime | None
    last_opened_at: datetime | None
    source_provider: str | None
    source_provider_name: str | None
    source_provider_url: str | None
    source_url: str | None
    source_site_name: str | None
    import_mode: str | None


@dataclass(slots=True)
class LibrarySummaryRecord:
    continue_reading: list[LibraryDocumentRecord]
    recent_documents: list[LibraryDocumentRecord]


@dataclass(slots=True)
class LibraryDocumentSectionRecord:
    id: int
    position: int
    title: str | None
    chunk_start_index: int
    chunk_count: int
    preview_text: str


@dataclass(slots=True)
class LibraryDocumentDetailRecord(LibraryDocumentRecord):
    sections: list[LibraryDocumentSectionRecord]


@dataclass(slots=True)
class DocumentProgressState:
    bookmark_enabled: bool
    current_chunk_index: int | None
    finished_at: datetime | None
    has_bookmark: bool
    is_finished: bool
    last_opened_at: datetime | None


def list_library_documents(*, owner_user_id: int | None = None) -> list[LibraryDocumentRecord]:
    with db.session_scope() as session:
        statement = select(document_model.Document).order_by(document_model.Document.id.desc())
        if owner_user_id is not None:
            statement = statement.where(document_model.Document.owner_user_id == owner_user_id)
        documents = list(session.scalars(statement))
        return [_build_library_record(session=session, document=document) for document in documents]


def get_library_document(document_id: int, *, owner_user_id: int | None = None) -> LibraryDocumentRecord | None:
    with db.session_scope() as session:
        document = _get_owned_document(session=session, document_id=document_id, owner_user_id=owner_user_id)
        if document is None:
            return None
        return _build_library_record(session=session, document=document)


def get_library_document_detail(
    document_id: int,
    *,
    owner_user_id: int | None = None,
) -> LibraryDocumentDetailRecord | None:
    with db.session_scope() as session:
        document = _get_owned_document(session=session, document_id=document_id, owner_user_id=owner_user_id)
        if document is None:
            return None

        library_record = _build_library_record(session=session, document=document)
        section_records = _build_section_records(document_id=document.id, session=session)
        return LibraryDocumentDetailRecord(**asdict(library_record), sections=section_records)


def get_library_summary(*, owner_user_id: int | None = None) -> LibrarySummaryRecord:
    documents = list_library_documents(owner_user_id=owner_user_id)
    continue_reading = [
        document
        for document in documents
        if document.current_chunk_index is not None and document.last_opened_at is not None
    ]
    continue_reading.sort(
        key=lambda document: document.last_opened_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    recent_documents = sorted(documents, key=lambda document: document.id, reverse=True)
    return LibrarySummaryRecord(
        continue_reading=continue_reading,
        recent_documents=recent_documents,
    )


def get_cover_path(document_id: int, *, owner_user_id: int | None = None) -> Path:
    with db.session_scope() as session:
        document = _get_owned_document(session=session, document_id=document_id, owner_user_id=owner_user_id)
        if document is None:
            raise ValueError(f"Document {document_id} was not found")

        profile = _ensure_document_profile(session=session, document=document)
        if profile.cover_path is None:
            raise FileNotFoundError(f"Cover for document {document_id} is unavailable")

        cover_path = Path(profile.cover_path)
        if not cover_path.exists():
            raise FileNotFoundError(f"Cover for document {document_id} is missing")
        return cover_path


def upsert_document_profile(
    *,
    session,
    document: "document_model.Document",
    author: str | None,
    summary: str | None,
    total_sections: int,
    total_chunks: int,
    cover_bytes: bytes | None,
    cover_extension: str | None,
    metadata_source: str | None = None,
    metadata_source_id: str | None = None,
    source_provider: str | None = None,
    source_provider_id: str | None = None,
    source_provider_name: str | None = None,
    source_provider_url: str | None = None,
    source_url: str | None = None,
    source_site_name: str | None = None,
    import_mode: str | None = None,
) -> "document_profile_model.DocumentProfile":
    profile = session.get(document_profile_model.DocumentProfile, document.id)
    if profile is None:
        profile = document_profile_model.DocumentProfile(document_id=document.id)
        session.add(profile)

    profile.author = author
    profile.summary = summary
    profile.total_sections = total_sections
    profile.total_chunks = total_chunks
    profile.estimated_duration_seconds = _estimate_duration_seconds(total_chunks)
    profile.metadata_source = metadata_source
    profile.metadata_source_id = metadata_source_id
    profile.source_provider = source_provider
    profile.source_provider_id = source_provider_id
    profile.source_provider_name = source_provider_name
    profile.source_provider_url = source_provider_url
    profile.source_url = source_url
    profile.source_site_name = source_site_name
    profile.import_mode = import_mode
    destination_root = (
        user_covers_root(document.owner_user_id)
        if getattr(document, "owner_user_id", None) is not None
        else None
    )
    profile.cover_path = str(
        write_cover_asset(
            document_id=document.id,
            title=document.title,
            author=author,
            file_format=document.format,
            cover_bytes=cover_bytes,
            cover_extension=cover_extension,
            destination_root=destination_root,
        )
    )
    session.flush()
    return profile


def upsert_document_progress(
    *, session, document_id: int, current_chunk_index: int
) -> "document_progress_model.DocumentProgress":
    progress = _get_or_create_document_progress(session=session, document_id=document_id)
    if not progress.bookmark_enabled:
        session.flush()
        return progress

    progress.current_chunk_index = current_chunk_index
    progress.has_bookmark = True
    progress.is_finished = False
    progress.finished_at = None
    progress.last_opened_at = datetime.now(timezone.utc)
    session.flush()
    return progress


def get_resume_chunk_index(*, session, document_id: int) -> int | None:
    progress_state = _build_progress_state(session=session, document_id=document_id)
    return progress_state.current_chunk_index


def reset_document_bookmark(
    *,
    document_id: int,
    owner_user_id: int | None = None,
) -> LibraryDocumentRecord:
    with db.session_scope() as session:
        document = _get_owned_document(session=session, document_id=document_id, owner_user_id=owner_user_id)
        if document is None:
            raise LookupError(f"Document {document_id} was not found")

        progress = _get_or_create_document_progress(session=session, document_id=document_id)
        progress.current_chunk_index = 0
        progress.has_bookmark = False
        session.flush()

        return _build_library_record(session=session, document=document)


def set_document_bookmark_enabled(
    *,
    document_id: int,
    enabled: bool,
    owner_user_id: int | None = None,
) -> LibraryDocumentRecord:
    with db.session_scope() as session:
        document = _get_owned_document(session=session, document_id=document_id, owner_user_id=owner_user_id)
        if document is None:
            raise LookupError(f"Document {document_id} was not found")

        progress = _get_or_create_document_progress(session=session, document_id=document_id)
        progress.bookmark_enabled = enabled
        if not enabled:
            progress.current_chunk_index = 0
            progress.has_bookmark = False
        session.flush()

        return _build_library_record(session=session, document=document)


def set_document_finished(
    *,
    document_id: int,
    is_finished: bool,
    owner_user_id: int | None = None,
) -> LibraryDocumentRecord:
    with db.session_scope() as session:
        document = _get_owned_document(session=session, document_id=document_id, owner_user_id=owner_user_id)
        if document is None:
            raise LookupError(f"Document {document_id} was not found")

        progress = _get_or_create_document_progress(session=session, document_id=document_id)
        progress.is_finished = is_finished
        progress.finished_at = datetime.now(timezone.utc) if is_finished else None
        if is_finished:
            progress.current_chunk_index = 0
            progress.has_bookmark = False
        session.flush()

        return _build_library_record(session=session, document=document)


def _build_library_record(
    *, session, document: "document_model.Document"
) -> LibraryDocumentRecord:
    profile = _ensure_document_profile(session=session, document=document)
    progress_state = _build_progress_state(session=session, document_id=document.id)

    return LibraryDocumentRecord(
        id=document.id,
        title=document.title,
        format=document.format,
        status=document.status,
        author=profile.author,
        cover_url=f"/api/documents/{document.id}/cover",
        summary=profile.summary,
        total_sections=profile.total_sections,
        total_chunks=profile.total_chunks,
        estimated_duration_seconds=profile.estimated_duration_seconds,
        current_chunk_index=progress_state.current_chunk_index,
        progress_percent=_calculate_progress_percent(
            current_chunk_index=progress_state.current_chunk_index,
            is_finished=progress_state.is_finished,
            total_chunks=profile.total_chunks,
        ),
        bookmark_enabled=progress_state.bookmark_enabled,
        is_finished=progress_state.is_finished,
        finished_at=progress_state.finished_at,
        last_opened_at=progress_state.last_opened_at,
        source_provider=profile.source_provider,
        source_provider_name=profile.source_provider_name,
        source_provider_url=profile.source_provider_url,
        source_url=profile.source_url,
        source_site_name=profile.source_site_name,
        import_mode=profile.import_mode,
    )


def _ensure_document_profile(
    *, session, document: "document_model.Document"
) -> "document_profile_model.DocumentProfile":
    profile = session.get(document_profile_model.DocumentProfile, document.id)
    if profile is not None:
        return profile

    sections = _load_sections(session=session, document_id=document.id)
    total_chunks = session.scalar(
        select(func.count(text_chunk_model.TextChunk.id))
        .join(
            section_model.Section,
            text_chunk_model.TextChunk.section_id == section_model.Section.id,
        )
        .where(section_model.Section.document_id == document.id)
    )
    summary = _summarize_sections(sections)
    return upsert_document_profile(
        session=session,
        document=document,
        author=None,
        summary=summary,
        total_sections=len(sections),
        total_chunks=int(total_chunks or 0),
        cover_bytes=None,
        cover_extension=None,
        metadata_source=None,
        metadata_source_id=None,
        source_provider=None,
        source_provider_id=None,
        source_provider_name=None,
        source_provider_url=None,
        source_url=None,
        source_site_name=None,
        import_mode=None,
    )


def _build_section_records(*, document_id: int, session) -> list[LibraryDocumentSectionRecord]:
    section_records: list[LibraryDocumentSectionRecord] = []
    chunk_start_index = 0

    for section in _load_sections(session=session, document_id=document_id):
        chunk_count = len(section.chunks)
        section_records.append(
            LibraryDocumentSectionRecord(
                id=section.id,
                position=section.position,
                title=section.title,
                chunk_start_index=chunk_start_index,
                chunk_count=chunk_count,
                preview_text=_build_preview_text(section.text),
            )
        )
        chunk_start_index += chunk_count

    return section_records


def _load_sections(*, session, document_id: int) -> list["section_model.Section"]:
    return list(
        session.scalars(
            select(section_model.Section)
            .where(section_model.Section.document_id == document_id)
            .order_by(section_model.Section.position)
        )
    )


def _summarize_sections(sections: list["section_model.Section"]) -> str | None:
    if not sections:
        return None

    first_text = sections[0].text.strip()
    if not first_text:
        return None

    return first_text[:240]


def _estimate_duration_seconds(total_chunks: int) -> int:
    return max(total_chunks * 6, 1) if total_chunks > 0 else 0


def _calculate_progress_percent(*, current_chunk_index: int | None, is_finished: bool, total_chunks: int) -> float:
    if is_finished:
        return 100

    if current_chunk_index is None or total_chunks <= 0:
        return 0

    return round((current_chunk_index / total_chunks) * 100, 2)


def _build_progress_state(*, session, document_id: int) -> DocumentProgressState:
    progress = session.get(document_progress_model.DocumentProgress, document_id)
    if progress is None:
        return DocumentProgressState(
            bookmark_enabled=True,
            current_chunk_index=None,
            finished_at=None,
            has_bookmark=False,
            is_finished=False,
            last_opened_at=None,
        )

    has_resumable_bookmark = progress.bookmark_enabled and progress.has_bookmark and not progress.is_finished

    return DocumentProgressState(
        bookmark_enabled=progress.bookmark_enabled,
        current_chunk_index=progress.current_chunk_index if has_resumable_bookmark else None,
        finished_at=progress.finished_at,
        has_bookmark=progress.has_bookmark,
        is_finished=progress.is_finished,
        last_opened_at=progress.last_opened_at if has_resumable_bookmark else None,
    )


def _get_or_create_document_progress(
    *, session, document_id: int
) -> "document_progress_model.DocumentProgress":
    progress = session.get(document_progress_model.DocumentProgress, document_id)
    if progress is None:
        progress = document_progress_model.DocumentProgress(document_id=document_id)
        session.add(progress)

    return progress


def _build_preview_text(text: str) -> str:
    stripped_text = text.strip()
    return stripped_text[:180] if stripped_text else ""


def _get_owned_document(*, session, document_id: int, owner_user_id: int | None) -> "document_model.Document | None":
    document = session.get(document_model.Document, document_id)
    if document is None:
        return None
    if owner_user_id is not None and document.owner_user_id != owner_user_id:
        return None
    return document
