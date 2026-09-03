from pydantic import BaseModel, ConfigDict, Field


class ThemeProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    source_kind: str
    source_label: str
    source_reference: str | None = None
    is_builtin: bool
    sort_order: int = 100
    family: str = "house"
    preview_variant: str = "standard"
    background_asset_path: str | None = None
    background_overlay_path: str | None = None
    shelf_asset_path: str | None = None
    surface_texture_asset_path: str | None = None
    supports_mix_and_match: bool = True
    tokens: dict[str, str] = Field(default_factory=dict)


class ThemeProfileCreate(BaseModel):
    id: str | None = None
    name: str
    description: str | None = None
    source_kind: str
    source_label: str
    source_reference: str | None = None
    family: str = "imported"
    preview_variant: str = "standard"
    background_asset_path: str | None = None
    background_overlay_path: str | None = None
    shelf_asset_path: str | None = None
    surface_texture_asset_path: str | None = None
    supports_mix_and_match: bool = True
    tokens: dict[str, str]


class ThemeApplyRead(BaseModel):
    active_theme_id: str
    active_theme: ThemeProfileRead


class ThemeImportMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_variable: str
    target_token: str
    value: str


class ThemeImportFallbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_token: str
    source_variable: str | None = None
    value: str
    reason: str


class KavitaThemeImportReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detected_variable_count: int
    mapped_variables: list[ThemeImportMappingRead] = Field(default_factory=list)
    ignored_variables: list[str] = Field(default_factory=list)
    fallback_tokens: list[ThemeImportFallbackRead] = Field(default_factory=list)


class KavitaThemeImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: ThemeProfileRead
    report: KavitaThemeImportReportRead
