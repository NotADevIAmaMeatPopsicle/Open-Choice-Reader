from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException

from app.config import settings
from app.db import session_scope
import app.services.auth as auth_service


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: int
    username: str
    display_name: str
    role: str
    status: str


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=settings.auth_session_cookie_name),
) -> CurrentUser:
    with session_scope() as session:
        try:
            user = auth_service.require_user_for_session_token(session, session_token)
        except auth_service.AuthenticationRequiredError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

        return CurrentUser(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            status=user.status,
        )


def get_current_admin_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access is required.")
    return current_user
