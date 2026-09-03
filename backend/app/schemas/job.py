from pydantic import BaseModel, ConfigDict


class JobExportCreate(BaseModel):
    document_id: int
    voice_preset_id: str
    clone_engine_id: str | None = None
    format: str
    split_chapters: bool = False
    artifact_basename: str | None = None


class JobArtifactRead(BaseModel):
    artifact_id: str
    filename: str
    label: str
    section_title: str | None = None
    download_url: str


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    voice_preset_id: str
    clone_engine_id: str | None = None
    format: str
    status: str
    split_chapters: bool
    artifact_basename: str
    progress_percent: int
    status_detail: str | None = None
    download_url: str | None = None
    failure_detail: str | None = None
    artifacts: list[JobArtifactRead] = []
    can_retry: bool
    can_cancel: bool
