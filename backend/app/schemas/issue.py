from pydantic import BaseModel, ConfigDict


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    issue_type: str
    severity: str
    title: str
    detail: str
    action_label: str
    action_path: str
    document_id: int | None = None


class IssueSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_count: int
    counts_by_severity: dict[str, int]
    items: list[IssueRead]
