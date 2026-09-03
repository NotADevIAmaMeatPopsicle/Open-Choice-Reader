from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import select

from app import db
import app.models.document as document_model
import app.models.document_profile as document_profile_model
import app.models.section as section_model
import app.models.shared_item as shared_item_model
import app.models.text_chunk as text_chunk_model
import app.models.user as user_model
import app.models.voice_preset as voice_preset_model
from app.services.friends import FriendUserSummary, are_friends
from app.services.user_storage import (
    ensure_user_storage_roots,
    user_covers_root,
    user_source_root,
    user_voices_root,
)


SHARE_STATUS_PENDING = "pending"
SHARE_STATUS_ACCEPTED = "accepted"
SHARE_STATUS_DECLINED = "declined"
SHAREABLE_ITEM_TYPES = {"document", "voice_preset"}


class ShareError(ValueError):
    pass


@dataclass(frozen=True)
class SharedItemRecord:
    id: int
    direction: str
    other_user: FriendUserSummary
    item_type: str
    item_label: str
    message: str | None
    status: str
    accepted_item_id: int | None
    created_at: datetime
    responded_at: datetime | None


@dataclass(frozen=True)
class SharesOverviewRecord:
    incoming: list[SharedItemRecord]
    outgoing: list[SharedItemRecord]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _user_summary(user: "user_model.User") -> FriendUserSummary:
    return FriendUserSummary(id=user.id, username=user.username, display_name=user.display_name)


def create_share(
    *,
    sender_user_id: int,
    recipient_user_id: int,
    item_type: str,
    item_id: int,
    message: str | None = None,
) -> SharesOverviewRecord:
    if item_type not in SHAREABLE_ITEM_TYPES:
        raise ShareError(f"Unsupported share type '{item_type}'.")
    if recipient_user_id == sender_user_id:
        raise ShareError("You cannot share an item with yourself.")

    with db.session_scope() as session:
        recipient = session.get(user_model.User, recipient_user_id)
        if recipient is None or recipient.status != "active":
            raise LookupError("That user was not found.")
        if not are_friends(session, sender_user_id, recipient_user_id):
            raise ShareError("You can only share with accepted friends.")

        item_label = _resolve_item_label(
            session, item_type=item_type, item_id=item_id, owner_user_id=sender_user_id
        )

        existing_pending = session.scalar(
            select(shared_item_model.SharedItem).where(
                shared_item_model.SharedItem.sender_user_id == sender_user_id,
                shared_item_model.SharedItem.recipient_user_id == recipient_user_id,
                shared_item_model.SharedItem.item_type == item_type,
                shared_item_model.SharedItem.source_item_id == item_id,
                shared_item_model.SharedItem.status == SHARE_STATUS_PENDING,
            )
        )
        if existing_pending is not None:
            raise ShareError("You already shared this; it is waiting for their answer.")

        normalized_message = (message or "").strip() or None
        session.add(
            shared_item_model.SharedItem(
                sender_user_id=sender_user_id,
                recipient_user_id=recipient_user_id,
                item_type=item_type,
                source_item_id=item_id,
                item_label=item_label,
                message=normalized_message,
                status=SHARE_STATUS_PENDING,
            )
        )
        session.flush()
        return _build_overview(session, sender_user_id)


def get_overview(*, user_id: int) -> SharesOverviewRecord:
    with db.session_scope() as session:
        return _build_overview(session, user_id)


def count_pending_incoming_shares(*, user_id: int) -> int:
    with db.session_scope() as session:
        return len(
            list(
                session.scalars(
                    select(shared_item_model.SharedItem.id).where(
                        shared_item_model.SharedItem.recipient_user_id == user_id,
                        shared_item_model.SharedItem.status == SHARE_STATUS_PENDING,
                    )
                )
            )
        )


def respond_to_share(*, user_id: int, share_id: int, accept: bool) -> SharesOverviewRecord:
    with db.session_scope() as session:
        share = session.get(shared_item_model.SharedItem, share_id)
        if (
            share is None
            or share.recipient_user_id != user_id
            or share.status != SHARE_STATUS_PENDING
        ):
            raise LookupError("That share was not found.")

        if accept:
            accepted_item_id = _materialize_share_copy(session, share)
            share.accepted_item_id = accepted_item_id
            share.status = SHARE_STATUS_ACCEPTED
        else:
            share.status = SHARE_STATUS_DECLINED

        share.responded_at = _utcnow()
        session.flush()
        return _build_overview(session, user_id)


def _resolve_item_label(session, *, item_type: str, item_id: int, owner_user_id: int) -> str:
    if item_type == "document":
        document = session.get(document_model.Document, item_id)
        if document is None or document.owner_user_id != owner_user_id:
            raise LookupError("That document was not found in your library.")
        return document.title

    preset = session.get(voice_preset_model.VoicePreset, item_id)
    if preset is None or preset.owner_user_id != owner_user_id:
        raise LookupError("That voice preset was not found in your collection.")
    return preset.name


def _materialize_share_copy(session, share: "shared_item_model.SharedItem") -> int:
    if share.item_type == "document":
        return _copy_document_to_user(
            session,
            document_id=share.source_item_id,
            sender_user_id=share.sender_user_id,
            recipient_user_id=share.recipient_user_id,
        )
    return _copy_voice_preset_to_user(
        session,
        preset_id=share.source_item_id,
        sender_user_id=share.sender_user_id,
        recipient_user_id=share.recipient_user_id,
    )


def _copy_document_to_user(
    session, *, document_id: int, sender_user_id: int, recipient_user_id: int
) -> int:
    document = session.get(document_model.Document, document_id)
    if document is None or document.owner_user_id != sender_user_id:
        raise ShareError("The shared document is no longer available from the sender.")

    source_path = Path(document.source_path)
    if not source_path.is_file():
        raise ShareError("The shared document's source file is missing on the sender's side.")

    ensure_user_storage_roots(recipient_user_id)
    copied_source_path = _copy_into_directory(source_path, user_source_root(recipient_user_id))

    copied_document = document_model.Document(
        owner_user_id=recipient_user_id,
        title=document.title,
        format=document.format,
        status=document.status,
        source_path=str(copied_source_path),
        origin_path=None,
    )
    session.add(copied_document)
    session.flush()

    profile = session.get(document_profile_model.DocumentProfile, document.id)
    if profile is not None:
        copied_cover_path: str | None = None
        if profile.cover_path:
            cover_source = Path(profile.cover_path)
            if cover_source.is_file():
                destination = (
                    user_covers_root(recipient_user_id)
                    / f"document-{copied_document.id}{cover_source.suffix}"
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(cover_source, destination)
                copied_cover_path = str(destination)

        session.add(
            document_profile_model.DocumentProfile(
                document_id=copied_document.id,
                author=profile.author,
                summary=profile.summary,
                cover_path=copied_cover_path,
                metadata_source=profile.metadata_source,
                metadata_source_id=profile.metadata_source_id,
                source_provider=profile.source_provider,
                source_provider_id=profile.source_provider_id,
                source_provider_name=profile.source_provider_name,
                source_provider_url=profile.source_provider_url,
                source_url=profile.source_url,
                source_site_name=profile.source_site_name,
                import_mode="friend-share",
                total_sections=profile.total_sections,
                total_chunks=profile.total_chunks,
                estimated_duration_seconds=profile.estimated_duration_seconds,
            )
        )

    sections = list(
        session.scalars(
            select(section_model.Section)
            .where(section_model.Section.document_id == document.id)
            .order_by(section_model.Section.position)
        )
    )
    for section in sections:
        copied_section = section_model.Section(
            document_id=copied_document.id,
            position=section.position,
            title=section.title,
            text=section.text,
        )
        session.add(copied_section)
        session.flush()

        chunks = list(
            session.scalars(
                select(text_chunk_model.TextChunk)
                .where(text_chunk_model.TextChunk.section_id == section.id)
                .order_by(text_chunk_model.TextChunk.position)
            )
        )
        for chunk in chunks:
            session.add(
                text_chunk_model.TextChunk(
                    section_id=copied_section.id,
                    position=chunk.position,
                    text=chunk.text,
                )
            )

    session.flush()
    return copied_document.id


def _copy_voice_preset_to_user(
    session, *, preset_id: int, sender_user_id: int, recipient_user_id: int
) -> int:
    preset = session.get(voice_preset_model.VoicePreset, preset_id)
    if preset is None or preset.owner_user_id != sender_user_id:
        raise ShareError("The shared voice preset is no longer available from the sender.")

    reference_path = Path(preset.reference_path)
    if not reference_path.is_file():
        raise ShareError("The shared preset's reference audio is missing on the sender's side.")

    sender = session.get(user_model.User, sender_user_id)
    sender_name = sender.display_name if sender is not None else "a friend"

    ensure_user_storage_roots(recipient_user_id)
    copied_reference_path = _copy_into_directory(reference_path, user_voices_root(recipient_user_id))

    copied_preset = voice_preset_model.VoicePreset(
        owner_user_id=recipient_user_id,
        name=preset.name,
        engine=preset.engine,
        reference_path=str(copied_reference_path),
        transcript=preset.transcript,
        source_provider="friend-share",
        source_url=preset.source_url,
        transcript_source_url=preset.transcript_source_url,
        license_label=preset.license_label,
        provenance_note=f"Shared by {sender_name} on this Open Choice Reader host.",
    )
    session.add(copied_preset)
    session.flush()
    return copied_preset.id


def _copy_into_directory(source: Path, destination_root: Path) -> Path:
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / source.name
    if destination.exists():
        destination = destination_root / f"{source.stem}-{uuid4().hex[:8]}{source.suffix}"
    shutil.copy2(source, destination)
    return destination


def _build_overview(session, user_id: int) -> SharesOverviewRecord:
    shares = list(
        session.scalars(
            select(shared_item_model.SharedItem)
            .where(
                (shared_item_model.SharedItem.sender_user_id == user_id)
                | (shared_item_model.SharedItem.recipient_user_id == user_id)
            )
            .order_by(shared_item_model.SharedItem.created_at.desc(), shared_item_model.SharedItem.id.desc())
        )
    )

    incoming: list[SharedItemRecord] = []
    outgoing: list[SharedItemRecord] = []
    for share in shares:
        direction = "incoming" if share.recipient_user_id == user_id else "outgoing"
        other_user = session.get(
            user_model.User,
            share.sender_user_id if direction == "incoming" else share.recipient_user_id,
        )
        if other_user is None:
            continue

        record = SharedItemRecord(
            id=share.id,
            direction=direction,
            other_user=_user_summary(other_user),
            item_type=share.item_type,
            item_label=share.item_label,
            message=share.message,
            status=share.status,
            accepted_item_id=share.accepted_item_id,
            created_at=share.created_at,
            responded_at=share.responded_at,
        )
        if direction == "incoming":
            incoming.append(record)
        else:
            outgoing.append(record)

    pending_first = {SHARE_STATUS_PENDING: 0, SHARE_STATUS_ACCEPTED: 1, SHARE_STATUS_DECLINED: 2}
    incoming.sort(key=lambda record: (pending_first.get(record.status, 3),))
    outgoing.sort(key=lambda record: (pending_first.get(record.status, 3),))
    return SharesOverviewRecord(incoming=incoming, outgoing=outgoing)
