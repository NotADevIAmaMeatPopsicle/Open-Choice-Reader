from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.issue import IssueSummaryRead
from app.services.issues import get_issue_summary


router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.get("", response_model=IssueSummaryRead)
def get_issues_route(current_user: CurrentUser = Depends(get_current_user)) -> IssueSummaryRead:
    summary = get_issue_summary(user_id=current_user.id)
    return IssueSummaryRead.model_validate(
        {
            "total_count": summary.total_count,
            "counts_by_severity": summary.counts_by_severity,
            "items": summary.items,
        }
    )
