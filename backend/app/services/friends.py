from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import or_, select

from app import db
import app.models.friendship as friendship_model
import app.models.user as user_model


FRIENDSHIP_STATUS_PENDING = "pending"
FRIENDSHIP_STATUS_ACCEPTED = "accepted"
FRIENDSHIP_STATUS_DECLINED = "declined"


class FriendshipError(ValueError):
    pass


@dataclass(frozen=True)
class FriendUserSummary:
    id: int
    username: str
    display_name: str


@dataclass(frozen=True)
class FriendRecord:
    friendship_id: int
    user: FriendUserSummary
    since: datetime | None


@dataclass(frozen=True)
class FriendRequestRecord:
    friendship_id: int
    direction: str
    user: FriendUserSummary
    created_at: datetime


@dataclass(frozen=True)
class DirectoryEntryRecord:
    user: FriendUserSummary
    state: str
    friendship_id: int | None


@dataclass(frozen=True)
class FriendsOverviewRecord:
    friends: list[FriendRecord]
    incoming_requests: list[FriendRequestRecord]
    outgoing_requests: list[FriendRequestRecord]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _user_summary(user: "user_model.User") -> FriendUserSummary:
    return FriendUserSummary(id=user.id, username=user.username, display_name=user.display_name)


def _friendship_between(session, user_a_id: int, user_b_id: int) -> "friendship_model.Friendship | None":
    return session.scalar(
        select(friendship_model.Friendship).where(
            or_(
                (friendship_model.Friendship.requester_user_id == user_a_id)
                & (friendship_model.Friendship.addressee_user_id == user_b_id),
                (friendship_model.Friendship.requester_user_id == user_b_id)
                & (friendship_model.Friendship.addressee_user_id == user_a_id),
            )
        )
    )


def are_friends(session, user_a_id: int, user_b_id: int) -> bool:
    friendship = _friendship_between(session, user_a_id, user_b_id)
    return friendship is not None and friendship.status == FRIENDSHIP_STATUS_ACCEPTED


def request_friend(*, user_id: int, target_user_id: int) -> FriendsOverviewRecord:
    if user_id == target_user_id:
        raise FriendshipError("You cannot send a friend request to yourself.")

    with db.session_scope() as session:
        target = session.get(user_model.User, target_user_id)
        if target is None or target.status != "active":
            raise LookupError("That user was not found.")

        friendship = _friendship_between(session, user_id, target_user_id)
        if friendship is None:
            session.add(
                friendship_model.Friendship(
                    requester_user_id=user_id,
                    addressee_user_id=target_user_id,
                    status=FRIENDSHIP_STATUS_PENDING,
                )
            )
        elif friendship.status == FRIENDSHIP_STATUS_ACCEPTED:
            raise FriendshipError("You are already friends.")
        elif friendship.status == FRIENDSHIP_STATUS_PENDING:
            if friendship.requester_user_id == user_id:
                raise FriendshipError("Your friend request is still waiting for an answer.")
            friendship.status = FRIENDSHIP_STATUS_ACCEPTED
            friendship.responded_at = _utcnow()
        else:
            friendship.requester_user_id = user_id
            friendship.addressee_user_id = target_user_id
            friendship.status = FRIENDSHIP_STATUS_PENDING
            friendship.created_at = _utcnow()
            friendship.responded_at = None

        session.flush()
        return _build_overview(session, user_id)


def respond_to_request(*, user_id: int, friendship_id: int, accept: bool) -> FriendsOverviewRecord:
    with db.session_scope() as session:
        friendship = session.get(friendship_model.Friendship, friendship_id)
        if (
            friendship is None
            or friendship.addressee_user_id != user_id
            or friendship.status != FRIENDSHIP_STATUS_PENDING
        ):
            raise LookupError("That friend request was not found.")

        friendship.status = FRIENDSHIP_STATUS_ACCEPTED if accept else FRIENDSHIP_STATUS_DECLINED
        friendship.responded_at = _utcnow()
        session.flush()
        return _build_overview(session, user_id)


def unfriend(*, user_id: int, other_user_id: int) -> FriendsOverviewRecord:
    with db.session_scope() as session:
        friendship = _friendship_between(session, user_id, other_user_id)
        if friendship is None or friendship.status != FRIENDSHIP_STATUS_ACCEPTED:
            raise LookupError("You are not friends with that user.")

        session.delete(friendship)
        session.flush()
        return _build_overview(session, user_id)


def get_overview(*, user_id: int) -> FriendsOverviewRecord:
    with db.session_scope() as session:
        return _build_overview(session, user_id)


def list_friend_summaries(*, user_id: int) -> list[FriendUserSummary]:
    with db.session_scope() as session:
        return [friend.user for friend in _build_overview(session, user_id).friends]


def get_directory(*, user_id: int) -> list[DirectoryEntryRecord]:
    with db.session_scope() as session:
        users = list(
            session.scalars(
                select(user_model.User)
                .where(user_model.User.id != user_id, user_model.User.status == "active")
                .order_by(user_model.User.display_name)
            )
        )

        entries: list[DirectoryEntryRecord] = []
        for user in users:
            friendship = _friendship_between(session, user_id, user.id)
            state = "none"
            friendship_id: int | None = None
            if friendship is not None and friendship.status == FRIENDSHIP_STATUS_ACCEPTED:
                state = "friends"
                friendship_id = friendship.id
            elif friendship is not None and friendship.status == FRIENDSHIP_STATUS_PENDING:
                friendship_id = friendship.id
                state = (
                    "pending_outgoing"
                    if friendship.requester_user_id == user_id
                    else "pending_incoming"
                )
            entries.append(
                DirectoryEntryRecord(user=_user_summary(user), state=state, friendship_id=friendship_id)
            )

        return entries


def count_pending_incoming_requests(*, user_id: int) -> int:
    with db.session_scope() as session:
        return len(
            list(
                session.scalars(
                    select(friendship_model.Friendship.id).where(
                        friendship_model.Friendship.addressee_user_id == user_id,
                        friendship_model.Friendship.status == FRIENDSHIP_STATUS_PENDING,
                    )
                )
            )
        )


def _build_overview(session, user_id: int) -> FriendsOverviewRecord:
    friendships = list(
        session.scalars(
            select(friendship_model.Friendship).where(
                or_(
                    friendship_model.Friendship.requester_user_id == user_id,
                    friendship_model.Friendship.addressee_user_id == user_id,
                )
            )
        )
    )

    friends: list[FriendRecord] = []
    incoming: list[FriendRequestRecord] = []
    outgoing: list[FriendRequestRecord] = []

    for friendship in friendships:
        other_user_id = (
            friendship.addressee_user_id
            if friendship.requester_user_id == user_id
            else friendship.requester_user_id
        )
        other_user = session.get(user_model.User, other_user_id)
        if other_user is None or other_user.status != "active":
            continue

        if friendship.status == FRIENDSHIP_STATUS_ACCEPTED:
            friends.append(
                FriendRecord(
                    friendship_id=friendship.id,
                    user=_user_summary(other_user),
                    since=friendship.responded_at,
                )
            )
        elif friendship.status == FRIENDSHIP_STATUS_PENDING:
            request_record = FriendRequestRecord(
                friendship_id=friendship.id,
                direction="incoming" if friendship.addressee_user_id == user_id else "outgoing",
                user=_user_summary(other_user),
                created_at=friendship.created_at,
            )
            if request_record.direction == "incoming":
                incoming.append(request_record)
            else:
                outgoing.append(request_record)

    friends.sort(key=lambda record: record.user.display_name.lower())
    incoming.sort(key=lambda record: record.created_at)
    outgoing.sort(key=lambda record: record.created_at)
    return FriendsOverviewRecord(friends=friends, incoming_requests=incoming, outgoing_requests=outgoing)
