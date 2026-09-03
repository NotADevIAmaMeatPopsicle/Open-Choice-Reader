import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select

from app.config import settings
from app import db
import app.models.collection as collection_model
import app.models.document as document_model
import app.models.document_profile as document_profile_model
import app.models.document_progress as document_progress_model
import app.models.job as job_model
import app.models.playback_session as playback_session_model
import app.models.section as section_model
import app.models.text_chunk as text_chunk_model
from app.parsers.base import ParsedDocument
from app.parsers.epub import parse_epub_document
from app.parsers.html import parse_html_document
from app.parsers.pdf import parse_pdf_document
from app.parsers.plain_text import parse_plain_text_document
from app.services.book_metadata import ExternalMetadata
from app.services.book_metadata import enrich_parsed_document
from app.services.chunking import chunk_paragraphs
from app.services.library_view import upsert_document_profile
from app.services.library_scan import resolve_inbox_candidate_path
from app.services.uploads import read_upload_bytes
from app.services.user_storage import user_source_root


PLAIN_TEXT_FORMATS = {"txt", "md", "markdown"}
RICH_TEXT_PARSERS = {
    "epub": parse_epub_document,
    "html": parse_html_document,
    "pdf": parse_pdf_document,
}
SUPPORTED_IMPORT_FORMATS = PLAIN_TEXT_FORMATS | set(RICH_TEXT_PARSERS)
ACTIVE_EXPORT_JOB_STATUSES = {"queued", "processing", "cancel_requested"}


@dataclass(slots=True)
class ExternalSourceProvenance:
    provider: str | None = None
    provider_id: str | None = None
    provider_name: str | None = None
    provider_url: str | None = None
    source_url: str | None = None
    source_site_name: str | None = None
    import_mode: str | None = None


def init_database() -> None:
    db.init_database()
    from app.services.themes import ensure_builtin_themes_seeded

    ensure_builtin_themes_seeded()


def _build_storage_path(filename: Path, *, owner_user_id: int | None = None) -> Path:
    source_root = user_source_root(owner_user_id) if owner_user_id is not None else Path(settings.source_root)
    source_root.mkdir(parents=True, exist_ok=True)

    stem = filename.stem or "upload"
    suffix = filename.suffix

    candidate = source_root / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate

    return source_root / f"{stem}-{uuid4().hex}{suffix}"


def import_document(file: UploadFile, *, owner_user_id: int | None = None) -> "document_model.Document":
    filename = Path(file.filename or "upload")
    return _import_document_from_bytes(
        filename=filename,
        file_bytes=read_upload_bytes(file, max_bytes=settings.document_upload_max_bytes),
        owner_user_id=owner_user_id,
    )


def import_inbox_candidate(relative_path: str, *, owner_user_id: int | None = None) -> "document_model.Document":
    inbox_path = resolve_inbox_candidate_path(relative_path, owner_user_id=owner_user_id)
    return import_local_path(inbox_path, owner_user_id=owner_user_id)


def import_local_path(
    path: Path, *, metadata_hint: ExternalMetadata | None = None, owner_user_id: int | None = None
) -> "document_model.Document":
    return _import_document_from_bytes(
        filename=Path(path.name),
        file_bytes=path.read_bytes(),
        origin_path=path,
        metadata_hint=metadata_hint,
        owner_user_id=owner_user_id,
    )


def import_external_document(
    *,
    filename: str,
    file_bytes: bytes,
    metadata_hint: ExternalMetadata | None,
    source_provenance: ExternalSourceProvenance,
    owner_user_id: int | None = None,
) -> "document_model.Document":
    return _import_document_from_bytes(
        filename=Path(filename),
        file_bytes=file_bytes,
        metadata_hint=metadata_hint,
        source_provenance=source_provenance,
        owner_user_id=owner_user_id,
    )


def reimport_document(document_id: int, *, owner_user_id: int | None = None) -> "document_model.Document":
    with db.session_scope() as session:
        document = session.get(document_model.Document, document_id)
        if document is None or (owner_user_id is not None and document.owner_user_id != owner_user_id):
            raise LookupError(f"Document {document_id} was not found")
        profile = session.get(document_profile_model.DocumentProfile, document.id)

        source_path = _resolve_reimport_source_path(document)
        file_format = _validate_import_format(source_path)
        file_bytes = source_path.read_bytes()
        parsed_document = _parse_document_content(file_bytes=file_bytes, file_format=file_format)
        metadata_resolution = enrich_parsed_document(
            parsed_document,
            filename=source_path,
            origin_path=source_path,
        )
        parsed_document = metadata_resolution.parsed_document

        _sync_document_source_copy(document=document, file_bytes=file_bytes)

        document.title = parsed_document.title or source_path.stem
        document.format = file_format
        document.status = "uploaded"
        document.origin_path = str(source_path)

        _replace_document_content(
            session=session,
            document=document,
            parsed_document=parsed_document,
            metadata_source=metadata_resolution.metadata_source,
            metadata_source_id=metadata_resolution.metadata_source_id,
            source_provenance=(
                ExternalSourceProvenance(
                    provider=profile.source_provider,
                    provider_id=profile.source_provider_id,
                    provider_name=profile.source_provider_name,
                    provider_url=profile.source_provider_url,
                    source_url=profile.source_url,
                    source_site_name=profile.source_site_name,
                    import_mode=profile.import_mode,
                )
                if profile is not None
                and (
                    profile.source_provider is not None
                    or profile.source_url is not None
                    or profile.import_mode is not None
                )
                else None
            ),
        )
        session.refresh(document)
        return document


def list_documents(*, owner_user_id: int | None = None) -> list["document_model.Document"]:
    with db.session_scope() as session:
        statement = select(document_model.Document).order_by(document_model.Document.id)
        if owner_user_id is not None:
            statement = statement.where(document_model.Document.owner_user_id == owner_user_id)
        return list(session.scalars(statement))


def delete_document(document_id: int, *, owner_user_id: int | None = None) -> None:
    file_paths: list[Path] = []
    directory_paths: list[Path] = []

    with db.session_scope() as session:
        document = session.get(document_model.Document, document_id)
        if document is None or (owner_user_id is not None and document.owner_user_id != owner_user_id):
            raise LookupError(f"Document {document_id} was not found")

        jobs = list(
            session.scalars(
                select(job_model.Job).where(job_model.Job.document_id == document.id)
            )
        )
        if any(job.status in ACTIVE_EXPORT_JOB_STATUSES for job in jobs):
            raise ValueError(
                f"Document {document_id} cannot be deleted while an export is still running; "
                "cancel the export or wait for it to finish"
            )

        profile = session.get(document_profile_model.DocumentProfile, document.id)
        progress = session.get(document_progress_model.DocumentProgress, document.id)
        playback_sessions = list(
            session.scalars(
                select(playback_session_model.PlaybackSession).where(
                    playback_session_model.PlaybackSession.document_id == document.id
                )
            )
        )
        sections = list(
            session.scalars(
                select(section_model.Section).where(section_model.Section.document_id == document.id)
            )
        )
        collection_memberships = list(
            session.scalars(
                select(collection_model.CollectionDocument).where(
                    collection_model.CollectionDocument.document_id == document.id
                )
            )
        )

        if document.source_path:
            file_paths.append(Path(document.source_path))
        if profile is not None and profile.cover_path:
            file_paths.append(Path(profile.cover_path))
        for job in jobs:
            file_paths.extend(_collect_job_artifact_paths(job))
        directory_paths.extend(
            _collect_document_audio_cache_directories(
                document_id=document.id,
                playback_sessions=playback_sessions,
            )
        )

        for section in sections:
            session.delete(section)
        if profile is not None:
            session.delete(profile)
        if progress is not None:
            session.delete(progress)
        for playback_session in playback_sessions:
            session.delete(playback_session)
        for collection_membership in collection_memberships:
            session.delete(collection_membership)
        for job in jobs:
            session.delete(job)
        session.delete(document)

    _remove_document_files(file_paths=file_paths, directory_paths=directory_paths)


def _collect_job_artifact_paths(job: "job_model.Job") -> list[Path]:
    artifact_paths: list[Path] = []
    if job.artifact_path:
        artifact_paths.append(Path(job.artifact_path))

    if not job.artifact_manifest:
        return artifact_paths

    try:
        manifest_entries = json.loads(job.artifact_manifest)
    except json.JSONDecodeError:
        return artifact_paths
    if not isinstance(manifest_entries, list):
        return artifact_paths

    for entry in manifest_entries:
        if not isinstance(entry, dict):
            continue
        entry_path = str(entry.get("path") or "").strip()
        if entry_path:
            artifact_paths.append(Path(entry_path))

    return artifact_paths


def _collect_document_audio_cache_directories(
    *,
    document_id: int,
    playback_sessions: list["playback_session_model.PlaybackSession"],
) -> list[Path]:
    document_directory_name = str(document_id)
    directories = [
        candidate
        for candidate in (Path(settings.cache_root) / "audio").glob(f"*/*/{document_directory_name}")
        if candidate.is_dir()
    ]

    for playback_session in playback_sessions:
        if not playback_session.audio_path:
            continue
        session_audio_directory = Path(playback_session.audio_path).parent
        if session_audio_directory.name == document_directory_name:
            directories.append(session_audio_directory)

    return directories


def _remove_document_files(*, file_paths: list[Path], directory_paths: list[Path]) -> None:
    allowed_roots = (Path(settings.storage_root).resolve(), Path(settings.cache_root).resolve())

    def _is_inside_allowed_roots(path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        return any(resolved.is_relative_to(allowed_root) for allowed_root in allowed_roots)

    for file_path in file_paths:
        if not _is_inside_allowed_roots(file_path):
            continue
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            continue

    for directory_path in directory_paths:
        if not _is_inside_allowed_roots(directory_path):
            continue
        shutil.rmtree(directory_path, ignore_errors=True)


def _store_document_content(
    *, session, document: "document_model.Document", parsed_document: ParsedDocument
) -> tuple[int, int]:
    sections = parsed_document.sections
    if not sections:
        return 0, 0

    total_chunks = 0
    for section_position, parsed_section in enumerate(sections):
        section = section_model.Section(
            document_id=document.id,
            position=section_position,
            title=parsed_section.title,
            text=parsed_section.text,
        )
        session.add(section)
        session.flush()

        for chunk_position, chunk_text in enumerate(chunk_paragraphs(parsed_section.text)):
            session.add(
                text_chunk_model.TextChunk(
                    section_id=section.id,
                    position=chunk_position,
                    text=chunk_text,
                )
            )
            total_chunks += 1

    return len(sections), total_chunks


def _parse_document_content(*, file_bytes: bytes, file_format: str) -> ParsedDocument:
    if file_format in PLAIN_TEXT_FORMATS:
        content = file_bytes.decode("utf-8-sig", errors="replace")
        return parse_plain_text_document(content, file_format)

    parser = RICH_TEXT_PARSERS.get(file_format)
    if parser is None:
        return ParsedDocument(sections=[])

    return parser(file_bytes)


def _build_document_summary(parsed_document: ParsedDocument) -> str | None:
    for section in parsed_document.sections:
        text = section.text.strip()
        if text:
            return text[:240]
    return None


def _validate_import_format(filename: Path) -> str:
    file_format = filename.suffix.lstrip(".").lower()
    if file_format not in SUPPORTED_IMPORT_FORMATS:
        raise ValueError(f"Unsupported import format '{file_format}'")
    return file_format


def _import_document_from_bytes(
    *,
    filename: Path,
    file_bytes: bytes,
    origin_path: Path | None = None,
    metadata_hint: ExternalMetadata | None = None,
    source_provenance: ExternalSourceProvenance | None = None,
    owner_user_id: int | None = None,
) -> "document_model.Document":
    file_format = _validate_import_format(filename)
    destination = _build_storage_path(filename, owner_user_id=owner_user_id)

    while True:
        try:
            with destination.open("xb") as output:
                output.write(file_bytes)
            break
        except FileExistsError:
            destination = _build_storage_path(filename)

    try:
        parsed_document = _parse_document_content(file_bytes=file_bytes, file_format=file_format)
        metadata_resolution = enrich_parsed_document(
            parsed_document,
            filename=filename,
            origin_path=origin_path or destination,
            metadata_hint=metadata_hint,
        )
        parsed_document = metadata_resolution.parsed_document
        document = document_model.Document(
            owner_user_id=owner_user_id,
            title=parsed_document.title or filename.stem,
            format=file_format,
            status="uploaded",
            source_path=str(destination),
            origin_path=str(origin_path or destination),
        )

        with db.session_scope() as session:
            session.add(document)
            session.flush()
            total_sections, total_chunks = _store_document_content(
                session=session,
                document=document,
                parsed_document=parsed_document,
            )
            upsert_document_profile(
                session=session,
                document=document,
                author=parsed_document.author,
                summary=parsed_document.description or _build_document_summary(parsed_document),
                total_sections=total_sections,
                total_chunks=total_chunks,
                cover_bytes=parsed_document.cover_bytes,
                cover_extension=parsed_document.cover_extension,
                metadata_source=metadata_resolution.metadata_source,
                metadata_source_id=metadata_resolution.metadata_source_id,
                source_provider=source_provenance.provider if source_provenance is not None else None,
                source_provider_id=source_provenance.provider_id if source_provenance is not None else None,
                source_provider_name=source_provenance.provider_name if source_provenance is not None else None,
                source_provider_url=source_provenance.provider_url if source_provenance is not None else None,
                source_url=source_provenance.source_url if source_provenance is not None else None,
                source_site_name=source_provenance.source_site_name if source_provenance is not None else None,
                import_mode=source_provenance.import_mode if source_provenance is not None else None,
            )
            session.refresh(document)

        return document
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def _replace_document_content(
    *,
    session,
    document: "document_model.Document",
    parsed_document: ParsedDocument,
    metadata_source: str | None,
    metadata_source_id: str | None,
    source_provenance: ExternalSourceProvenance | None,
) -> None:
    sections = list(
        session.scalars(
            select(section_model.Section).where(section_model.Section.document_id == document.id)
        )
    )
    for section in sections:
        session.delete(section)

    progress = session.get(document_progress_model.DocumentProgress, document.id)
    if progress is not None:
        session.delete(progress)

    playback_sessions = list(
        session.scalars(
            select(playback_session_model.PlaybackSession).where(
                playback_session_model.PlaybackSession.document_id == document.id
            )
        )
    )
    for playback_session in playback_sessions:
        session.delete(playback_session)

    session.flush()
    total_sections, total_chunks = _store_document_content(
        session=session,
        document=document,
        parsed_document=parsed_document,
    )
    upsert_document_profile(
        session=session,
        document=document,
        author=parsed_document.author,
        summary=parsed_document.description or _build_document_summary(parsed_document),
        total_sections=total_sections,
        total_chunks=total_chunks,
        cover_bytes=parsed_document.cover_bytes,
        cover_extension=parsed_document.cover_extension,
        metadata_source=metadata_source,
        metadata_source_id=metadata_source_id,
        source_provider=source_provenance.provider if source_provenance is not None else None,
        source_provider_id=source_provenance.provider_id if source_provenance is not None else None,
        source_provider_name=source_provenance.provider_name if source_provenance is not None else None,
        source_provider_url=source_provenance.provider_url if source_provenance is not None else None,
        source_url=source_provenance.source_url if source_provenance is not None else None,
        source_site_name=source_provenance.source_site_name if source_provenance is not None else None,
        import_mode=source_provenance.import_mode if source_provenance is not None else None,
    )


def _resolve_reimport_source_path(document: "document_model.Document") -> Path:
    for candidate in (document.origin_path, document.source_path):
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.is_file():
            return candidate_path

    raise FileNotFoundError(f"Document {document.id} is missing its source file")


def _sync_document_source_copy(*, document: "document_model.Document", file_bytes: bytes) -> None:
    source_copy_path = Path(document.source_path)
    source_copy_path.parent.mkdir(parents=True, exist_ok=True)
    source_copy_path.write_bytes(file_bytes)
