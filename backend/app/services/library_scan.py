from pathlib import Path

from sqlalchemy import select

from app import db
from app.config import settings
import app.models.document as document_model
from app.schemas.document import InboxCandidate
from app.services.user_storage import user_inbox_root


def list_inbox_candidates(*, owner_user_id: int | None = None) -> list[InboxCandidate]:
    inbox_root = user_inbox_root(owner_user_id) if owner_user_id is not None else Path(settings.inbox_root)
    if not inbox_root.exists():
        return []

    with db.session_scope() as session:
        origin_map = {
            Path(document.origin_path).resolve(): document.id
            for document in session.scalars(
                select(document_model.Document).where(
                    document_model.Document.owner_user_id == owner_user_id
                )
                if owner_user_id is not None
                else select(document_model.Document)
            )
            if document.origin_path
        }

    candidates = []
    for path in sorted(inbox_root.rglob("*")):
        if not path.is_file():
            continue

        resolved_path = path.resolve()
        candidates.append(
            InboxCandidate(
                name=path.name,
                path=str(path.relative_to(inbox_root)),
                format=path.suffix.lstrip(".").lower(),
                document_id=origin_map.get(resolved_path),
            )
        )

    return candidates


def resolve_inbox_candidate_path(relative_path: str, *, owner_user_id: int | None = None) -> Path:
    inbox_root = (
        user_inbox_root(owner_user_id) if owner_user_id is not None else Path(settings.inbox_root)
    ).resolve()
    candidate_path = (inbox_root / relative_path).resolve()
    if inbox_root not in candidate_path.parents and candidate_path != inbox_root:
        raise LookupError(f"Inbox file '{relative_path}' was not found")
    if not candidate_path.is_file():
        raise LookupError(f"Inbox file '{relative_path}' was not found")
    return candidate_path
