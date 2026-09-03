from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.friends import FriendUserRead


class SharedItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    direction: str
    other_user: FriendUserRead
    item_type: str
    item_label: str
    message: str | None = None
    status: str
    accepted_item_id: int | None = None
    created_at: datetime
    responded_at: datetime | None = None


class SharesOverviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incoming: list[SharedItemRead]
    outgoing: list[SharedItemRead]


class ShareCreateRequest(BaseModel):
    recipient_user_id: int
    item_type: str
    item_id: int
    message: str | None = None
