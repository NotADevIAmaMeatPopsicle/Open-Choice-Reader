from pydantic import BaseModel, ConfigDict


class CollectionDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str | None = None
    cover_url: str
    progress_percent: float


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None


class CollectionDocumentAdd(BaseModel):
    document_id: int


class CollectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    document_count: int
    documents: list[CollectionDocumentRead]
