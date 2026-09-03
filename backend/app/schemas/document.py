from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    title: str | None
    chunk_start_index: int
    chunk_count: int
    preview_text: str


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    bookmark_enabled: bool = True
    is_finished: bool = False
    finished_at: datetime | None = None
    last_opened_at: datetime | None
    source_provider: str | None = None
    source_provider_name: str | None = None
    source_provider_url: str | None = None
    source_url: str | None = None
    source_site_name: str | None = None
    import_mode: str | None = None


class DocumentDetailRead(DocumentRead):
    sections: list[DocumentSectionRead]


class DocumentSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    continue_reading: list[DocumentRead]
    recent_documents: list[DocumentRead]


class InboxCandidate(BaseModel):
    name: str
    path: str
    format: str
    document_id: int | None = None


class InboxImportRequest(BaseModel):
    path: str


class BookmarkPreferenceUpdate(BaseModel):
    enabled: bool
