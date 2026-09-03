from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: str
    status: str
    last_login_at: datetime | None = None


class AdminUserRead(AuthUserRead):
    created_at: datetime | None = None
    documents_count: int = 0
    voice_presets_count: int = 0
    jobs_count: int = 0
    storage_bytes: int = 0


class AdminUserUpdateRequest(BaseModel):
    role: str | None = None
    status: str | None = None


class AdminPasswordResetRead(BaseModel):
    user: AuthUserRead
    temporary_password: str


class AdminSessionsRevokedRead(BaseModel):
    user: AuthUserRead
    revoked_sessions: int


class BootstrapAdminRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=1, max_length=1024)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=1, max_length=1024)


class ClaimInviteRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    username: str = Field(min_length=1, max_length=64)
    display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=1, max_length=1024)


class AuthSessionRead(BaseModel):
    user: AuthUserRead


class BootstrapStatusRead(BaseModel):
    bootstrap_available: bool


class UserInviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_user_id: int | None = None
    claimed_by_user_id: int | None = None
    display_name_hint: str | None = None
    role_to_grant: str
    expires_at: datetime | None = None
    claimed_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class CreateInviteRequest(BaseModel):
    display_name_hint: str | None = Field(default=None, max_length=120)
    role_to_grant: str = Field(default="member", max_length=20)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class InviteCreateRead(BaseModel):
    invite: UserInviteRead
    token: str
