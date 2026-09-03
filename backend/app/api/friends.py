from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.friends import (
    DirectoryEntryRead,
    FriendRequestCreate,
    FriendsOverviewRead,
    FriendsSummaryRead,
)
from app.services.friends import (
    FriendshipError,
    count_pending_incoming_requests,
    get_directory,
    get_overview,
    request_friend,
    respond_to_request,
    unfriend,
)
from app.services.shares import count_pending_incoming_shares


router = APIRouter(prefix="/api/friends", tags=["friends"])


@router.get("", response_model=FriendsOverviewRead)
def get_friends_route(current_user: CurrentUser = Depends(get_current_user)) -> FriendsOverviewRead:
    return FriendsOverviewRead.model_validate(get_overview(user_id=current_user.id))


@router.get("/directory", response_model=list[DirectoryEntryRead])
def get_directory_route(current_user: CurrentUser = Depends(get_current_user)) -> list[DirectoryEntryRead]:
    return [DirectoryEntryRead.model_validate(entry) for entry in get_directory(user_id=current_user.id)]


@router.get("/summary", response_model=FriendsSummaryRead)
def get_summary_route(current_user: CurrentUser = Depends(get_current_user)) -> FriendsSummaryRead:
    return FriendsSummaryRead(
        pending_friend_requests=count_pending_incoming_requests(user_id=current_user.id),
        pending_shares=count_pending_incoming_shares(user_id=current_user.id),
    )


@router.post("/requests", response_model=FriendsOverviewRead, status_code=status.HTTP_201_CREATED)
def create_friend_request_route(
    payload: FriendRequestCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> FriendsOverviewRead:
    try:
        overview = request_friend(user_id=current_user.id, target_user_id=payload.user_id)
    except FriendshipError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return FriendsOverviewRead.model_validate(overview)


@router.post("/requests/{friendship_id}/accept", response_model=FriendsOverviewRead)
def accept_friend_request_route(
    friendship_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> FriendsOverviewRead:
    try:
        overview = respond_to_request(user_id=current_user.id, friendship_id=friendship_id, accept=True)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return FriendsOverviewRead.model_validate(overview)


@router.post("/requests/{friendship_id}/decline", response_model=FriendsOverviewRead)
def decline_friend_request_route(
    friendship_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> FriendsOverviewRead:
    try:
        overview = respond_to_request(user_id=current_user.id, friendship_id=friendship_id, accept=False)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return FriendsOverviewRead.model_validate(overview)


@router.delete("/{user_id}", response_model=FriendsOverviewRead)
def unfriend_route(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> FriendsOverviewRead:
    try:
        overview = unfriend(user_id=current_user.id, other_user_id=user_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return FriendsOverviewRead.model_validate(overview)
