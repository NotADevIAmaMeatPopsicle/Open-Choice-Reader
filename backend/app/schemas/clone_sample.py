from pydantic import BaseModel, Field


class CloneSampleCandidateRead(BaseModel):
    id: str
    provider: str
    title: str
    speaker: str | None = None
    audio_url: str
    transcript: str | None = None
    transcript_source_url: str
    source_url: str
    license_label: str
    provenance_note: str
    is_importable: bool


class CloneSampleSearchRead(BaseModel):
    query: str
    items: list[CloneSampleCandidateRead]


class CloneSampleImportRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    speaker: str | None = Field(default=None, max_length=300)
    audio_url: str = Field(min_length=1, max_length=4096)
    transcript: str = Field(min_length=1, max_length=100_000)
    transcript_source_url: str = Field(min_length=1, max_length=4096)
    source_url: str = Field(min_length=1, max_length=4096)
    license_label: str = Field(min_length=1, max_length=300)
    provenance_note: str = Field(min_length=1, max_length=2000)
