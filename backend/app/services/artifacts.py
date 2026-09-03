import json
from dataclasses import dataclass
from pathlib import Path

from app.models.job import Job


@dataclass(slots=True)
class JobArtifactRecord:
    artifact_id: str
    filename: str
    label: str
    section_title: str | None
    path: str
    download_url: str


def list_job_artifacts(job: Job) -> list[JobArtifactRecord]:
    if job.artifact_manifest:
        return _deserialize_manifest(job)
    if job.status == "completed" and job.artifact_path:
        artifact_path = Path(job.artifact_path)
        return [
            JobArtifactRecord(
                artifact_id="0",
                filename=artifact_path.name,
                label="Merged audiobook",
                section_title=None,
                path=str(artifact_path),
                download_url=f"/api/jobs/{job.id}/download",
            )
        ]
    return []


def resolve_job_artifact_path(*, job: Job, artifact_index: int) -> Path:
    artifacts = list_job_artifacts(job)
    if artifact_index < 0 or artifact_index >= len(artifacts):
        raise LookupError(f"Artifact {artifact_index} was not found for job {job.id}")
    return Path(artifacts[artifact_index].path)


def serialize_job_artifacts(job: Job) -> list[dict[str, str | None]]:
    return [
        {
            "artifact_id": artifact.artifact_id,
            "filename": artifact.filename,
            "label": artifact.label,
            "section_title": artifact.section_title,
            "download_url": artifact.download_url,
        }
        for artifact in list_job_artifacts(job)
    ]


def build_manifest_entry(
    *,
    filename: str,
    label: str,
    section_title: str | None,
    path: str,
) -> dict[str, str | None]:
    return {
        "filename": filename,
        "label": label,
        "section_title": section_title,
        "path": path,
    }


def serialize_manifest_entries(entries: list[dict[str, str | None]]) -> str:
    return json.dumps(entries, ensure_ascii=True)


def _deserialize_manifest(job: Job) -> list[JobArtifactRecord]:
    try:
        manifest = json.loads(job.artifact_manifest or "[]")
    except json.JSONDecodeError:
        return []

    artifacts: list[JobArtifactRecord] = []
    for artifact_index, item in enumerate(manifest):
        if not isinstance(item, dict):
            continue

        path = str(item.get("path") or "").strip()
        filename = str(item.get("filename") or "").strip()
        if not path or not filename:
            continue

        artifacts.append(
            JobArtifactRecord(
                artifact_id=str(artifact_index),
                filename=filename,
                label=str(item.get("label") or filename),
                section_title=(str(item["section_title"]) if item.get("section_title") else None),
                path=path,
                download_url=f"/api/jobs/{job.id}/artifacts/{artifact_index}/download",
            )
        )

    return artifacts
