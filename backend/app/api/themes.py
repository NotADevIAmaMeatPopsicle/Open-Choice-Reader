from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.api.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.schemas.theme import (
    KavitaThemeImportRead,
    ThemeApplyRead,
    ThemeProfileCreate,
    ThemeProfileRead,
)
from app.services.kavita_theme_import import import_kavita_theme
from app.services.settings import set_active_theme
from app.services.themes import create_theme, delete_theme, get_theme, list_themes
from app.services.uploads import read_upload_bytes_async


router = APIRouter(prefix="/api/themes", tags=["themes"])


@router.get("", response_model=list[ThemeProfileRead])
def list_themes_route(current_user: CurrentUser = Depends(get_current_user)) -> list[ThemeProfileRead]:
    return [
        ThemeProfileRead.model_validate(theme)
        for theme in list_themes(owner_user_id=current_user.id)
    ]


@router.post("/import/kavita", response_model=KavitaThemeImportRead, status_code=status.HTTP_201_CREATED)
async def import_kavita_theme_route(
    name: str | None = Form(default=None),
    css_text: str | None = Form(default=None),
    css_file: UploadFile | None = File(default=None),
    current_user: CurrentUser = Depends(get_current_user),
) -> KavitaThemeImportRead:
    if css_text and css_file is not None:
        raise HTTPException(status_code=422, detail="Provide either pasted CSS or an uploaded CSS file, not both")
    if not css_text and css_file is None:
        raise HTTPException(status_code=422, detail="Provide Kavita CSS text or upload a .css file")

    source_reference: str | None = None
    resolved_css_text = css_text.strip() if css_text else None
    if css_file is not None:
        source_reference = css_file.filename or "uploaded-theme.css"
        try:
            resolved_css_text = (
                await read_upload_bytes_async(css_file, max_bytes=settings.theme_upload_max_bytes)
            ).decode("utf-8")
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=422, detail="Uploaded theme files must be UTF-8 encoded CSS") from error
    elif resolved_css_text is not None:
        source_reference = "pasted-css"

    if len((resolved_css_text or "").encode("utf-8")) > settings.theme_upload_max_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"The theme exceeds the {settings.theme_upload_max_bytes}-byte limit",
        )

    try:
        result = import_kavita_theme(
            css_text=resolved_css_text or "",
            name=name,
            source_reference=source_reference,
            owner_user_id=current_user.id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return KavitaThemeImportRead.model_validate(result)


@router.get("/{theme_id}", response_model=ThemeProfileRead)
def get_theme_route(
    theme_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> ThemeProfileRead:
    try:
        theme = get_theme(theme_id, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return ThemeProfileRead.model_validate(theme)


@router.post("", response_model=ThemeProfileRead, status_code=status.HTTP_201_CREATED)
def create_theme_route(
    payload: ThemeProfileCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> ThemeProfileRead:
    try:
        theme = create_theme(
            owner_user_id=current_user.id,
            theme_id=payload.id,
            name=payload.name,
            description=payload.description,
            source_kind=payload.source_kind,
            source_label=payload.source_label,
            source_reference=payload.source_reference,
            family=payload.family,
            preview_variant=payload.preview_variant,
            background_asset_path=payload.background_asset_path,
            background_overlay_path=payload.background_overlay_path,
            shelf_asset_path=payload.shelf_asset_path,
            surface_texture_asset_path=payload.surface_texture_asset_path,
            supports_mix_and_match=payload.supports_mix_and_match,
            tokens=payload.tokens,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return ThemeProfileRead.model_validate(theme)


@router.post("/{theme_id}/apply", response_model=ThemeApplyRead)
def apply_theme_route(
    theme_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> ThemeApplyRead:
    try:
        snapshot = set_active_theme(theme_id, user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return ThemeApplyRead.model_validate(
        {
            "active_theme_id": snapshot.active_theme_id,
            "active_theme": snapshot.active_theme,
        }
    )


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_theme_route(
    theme_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    try:
        delete_theme(theme_id, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
