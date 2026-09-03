from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.shares import ShareCreateRequest, SharesOverviewRead
from app.services.shares import ShareError, create_share, get_overview, respond_to_share


router = APIRouter(prefix="/api/shares", tags=["shares"])


@router.get("", response_model=SharesOverviewRead)
def get_shares_route(current_user: CurrentUser = Depends(get_current_user)) -> SharesOverviewRead:
    return SharesOverviewRead.model_validate(get_overview(user_id=current_user.id))


@router.post("", response_model=SharesOverviewRead, status_code=status.HTTP_201_CREATED)
def create_share_route(
    payload: ShareCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> SharesOverviewRead:
    try:
        overview = create_share(
            sender_user_id=current_user.id,
            recipient_user_id=payload.recipient_user_id,
            item_type=payload.item_type,
            item_id=payload.item_id,
            message=payload.message,
        )
    except ShareError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return SharesOverviewRead.model_validate(overview)


@router.post("/{share_id}/accept", response_model=SharesOverviewRead)
def accept_share_route(
    share_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> SharesOverviewRead:
    try:
        overview = respond_to_share(user_id=current_user.id, share_id=share_id, accept=True)
    except ShareError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return SharesOverviewRead.model_validate(overview)


@router.post("/{share_id}/decline", response_model=SharesOverviewRead)
def decline_share_route(
    share_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> SharesOverviewRead:
    try:
        overview = respond_to_share(user_id=current_user.id, share_id=share_id, accept=False)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return SharesOverviewRead.model_validate(overview)
