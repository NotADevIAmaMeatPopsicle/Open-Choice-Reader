from pydantic import BaseModel, ConfigDict, Field


class CatalogSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    supports_search: bool
    supports_browse: bool


class CatalogResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    source_name: str
    title: str
    author: str | None
    summary: str | None
    cover_url: str | None
    detail_url: str
    download_format: str | None
    language: str | None
    importable: bool


class CatalogImportRequest(BaseModel):
    source: str = Field(min_length=1, max_length=64)
    catalog_id: str = Field(min_length=1, max_length=2048)


class UrlImportRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


class TextImportRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=5_000_000)
    author: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None, max_length=4096)
