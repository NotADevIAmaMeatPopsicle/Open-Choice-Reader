from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FriendUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str


class FriendRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    friendship_id: int
    user: FriendUserRead
    since: datetime | None = None


class FriendRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    friendship_id: int
    direction: str
    user: FriendUserRead
    created_at: datetime


class FriendsOverviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    friends: list[FriendRead]
    incoming_requests: list[FriendRequestRead]
    outgoing_requests: list[FriendRequestRead]


class DirectoryEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: FriendUserRead
    state: str
    friendship_id: int | None = None


class FriendRequestCreate(BaseModel):
    user_id: int


class FriendsSummaryRead(BaseModel):
    pending_friend_requests: int
    pending_shares: int
