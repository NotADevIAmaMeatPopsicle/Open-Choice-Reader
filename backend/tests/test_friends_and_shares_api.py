from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings

SHORT_SAMPLE_TEXT = "First sentence. Second sentence."


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    for module_name in (
        "app.models.app_setting",
        "app.models.auth_session",
        "app.models.collection",
        "app.models.document",
        "app.models.document_profile",
        "app.models.document_progress",
        "app.models.friendship",
        "app.models.job",
        "app.models.playback_session",
        "app.models.section",
        "app.models.shared_item",
        "app.models.text_chunk",
        "app.models.theme_profile",
        "app.models.user",
        "app.models.user_invite",
        "app.models.user_setting",
        "app.models.voice_preset",
    ):
        reload(import_module(module_name))

    reload(import_module("app.db"))
    reload(import_module("app.services.auth"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.friends"))
    reload(import_module("app.services.playback"))
    reload(import_module("app.services.shares"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.api.auth"))
    reload(import_module("app.api.documents"))
    reload(import_module("app.api.friends"))
    reload(import_module("app.api.playback"))
    reload(import_module("app.api.shares"))

    main_module = import_module("app.main")
    return reload(main_module).app


def _bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "alice",
            "display_name": "Alice",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201


def _create_user(*, username: str, display_name: str, password: str) -> int:
    db_module = import_module("app.db")
    auth_service = import_module("app.services.auth")

    with db_module.session_scope() as session:
        user = auth_service.create_user(
            session,
            username=username,
            display_name=display_name,
            password=password,
        )
        return user.id


def _login(client: TestClient, *, username: str, password: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


def _make_friends(sender: TestClient, recipient: TestClient, *, recipient_user_id: int) -> None:
    request_response = sender.post("/api/friends/requests", json={"user_id": recipient_user_id})
    assert request_response.status_code == 201

    overview = recipient.get("/api/friends").json()
    assert len(overview["incoming_requests"]) == 1
    friendship_id = overview["incoming_requests"][0]["friendship_id"]

    accept_response = recipient.post(f"/api/friends/requests/{friendship_id}/accept")
    assert accept_response.status_code == 200
    assert len(accept_response.json()["friends"]) == 1


def _create_voice_preset(owner_user_id: int, *, name: str = "Shared Narrator") -> int:
    db_module = import_module("app.db")
    voice_preset_model = import_module("app.models.voice_preset")
    user_storage = import_module("app.services.user_storage")

    voices_root = user_storage.user_voices_root(owner_user_id)
    voices_root.mkdir(parents=True, exist_ok=True)
    reference_path = voices_root / "reference.wav"
    reference_path.write_bytes(b"RIFF-reference-audio")

    with db_module.session_scope() as session:
        preset = voice_preset_model.VoicePreset(
            owner_user_id=owner_user_id,
            name=name,
            engine="qwen3_clone",
            reference_path=str(reference_path),
            transcript="A calm, warm speaking sample.",
        )
        session.add(preset)
        session.flush()
        session.refresh(preset)
        return preset.id


@pytest.fixture()
def client_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'friends.db'}")

    app = _load_app()

    with TestClient(app) as alice_client, TestClient(app) as bob_client:
        _bootstrap_admin(alice_client)
        bob_user_id = _create_user(username="bob", display_name="Bob", password="bob-password-123")
        _login(bob_client, username="bob", password="bob-password-123")
        yield alice_client, bob_client, bob_user_id


def test_friend_request_lifecycle(client_pair) -> None:
    alice_client, bob_client, bob_user_id = client_pair

    directory = alice_client.get("/api/friends/directory").json()
    assert [entry["user"]["username"] for entry in directory] == ["bob"]
    assert directory[0]["state"] == "none"

    request_response = alice_client.post("/api/friends/requests", json={"user_id": bob_user_id})
    assert request_response.status_code == 201
    assert len(request_response.json()["outgoing_requests"]) == 1

    repeat_response = alice_client.post("/api/friends/requests", json={"user_id": bob_user_id})
    assert repeat_response.status_code == 422

    bob_summary = bob_client.get("/api/friends/summary").json()
    assert bob_summary["pending_friend_requests"] == 1

    bob_overview = bob_client.get("/api/friends").json()
    friendship_id = bob_overview["incoming_requests"][0]["friendship_id"]
    accept_response = bob_client.post(f"/api/friends/requests/{friendship_id}/accept")
    assert accept_response.status_code == 200
    assert accept_response.json()["friends"][0]["user"]["username"] == "alice"

    alice_overview = alice_client.get("/api/friends").json()
    assert alice_overview["friends"][0]["user"]["username"] == "bob"

    unfriend_response = alice_client.delete(f"/api/friends/{bob_user_id}")
    assert unfriend_response.status_code == 200
    assert unfriend_response.json()["friends"] == []


def test_mutual_friend_requests_auto_accept(client_pair) -> None:
    alice_client, bob_client, bob_user_id = client_pair

    assert alice_client.post("/api/friends/requests", json={"user_id": bob_user_id}).status_code == 201

    alice_user_id = alice_client.get("/api/auth/me").json()["id"]
    mutual_response = bob_client.post("/api/friends/requests", json={"user_id": alice_user_id})
    assert mutual_response.status_code == 201
    assert mutual_response.json()["friends"][0]["user"]["username"] == "alice"


def test_share_requires_friendship_and_ownership(client_pair) -> None:
    alice_client, bob_client, bob_user_id = client_pair

    import_response = alice_client.post(
        "/api/documents/import",
        files={"file": ("frankenstein.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    not_friends_response = alice_client.post(
        "/api/shares",
        json={"recipient_user_id": bob_user_id, "item_type": "document", "item_id": document_id},
    )
    assert not_friends_response.status_code == 422

    _make_friends(alice_client, bob_client, recipient_user_id=bob_user_id)

    alice_user_id = alice_client.get("/api/auth/me").json()["id"]
    not_owner_response = bob_client.post(
        "/api/shares",
        json={"recipient_user_id": alice_user_id, "item_type": "document", "item_id": document_id},
    )
    assert not_owner_response.status_code == 404


def test_shared_document_accept_creates_independent_copy(client_pair, tmp_path: Path) -> None:
    alice_client, bob_client, bob_user_id = client_pair
    _make_friends(alice_client, bob_client, recipient_user_id=bob_user_id)

    import_response = alice_client.post(
        "/api/documents/import",
        files={"file": ("frankenstein.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    share_response = alice_client.post(
        "/api/shares",
        json={
            "recipient_user_id": bob_user_id,
            "item_type": "document",
            "item_id": document_id,
            "message": "You will love this one.",
        },
    )
    assert share_response.status_code == 201
    assert share_response.json()["outgoing"][0]["status"] == "pending"

    duplicate_response = alice_client.post(
        "/api/shares",
        json={"recipient_user_id": bob_user_id, "item_type": "document", "item_id": document_id},
    )
    assert duplicate_response.status_code == 422

    bob_incoming = bob_client.get("/api/shares").json()["incoming"]
    assert len(bob_incoming) == 1
    assert bob_incoming[0]["item_label"] == "frankenstein"
    assert bob_incoming[0]["message"] == "You will love this one."
    share_id = bob_incoming[0]["id"]

    assert bob_client.get("/api/friends/summary").json()["pending_shares"] == 1

    accept_response = bob_client.post(f"/api/shares/{share_id}/accept")
    assert accept_response.status_code == 200
    accepted_share = accept_response.json()["incoming"][0]
    assert accepted_share["status"] == "accepted"
    copied_document_id = accepted_share["accepted_item_id"]
    assert copied_document_id is not None
    assert copied_document_id != document_id

    bob_documents = bob_client.get("/api/documents").json()
    assert [document["id"] for document in bob_documents] == [copied_document_id]

    playback_response = bob_client.post(
        "/api/playback/sessions",
        json={"document_id": copied_document_id},
    )
    assert playback_response.status_code == 201
    assert playback_response.json()["current_chunk_text"] == SHORT_SAMPLE_TEXT

    db_module = import_module("app.db")
    document_model = import_module("app.models.document")
    user_storage = import_module("app.services.user_storage")
    with db_module.session_scope() as session:
        copied_document = session.get(document_model.Document, copied_document_id)
        assert copied_document is not None
        assert copied_document.owner_user_id == bob_user_id
        copied_source = Path(copied_document.source_path)
        assert copied_source.is_file()
        assert copied_source.resolve().is_relative_to(
            user_storage.user_source_root(bob_user_id).resolve()
        )

    alice_documents = alice_client.get("/api/documents").json()
    assert [document["id"] for document in alice_documents] == [document_id]


def test_accepted_document_copy_survives_sender_deleting_original(client_pair) -> None:
    alice_client, bob_client, bob_user_id = client_pair
    _make_friends(alice_client, bob_client, recipient_user_id=bob_user_id)

    import_response = alice_client.post(
        "/api/documents/import",
        files={"file": ("frankenstein.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    share_response = alice_client.post(
        "/api/shares",
        json={"recipient_user_id": bob_user_id, "item_type": "document", "item_id": document_id},
    )
    assert share_response.status_code == 201

    share_id = bob_client.get("/api/shares").json()["incoming"][0]["id"]
    accept_response = bob_client.post(f"/api/shares/{share_id}/accept")
    assert accept_response.status_code == 200
    copied_document_id = accept_response.json()["incoming"][0]["accepted_item_id"]
    assert copied_document_id is not None

    delete_response = alice_client.delete(f"/api/documents/{document_id}")
    assert delete_response.status_code == 204
    assert alice_client.get("/api/documents").json() == []

    bob_documents = bob_client.get("/api/documents").json()
    assert [document["id"] for document in bob_documents] == [copied_document_id]

    playback_response = bob_client.post(
        "/api/playback/sessions",
        json={"document_id": copied_document_id},
    )
    assert playback_response.status_code == 201
    assert playback_response.json()["current_chunk_text"] == SHORT_SAMPLE_TEXT


def test_shared_voice_preset_accept_copies_preset_and_audio(client_pair) -> None:
    alice_client, bob_client, bob_user_id = client_pair
    _make_friends(alice_client, bob_client, recipient_user_id=bob_user_id)

    alice_user_id = alice_client.get("/api/auth/me").json()["id"]
    preset_id = _create_voice_preset(alice_user_id)

    share_response = alice_client.post(
        "/api/shares",
        json={"recipient_user_id": bob_user_id, "item_type": "voice_preset", "item_id": preset_id},
    )
    assert share_response.status_code == 201

    share_id = bob_client.get("/api/shares").json()["incoming"][0]["id"]
    accept_response = bob_client.post(f"/api/shares/{share_id}/accept")
    assert accept_response.status_code == 200
    copied_preset_id = accept_response.json()["incoming"][0]["accepted_item_id"]
    assert copied_preset_id is not None

    db_module = import_module("app.db")
    voice_preset_model = import_module("app.models.voice_preset")
    user_storage = import_module("app.services.user_storage")
    with db_module.session_scope() as session:
        copied_preset = session.get(voice_preset_model.VoicePreset, copied_preset_id)
        assert copied_preset is not None
        assert copied_preset.owner_user_id == bob_user_id
        assert copied_preset.name == "Shared Narrator"
        assert copied_preset.transcript == "A calm, warm speaking sample."
        assert copied_preset.source_provider == "friend-share"
        assert "Shared by Alice" in (copied_preset.provenance_note or "")
        copied_reference = Path(copied_preset.reference_path)
        assert copied_reference.is_file()
        assert copied_reference.resolve().is_relative_to(
            user_storage.user_voices_root(bob_user_id).resolve()
        )


def test_declined_share_does_not_copy(client_pair) -> None:
    alice_client, bob_client, bob_user_id = client_pair
    _make_friends(alice_client, bob_client, recipient_user_id=bob_user_id)

    import_response = alice_client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    document_id = import_response.json()["id"]

    alice_client.post(
        "/api/shares",
        json={"recipient_user_id": bob_user_id, "item_type": "document", "item_id": document_id},
    )
    share_id = bob_client.get("/api/shares").json()["incoming"][0]["id"]

    decline_response = bob_client.post(f"/api/shares/{share_id}/decline")
    assert decline_response.status_code == 200
    assert decline_response.json()["incoming"][0]["status"] == "declined"
    assert bob_client.get("/api/documents").json() == []

    sender_cannot_respond = alice_client.post(f"/api/shares/{share_id}/accept")
    assert sender_cannot_respond.status_code == 404
