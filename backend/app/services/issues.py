from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from app import db
import app.models.document as document_model
import app.models.job as job_model
from app.tts.registry import list_engine_statuses


@dataclass(slots=True)
class IssueRecord:
    id: str
    issue_type: str
    severity: str
    title: str
    detail: str
    action_label: str
    action_path: str
    document_id: int | None = None


@dataclass(slots=True)
class IssueSummaryRecord:
    total_count: int
    counts_by_severity: dict[str, int]
    items: list[IssueRecord]


def get_issue_summary(*, user_id: int | None = None) -> IssueSummaryRecord:
    issues: list[IssueRecord] = []

    with db.session_scope() as session:
        documents_statement = select(document_model.Document).order_by(document_model.Document.id.desc())
        if user_id is not None:
            documents_statement = documents_statement.where(document_model.Document.owner_user_id == user_id)
        documents = list(
            session.scalars(documents_statement)
        )
        for document in documents:
            source_path = Path(document.origin_path or document.source_path)
            if source_path.exists():
                continue
            issues.append(
                IssueRecord(
                    id=f"missing-source-{document.id}",
                    issue_type="missing_source",
                    severity="error",
                    title=f"Source file missing for {document.title}",
                    detail="Re-import or refresh this title from the library.",
                    action_label="Open library",
                    action_path="/",
                    document_id=document.id,
                )
            )

        failed_jobs_statement = (
            select(job_model.Job)
            .where(job_model.Job.status == "failed")
            .order_by(job_model.Job.id.desc())
        )
        if user_id is not None:
            failed_jobs_statement = failed_jobs_statement.where(job_model.Job.user_id == user_id)
        failed_jobs = list(session.scalars(failed_jobs_statement))
        for job in failed_jobs:
            document = session.get(document_model.Document, job.document_id)
            title = document.title if document is not None else f"Document {job.document_id}"
            issues.append(
                IssueRecord(
                    id=f"job-failure-{job.id}",
                    issue_type="export_failure",
                    severity="error",
                    title=f"Export failed for {title}",
                    detail=job.failure_detail or "Export worker failed without a reason.",
                    action_label="Open jobs",
                    action_path="/jobs",
                    document_id=job.document_id,
                )
            )

    for engine_status in list_engine_statuses():
        if engine_status.availability == "available":
            continue
        issues.append(
            IssueRecord(
                id=f"engine-warning-{engine_status.engine}",
                issue_type="engine_warning",
                severity="warning",
                title=f"{engine_status.display_name} is degraded",
                detail=engine_status.availability_detail,
                action_label="Open settings",
                action_path="/settings",
            )
        )

    counts_by_severity: dict[str, int] = {}
    for issue in issues:
        counts_by_severity[issue.severity] = counts_by_severity.get(issue.severity, 0) + 1

    return IssueSummaryRecord(
        total_count=len(issues),
        counts_by_severity=counts_by_severity,
        items=issues,
    )
