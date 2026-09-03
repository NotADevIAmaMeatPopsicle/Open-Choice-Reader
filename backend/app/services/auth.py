from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
import app.models.auth_session as auth_session_model
import app.models.user as user_model
import app.models.user_invite as user_invite_model


password_hasher = PasswordHash.recommended()


class BootstrapAlreadyCompleteError(RuntimeError):
    pass


class InvalidCredentialsError(RuntimeError):
    pass


class AuthenticationRequiredError(RuntimeError):
    pass


class UsernameAlreadyExistsError(RuntimeError):
    pass


class InviteClaimError(RuntimeError):
    pass


@dataclass(slots=True)
class SessionContext:
    user: "user_model.User"
    session: "auth_session_model.AuthSession"


@dataclass(slots=True)
class InviteCreationResult:
    invite: "user_invite_model.UserInvite"
    raw_token: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def _hash_token(raw_token: str) -> str:
    return sha256(raw_token.encode("utf-8")).hexdigest()


def _ensure_password_strength(password: str) -> None:
    if len(password) < settings.auth_password_min_length:
        raise ValueError(
            f"Password must be at least {settings.auth_password_min_length} characters long."
        )


def create_user(
    session: Session,
    *,
    username: str,
    display_name: str | None,
    password: str,
    role: str = "member",
) -> "user_model.User":
    normalized_username = normalize_username(username)
    existing = session.scalar(
        select(user_model.User).where(user_model.User.username == normalized_username)
    )
    if existing is not None:
        raise UsernameAlreadyExistsError("That username is already in use.")

    _ensure_password_strength(password)

    user = user_model.User(
        username=normalized_username,
        display_name=(display_name or username).strip(),
        password_hash=hash_password(password),
        role=role,
        status="active",
    )
    session.add(user)
    session.flush()
    return user


def bootstrap_admin(
    session: Session,
    *,
    username: str,
    display_name: str | None,
    password: str,
) -> "user_model.User":
    user_count = session.scalar(select(func.count()).select_from(user_model.User)) or 0
    if user_count > 0:
        raise BootstrapAlreadyCompleteError("Bootstrap admin is no longer available.")

    user = create_user(
        session,
        username=username,
        display_name=display_name,
        password=password,
        role="admin",
    )
    from app.services.ownership_backfill import backfill_legacy_single_user_data

    backfill_legacy_single_user_data(session, user)
    return user


def is_bootstrap_available(session: Session) -> bool:
    user_count = session.scalar(select(func.count()).select_from(user_model.User)) or 0
    return user_count == 0


def authenticate_user(
    session: Session, *, username: str, password: str
) -> "user_model.User":
    normalized_username = normalize_username(username)
    user = session.scalar(
        select(user_model.User).where(user_model.User.username == normalized_username)
    )
    if user is None or user.status != "active":
        raise InvalidCredentialsError("Invalid username or password.")
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid username or password.")

    user.last_login_at = _utcnow()
    session.flush()
    return user


def list_users(session: Session) -> list["user_model.User"]:
    return list(session.scalars(select(user_model.User).order_by(user_model.User.id)))


def issue_session(
    session: Session,
    user: "user_model.User",
    *,
    created_by_ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    raw_token = secrets.token_urlsafe(32)
    session_record = auth_session_model.AuthSession(
        user_id=user.id,
        session_token_hash=_hash_token(raw_token),
        expires_at=_utcnow() + timedelta(hours=settings.auth_session_ttl_hours),
        created_by_ip=created_by_ip,
        user_agent=user_agent,
    )
    session.add(session_record)
    session.flush()
    return raw_token


def _get_active_session(
    session: Session,
    raw_token: str,
    *,
    touch_last_seen: bool,
) -> "auth_session_model.AuthSession | None":
    session_record = session.scalar(
        select(auth_session_model.AuthSession).where(
            auth_session_model.AuthSession.session_token_hash == _hash_token(raw_token)
        )
    )
    if session_record is None:
        return None
    if session_record.revoked_at is not None:
        return None
    if _coerce_utc(session_record.expires_at) <= _utcnow():
        return None

    if touch_last_seen:
        session_record.last_seen_at = _utcnow()
        session.flush()

    return session_record


def get_user_for_session_token(
    session: Session, raw_token: str
) -> "user_model.User | None":
    session_record = _get_active_session(session, raw_token, touch_last_seen=True)
    if session_record is None:
        return None

    user = session.get(user_model.User, session_record.user_id)
    if user is None or user.status != "active":
        return None
    return user


def require_user_for_session_token(
    session: Session, raw_token: str | None
) -> "user_model.User":
    if not raw_token:
        raise AuthenticationRequiredError("You must be signed in.")

    user = get_user_for_session_token(session, raw_token)
    if user is None:
        raise AuthenticationRequiredError("You must be signed in.")
    return user


def revoke_session(session: Session, raw_token: str | None) -> None:
    if not raw_token:
        return

    session_record = _get_active_session(session, raw_token, touch_last_seen=False)
    if session_record is None:
        return

    session_record.revoked_at = _utcnow()
    session.flush()


def change_password(
    session: Session,
    *,
    user: "user_model.User",
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError("Current password is incorrect.")

    _ensure_password_strength(new_password)
    user.password_hash = hash_password(new_password)
    session.flush()


def claim_invite(
    session: Session,
    *,
    token: str,
    username: str,
    display_name: str | None,
    password: str,
) -> "user_model.User":
    invite = session.scalar(
        select(user_invite_model.UserInvite).where(
            user_invite_model.UserInvite.token_hash == _hash_token(token)
        )
    )
    if invite is None or invite.revoked_at is not None:
        raise InviteClaimError("That invite is not valid.")
    if invite.claimed_at is not None:
        raise InviteClaimError("That invite has already been claimed.")
    if invite.expires_at is not None and _coerce_utc(invite.expires_at) <= _utcnow():
        raise InviteClaimError("That invite has expired.")

    user = create_user(
        session,
        username=username,
        display_name=display_name or invite.display_name_hint,
        password=password,
        role=invite.role_to_grant,
    )
    invite.claimed_by_user_id = user.id
    invite.claimed_at = _utcnow()
    session.flush()
    return user


def list_invites(session: Session) -> list["user_invite_model.UserInvite"]:
    statement = select(user_invite_model.UserInvite).order_by(
        user_invite_model.UserInvite.created_at.desc(),
        user_invite_model.UserInvite.id.desc(),
    )
    return list(session.scalars(statement))


def create_invite(
    session: Session,
    *,
    created_by_user_id: int,
    display_name_hint: str | None,
    role_to_grant: str = "member",
    expires_in_days: int | None = None,
) -> InviteCreationResult:
    normalized_role = role_to_grant.strip().lower()
    if normalized_role not in {"admin", "member"}:
        raise ValueError("Invites can only grant the admin or member role.")

    expires_at: datetime | None = None
    if expires_in_days is not None:
        if expires_in_days <= 0:
            raise ValueError("Invite expiry must be at least 1 day.")
        expires_at = _utcnow() + timedelta(days=expires_in_days)

    raw_token = secrets.token_urlsafe(24)
    invite = user_invite_model.UserInvite(
        token_hash=_hash_token(raw_token),
        created_by_user_id=created_by_user_id,
        display_name_hint=display_name_hint.strip() if display_name_hint and display_name_hint.strip() else None,
        role_to_grant=normalized_role,
        expires_at=expires_at,
    )
    session.add(invite)
    session.flush()
    return InviteCreationResult(invite=invite, raw_token=raw_token)


def revoke_invite(session: Session, *, invite_id: int) -> "user_invite_model.UserInvite":
    invite = session.get(user_invite_model.UserInvite, invite_id)
    if invite is None:
        raise LookupError(f"Invite {invite_id} was not found.")

    if invite.revoked_at is None:
        invite.revoked_at = _utcnow()
        session.flush()
    return invite


def revoke_all_sessions_for_user(session: Session, *, user_id: int) -> int:
    revoked_count = 0
    for session_record in session.scalars(
        select(auth_session_model.AuthSession).where(
            auth_session_model.AuthSession.user_id == user_id,
            auth_session_model.AuthSession.revoked_at.is_(None),
        )
    ):
        session_record.revoked_at = _utcnow()
        revoked_count += 1

    session.flush()
    return revoked_count


def require_admin_target(
    session: Session, *, acting_user_id: int, target_user_id: int
) -> "user_model.User":
    if target_user_id == acting_user_id:
        raise ValueError("You cannot change your own account from the admin panel.")

    target = session.get(user_model.User, target_user_id)
    if target is None:
        raise LookupError(f"User {target_user_id} was not found.")
    return target


def admin_update_user(
    session: Session,
    *,
    acting_user_id: int,
    target_user_id: int,
    role: str | None = None,
    status: str | None = None,
) -> "user_model.User":
    target = require_admin_target(
        session, acting_user_id=acting_user_id, target_user_id=target_user_id
    )

    if role is not None:
        normalized_role = role.strip().lower()
        if normalized_role not in {"admin", "member"}:
            raise ValueError("Role must be admin or member.")
        target.role = normalized_role

    if status is not None:
        normalized_status = status.strip().lower()
        if normalized_status not in {"active", "disabled"}:
            raise ValueError("Status must be active or disabled.")
        target.status = normalized_status
        if normalized_status == "disabled":
            revoke_all_sessions_for_user(session, user_id=target.id)

    session.flush()
    return target


def admin_reset_password(
    session: Session, *, acting_user_id: int, target_user_id: int
) -> tuple["user_model.User", str]:
    target = require_admin_target(
        session, acting_user_id=acting_user_id, target_user_id=target_user_id
    )

    temporary_password = f"ocr-{secrets.token_urlsafe(9)}"
    target.password_hash = hash_password(temporary_password)
    revoke_all_sessions_for_user(session, user_id=target.id)
    session.flush()
    return target, temporary_password
