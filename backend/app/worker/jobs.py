import os
import shutil
import wave
import math
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app import db
from app.config import settings
from app.models.job import Job
from app.models.section import Section
from app.models.text_chunk import TextChunk
from app.services.audio_cache import build_chunk_audio_cache_path, populate_cached_audio
from app.services.artifacts import build_manifest_entry, serialize_manifest_entries
from app.services.jobs import utcnow, validate_export_request
from app.tts.qwen_clone_engine import Qwen3CloneEngine
from app.tts.registry import build_clone_engine_for_profile, get_tts_engine


class ExportCanceled(RuntimeError):
    pass


@dataclass(slots=True)
class ExportChunk:
    id: int
    text: str


@dataclass(slots=True)
class ExportSection:
    id: int
    position: int
    title: str | None
    chunks: list[ExportChunk]


def process_export_job(job: Job) -> None:
    with db.session_scope() as session:
        persisted_job = session.get(Job, job.id)
        if persisted_job is None:
            return

        try:
            export_result = _export_document_audio(persisted_job)
        except ExportCanceled:
            persisted_job.status = "canceled"
            persisted_job.artifact_path = None
            persisted_job.artifact_manifest = None
            persisted_job.failure_detail = None
            persisted_job.status_detail = "Export canceled"
            return
        except Exception as error:
            persisted_job.status = "failed"
            persisted_job.artifact_path = None
            persisted_job.artifact_manifest = None
            persisted_job.failure_detail = _build_failure_detail(error)
            persisted_job.status_detail = persisted_job.failure_detail
            return

        if export_result["artifact_path"] is not None and not export_result["artifact_path"].exists():
            persisted_job.status = "failed"
            persisted_job.artifact_path = None
            persisted_job.artifact_manifest = None
            persisted_job.failure_detail = "Export artifact was not created"
            persisted_job.status_detail = persisted_job.failure_detail
            return

        persisted_job.status = "completed"
        persisted_job.artifact_path = (
            str(export_result["artifact_path"]) if export_result["artifact_path"] is not None else None
        )
        persisted_job.artifact_manifest = export_result["artifact_manifest"]
        persisted_job.progress_percent = 100
        persisted_job.failure_detail = None
        persisted_job.status_detail = "Export ready"


def _export_document_audio(job: Job) -> dict[str, Path | str | None]:
    voice_preset = _validate_export_request(job)
    sections = _load_export_sections(job.document_id)

    if not sections:
        raise ValueError(f"Document {job.document_id} has no text chunks")

    temporary_chunk_dir: Path | None = None
    try:
        if job.split_chapters:
            artifact_manifest, temporary_chunk_dir = _export_split_sections(
                job=job,
                sections=sections,
                voice_preset=voice_preset,
            )
            return {"artifact_path": None, "artifact_manifest": artifact_manifest}

        if voice_preset is None:
            chunk_audio_paths = _synthesize_default_chunk_audio(
                job=job,
                sections=sections,
            )
        else:
            chunk_audio_paths, temporary_chunk_dir = _synthesize_clone_chunk_audio(
                job=job,
                sections=sections,
                voice_preset=voice_preset,
            )

        export_path = _build_export_path(job)
        _write_combined_wav(chunk_audio_paths=chunk_audio_paths, output_path=export_path)
        return {"artifact_path": export_path, "artifact_manifest": None}
    finally:
        if temporary_chunk_dir is not None:
            shutil.rmtree(temporary_chunk_dir, ignore_errors=True)


def _validate_export_request(job: Job):
    return validate_export_request(voice_preset_id=job.voice_preset_id, format=job.format)


def _synthesize_default_chunk_audio(*, job: Job, sections: list[ExportSection]) -> list[Path]:
    engine = get_tts_engine()
    chunk_audio_paths: list[Path] = []
    processed_chunks = 0
    total_chunks = _count_total_chunks(sections)

    for section in sections:
        for chunk in section.chunks:
            _raise_if_cancel_requested(job.id)
            audio_path = build_chunk_audio_cache_path(
                engine_name=engine.name,
                document_id=job.document_id,
                chunk_id=chunk.id,
                text=chunk.text,
            )
            populate_cached_audio(engine=engine, text=chunk.text, output_path=audio_path)
            chunk_audio_paths.append(audio_path)
            processed_chunks += 1
            _update_job_progress(
                job_id=job.id,
                processed_chunks=processed_chunks,
                total_chunks=total_chunks,
                status_detail=f"Rendering chunk {processed_chunks} of {total_chunks}",
            )

    return chunk_audio_paths


def _synthesize_clone_chunk_audio(
    *,
    job: Job,
    sections: list[ExportSection],
    voice_preset,
) -> tuple[list[Path], Path]:
    engine = _build_clone_engine(job=job, voice_preset=voice_preset)
    reference_audio_path = Path(voice_preset.reference_path)
    chunk_audio_root = Path(settings.cache_root) / "audio" / engine.name / "jobs" / f"job-{job.id}"
    chunk_audio_root.mkdir(parents=True, exist_ok=True)

    chunk_audio_paths: list[Path] = []
    processed_chunks = 0
    total_chunks = _count_total_chunks(sections)
    for section in sections:
        for chunk in section.chunks:
            _raise_if_cancel_requested(job.id)
            audio_path = chunk_audio_root / f"chunk-{chunk.id}.wav"
            engine.clone_to_file(
                text=chunk.text,
                output_path=audio_path,
                reference_audio_path=reference_audio_path,
                transcript=voice_preset.transcript,
            )
            chunk_audio_paths.append(audio_path)
            processed_chunks += 1
            _update_job_progress(
                job_id=job.id,
                processed_chunks=processed_chunks,
                total_chunks=total_chunks,
                status_detail=f"Rendering chunk {processed_chunks} of {total_chunks}",
            )

    return chunk_audio_paths, chunk_audio_root


def _export_split_sections(*, job: Job, sections: list[ExportSection], voice_preset) -> tuple[str, Path | None]:
    temporary_chunk_dir: Path | None = None
    export_root = Path(settings.export_root)
    export_root.mkdir(parents=True, exist_ok=True)
    total_chunks = _count_total_chunks(sections)
    processed_chunks = 0
    manifest_entries: list[dict[str, str | None]] = []
    clone_engine = _build_clone_engine(job=job, voice_preset=voice_preset) if voice_preset is not None else None
    reference_audio_path = Path(voice_preset.reference_path) if voice_preset is not None else None
    chunk_audio_root: Path | None = None

    if clone_engine is not None:
        chunk_audio_root = (
            Path(settings.cache_root) / "audio" / clone_engine.name / "jobs" / f"job-{job.id}-split"
        )
        chunk_audio_root.mkdir(parents=True, exist_ok=True)
        temporary_chunk_dir = chunk_audio_root

    default_engine = get_tts_engine() if clone_engine is None else None

    for section_index, section in enumerate(sections, start=1):
        _raise_if_cancel_requested(job.id)
        section_chunk_paths: list[Path] = []
        section_slug = _slugify(section.title or f"section-{section_index}")
        output_path = export_root / f"{job.artifact_basename}-{section_index:02d}-{section_slug}.{job.format}"

        for chunk in section.chunks:
            _raise_if_cancel_requested(job.id)
            if clone_engine is None:
                assert default_engine is not None
                audio_path = build_chunk_audio_cache_path(
                    engine_name=default_engine.name,
                    document_id=job.document_id,
                    chunk_id=chunk.id,
                    text=chunk.text,
                )
                populate_cached_audio(engine=default_engine, text=chunk.text, output_path=audio_path)
            else:
                assert reference_audio_path is not None
                assert chunk_audio_root is not None
                audio_path = chunk_audio_root / f"section-{section.id}-chunk-{chunk.id}.wav"
                clone_engine.clone_to_file(
                    text=chunk.text,
                    output_path=audio_path,
                    reference_audio_path=reference_audio_path,
                    transcript=voice_preset.transcript,
                )

            section_chunk_paths.append(audio_path)
            processed_chunks += 1
            _update_job_progress(
                job_id=job.id,
                processed_chunks=processed_chunks,
                total_chunks=total_chunks,
                status_detail=f"Rendering chunk {processed_chunks} of {total_chunks}",
            )

        _write_combined_wav(chunk_audio_paths=section_chunk_paths, output_path=output_path)
        manifest_entries.append(
            build_manifest_entry(
                filename=output_path.name,
                label=f"Chapter {section_index}",
                section_title=section.title,
                path=str(output_path),
            )
        )

    return serialize_manifest_entries(manifest_entries), temporary_chunk_dir


def _build_clone_engine(*, job: Job, voice_preset):
    if voice_preset.engine != Qwen3CloneEngine.name:
        raise ValueError(f"Unsupported voice preset engine '{voice_preset.engine}'")
    return build_clone_engine_for_profile(job.clone_engine_id)


def _build_export_path(job: Job) -> Path:
    export_root = Path(settings.export_root)
    export_root.mkdir(parents=True, exist_ok=True)
    return export_root / f"job-{job.id}.{job.format}"


def _write_combined_wav(*, chunk_audio_paths: list[Path], output_path: Path) -> None:
    temp_path = output_path.with_name(f"{output_path.name}.{uuid4().hex}.tmp")

    try:
        with wave.open(str(chunk_audio_paths[0]), "rb") as first_chunk:
            params = (
                first_chunk.getnchannels(),
                first_chunk.getsampwidth(),
                first_chunk.getframerate(),
                first_chunk.getcomptype(),
                first_chunk.getcompname(),
            )

        with wave.open(str(temp_path), "wb") as combined:
            combined.setnchannels(params[0])
            combined.setsampwidth(params[1])
            combined.setframerate(params[2])
            combined.setcomptype(params[3], params[4])

            for chunk_audio_path in chunk_audio_paths:
                with wave.open(str(chunk_audio_path), "rb") as chunk_audio:
                    chunk_params = (
                        chunk_audio.getnchannels(),
                        chunk_audio.getsampwidth(),
                        chunk_audio.getframerate(),
                        chunk_audio.getcomptype(),
                    )
                    if chunk_params != params[:4]:
                        raise ValueError("Chunk audio parameters do not match")

                    combined.writeframes(chunk_audio.readframes(chunk_audio.getnframes()))

        os.replace(temp_path, output_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _build_failure_detail(error: Exception) -> str:
    detail = str(error).strip()
    if detail:
        return detail
    return error.__class__.__name__


def _load_export_sections(document_id: int) -> list[ExportSection]:
    with db.session_scope() as session:
        sections = list(
            session.scalars(
                select(Section).where(Section.document_id == document_id).order_by(Section.position)
            )
        )
        export_sections: list[ExportSection] = []
        for section in sections:
            chunks = list(
                session.scalars(
                    select(TextChunk)
                    .where(TextChunk.section_id == section.id)
                    .order_by(TextChunk.position)
                )
            )
            if not chunks:
                continue
            export_sections.append(
                ExportSection(
                    id=section.id,
                    position=section.position,
                    title=section.title,
                    chunks=[ExportChunk(id=chunk.id, text=chunk.text) for chunk in chunks],
                )
            )
        return export_sections


def _count_total_chunks(sections: list[ExportSection]) -> int:
    return sum(len(section.chunks) for section in sections)


def _update_job_progress(*, job_id: int, processed_chunks: int, total_chunks: int, status_detail: str) -> None:
    progress_percent = 100 if total_chunks <= 0 else min(
        100,
        max(0, math.floor((processed_chunks / total_chunks) * 100)),
    )
    with db.session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            return
        if job.status == "cancel_requested":
            raise ExportCanceled()
        job.progress_percent = progress_percent
        job.status_detail = status_detail
        job.heartbeat_at = utcnow()


def _raise_if_cancel_requested(job_id: int) -> None:
    with db.session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise ExportCanceled()
        if job.status == "cancel_requested":
            raise ExportCanceled()
        job.heartbeat_at = utcnow()


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return normalized or "section"
