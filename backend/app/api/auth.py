from pathlib import Path
import ipaddress
import secrets

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, get_current_admin_user
from app.db import session_scope
from app.schemas.auth import (
    AdminPasswordResetRead,
    AdminSessionsRevokedRead,
    AdminUserRead,
    AdminUserUpdateRequest,
    AuthSessionRead,
    AuthUserRead,
    BootstrapAdminRequest,
    BootstrapStatusRead,
    ChangePasswordRequest,
    ClaimInviteRequest,
    CreateInviteRequest,
    InviteCreateRead,
    LoginRequest,
    UserInviteRead,
)
from app.config import settings
import app.models.document as document_model
import app.models.job as job_model
import app.models.voice_preset as voice_preset_model
import app.services.auth as auth_service
from app.services.login_throttle import LoginAttemptLimiter
from app.services.user_storage import user_root


router = APIRouter(prefix="/api/auth", tags=["auth"])
login_limiter = LoginAttemptLimiter(
    max_attempts=settings.auth_login_max_attempts,
    window_seconds=settings.auth_login_window_seconds,
)


def _is_loopback_request(request: Request) -> bool:
    if request.client is None:
        return False

    if any(
        header_name in request.headers
        for header_name in (
            "forwarded",
            "x-forwarded-for",
            "x-forwarded-host",
            "x-forwarded-proto",
            "x-real-ip",
        )
    ):
        return False

    request_hostname = request.url.hostname
    if request.client.host == "testclient":
        return request_hostname == "testserver"

    try:
        client_is_loopback = ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        return False

    if request_hostname is None:
        return False
    if request_hostname.rstrip(".").lower() == "localhost":
        return client_is_loopback
    try:
        return client_is_loopback and ipaddress.ip_address(request_hostname).is_loopback
    except ValueError:
        return False


def _require_bootstrap_access(request: Request, supplied_token: str | None) -> None:
    configured_token = settings.auth_bootstrap_token
    if configured_token:
        if supplied_token and secrets.compare_digest(supplied_token, configured_token):
            return
        raise HTTPException(status_code=403, detail="A valid bootstrap token is required.")
    if not _is_loopback_request(request):
        raise HTTPException(
            status_code=403,
            detail="Initial administrator setup is limited to localhost unless a bootstrap token is configured.",
        )


def _set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=raw_token,
        max_age=settings.auth_session_ttl_hours * 60 * 60,
        httponly=True,
        secure=settings.auth_session_secure,
        samesite=settings.auth_session_samesite,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
        path="/",
        secure=settings.auth_session_secure,
        samesite=settings.auth_session_samesite,
    )


def _request_ip(request: Request) -> str | None:
    return request.client.host if request.client is not None else None


def _session_cookie(session_token: str | None = Cookie(default=None, alias=settings.auth_session_cookie_name)) -> str | None:
    return session_token


@router.get("/bootstrap-status", response_model=BootstrapStatusRead)
def bootstrap_status_route() -> BootstrapStatusRead:
    with session_scope() as session:
        return BootstrapStatusRead(bootstrap_available=auth_service.is_bootstrap_available(session))


@router.post("/bootstrap-admin", response_model=AuthSessionRead, status_code=status.HTTP_201_CREATED)
def bootstrap_admin_route(
    payload: BootstrapAdminRequest,
    request: Request,
    response: Response,
    bootstrap_token: str | None = Header(default=None, alias="X-Bootstrap-Token"),
) -> AuthSessionRead:
    _require_bootstrap_access(request, bootstrap_token)
    with session_scope() as session:
        try:
            user = auth_service.bootstrap_admin(
                session,
                username=payload.username,
                display_name=payload.display_name,
                password=payload.password,
            )
        except auth_service.BootstrapAlreadyCompleteError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        raw_token = auth_service.issue_session(
            session,
            user,
            created_by_ip=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        _set_session_cookie(response, raw_token)
        return AuthSessionRead(user=AuthUserRead.model_validate(user))


@router.post("/login", response_model=AuthSessionRead)
def login_route(payload: LoginRequest, request: Request, response: Response) -> AuthSessionRead:
    client_host = request.client.host if request.client is not None else "unknown"
    limiter_key = f"{client_host}:{auth_service.normalize_username(payload.username)}"
    retry_after = login_limiter.retry_after(limiter_key)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    with session_scope() as session:
        try:
            user = auth_service.authenticate_user(session, username=payload.username, password=payload.password)
        except auth_service.InvalidCredentialsError as error:
            login_limiter.record_failure(limiter_key)
            raise HTTPException(status_code=401, detail=str(error)) from error

        login_limiter.clear(limiter_key)
        raw_token = auth_service.issue_session(
            session,
            user,
            created_by_ip=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        _set_session_cookie(response, raw_token)
        return AuthSessionRead(user=AuthUserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_route(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=settings.auth_session_cookie_name),
) -> Response:
    with session_scope() as session:
        auth_service.revoke_session(session, session_token)

    _clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthUserRead)
def me_route(session_token: str | None = _session_cookie()) -> AuthUserRead:
    with session_scope() as session:
        try:
            user = auth_service.require_user_for_session_token(session, session_token)
        except auth_service.AuthenticationRequiredError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

        return AuthUserRead.model_validate(user)


def _directory_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0

    total_bytes = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total_bytes += child.stat().st_size
            except OSError:
                continue
    return total_bytes


def _count_owned(session, model, owner_column, user_id: int) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(owner_column == user_id)) or 0)


@router.get("/users", response_model=list[AdminUserRead])
def list_users_route(current_user: CurrentUser = Depends(get_current_admin_user)) -> list[AdminUserRead]:
    with session_scope() as session:
        users = auth_service.list_users(session)
        results: list[AdminUserRead] = []
        for user in users:
            base = AdminUserRead.model_validate(user)
            results.append(
                base.model_copy(
                    update={
                        "created_at": user.created_at,
                        "documents_count": _count_owned(
                            session, document_model.Document, document_model.Document.owner_user_id, user.id
                        ),
                        "voice_presets_count": _count_owned(
                            session,
                            voice_preset_model.VoicePreset,
                            voice_preset_model.VoicePreset.owner_user_id,
                            user.id,
                        ),
                        "jobs_count": _count_owned(
                            session, job_model.Job, job_model.Job.user_id, user.id
                        ),
                        "storage_bytes": _directory_size_bytes(user_root(user.id)),
                    }
                )
            )
        return results


@router.patch("/users/{user_id}", response_model=AdminUserRead)
def admin_update_user_route(
    user_id: int,
    payload: AdminUserUpdateRequest,
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> AdminUserRead:
    with session_scope() as session:
        try:
            user = auth_service.admin_update_user(
                session,
                acting_user_id=current_user.id,
                target_user_id=user_id,
                role=payload.role,
                status=payload.status,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        return AdminUserRead.model_validate(user)


@router.post("/users/{user_id}/reset-password", response_model=AdminPasswordResetRead)
def admin_reset_password_route(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> AdminPasswordResetRead:
    with session_scope() as session:
        try:
            user, temporary_password = auth_service.admin_reset_password(
                session,
                acting_user_id=current_user.id,
                target_user_id=user_id,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        return AdminPasswordResetRead(
            user=AuthUserRead.model_validate(user),
            temporary_password=temporary_password,
        )


@router.post("/users/{user_id}/revoke-sessions", response_model=AdminSessionsRevokedRead)
def admin_revoke_sessions_route(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> AdminSessionsRevokedRead:
    with session_scope() as session:
        try:
            user = auth_service.require_admin_target(
                session, acting_user_id=current_user.id, target_user_id=user_id
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        revoked_sessions = auth_service.revoke_all_sessions_for_user(session, user_id=user.id)
        return AdminSessionsRevokedRead(
            user=AuthUserRead.model_validate(user),
            revoked_sessions=revoked_sessions,
        )


@router.get("/invites", response_model=list[UserInviteRead])
def list_invites_route(current_user: CurrentUser = Depends(get_current_admin_user)) -> list[UserInviteRead]:
    with session_scope() as session:
        invites = auth_service.list_invites(session)
        return [UserInviteRead.model_validate(invite) for invite in invites]


@router.post("/invites", response_model=InviteCreateRead, status_code=status.HTTP_201_CREATED)
def create_invite_route(
    payload: CreateInviteRequest,
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> InviteCreateRead:
    with session_scope() as session:
        try:
            result = auth_service.create_invite(
                session,
                created_by_user_id=current_user.id,
                display_name_hint=payload.display_name_hint,
                role_to_grant=payload.role_to_grant,
                expires_in_days=payload.expires_in_days,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        return InviteCreateRead(
            invite=UserInviteRead.model_validate(result.invite),
            token=result.raw_token,
        )


@router.post("/invites/{invite_id}/revoke", response_model=UserInviteRead)
def revoke_invite_route(
    invite_id: int,
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> UserInviteRead:
    with session_scope() as session:
        try:
            invite = auth_service.revoke_invite(session, invite_id=invite_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return UserInviteRead.model_validate(invite)


@router.post("/change-password", response_model=AuthUserRead)
def change_password_route(
    payload: ChangePasswordRequest,
    session_token: str | None = _session_cookie(),
) -> AuthUserRead:
    with session_scope() as session:
        try:
            user = auth_service.require_user_for_session_token(session, session_token)
            auth_service.change_password(
                session,
                user=user,
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
        except auth_service.AuthenticationRequiredError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        except auth_service.InvalidCredentialsError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        return AuthUserRead.model_validate(user)


@router.post("/claim-invite", response_model=AuthSessionRead, status_code=status.HTTP_201_CREATED)
def claim_invite_route(
    payload: ClaimInviteRequest,
    request: Request,
    response: Response,
) -> AuthSessionRead:
    with session_scope() as session:
        try:
            user = auth_service.claim_invite(
                session,
                token=payload.token,
                username=payload.username,
                display_name=payload.display_name,
                password=payload.password,
            )
        except auth_service.InviteClaimError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        raw_token = auth_service.issue_session(
            session,
            user,
            created_by_ip=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        _set_session_cookie(response, raw_token)
        return AuthSessionRead(user=AuthUserRead.model_validate(user))
