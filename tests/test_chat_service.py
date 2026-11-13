import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    """Sets up an isolated test database and Flask test client."""
    test_db = tmp_path / "test_chat.db"
    test_app = create_app(f"sqlite:///{test_db}")
    test_app.config["TESTING"] = True
    with test_app.test_client() as client:
        yield client


def _register_users(client, *usernames: str) -> None:
    for u in usernames:
        client.post("/auth/register", json={"username": u, "display_name": u.capitalize()})


def test_health_check(client):
    """Verify health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "chat-service"


def test_create_conversation_success(client):
    """Verify valid conversation creation with initial participants."""
    _register_users(client, "marcos", "profe")
    payload = {"title": "Team Alpha", "participants": ["marcos", "profe"]}
    response = client.post("/conversations", json=payload)

    assert response.status_code == 201
    data = response.get_json()
    assert data["status"] == "created"
    assert data["title"] == "Team Alpha"
    assert data["participants"] == ["marcos", "profe"]
    assert "conversation_id" in data


def test_create_conversation_validation_error(client):
    """Verify invalid payloads are rejected with 400 Bad Request."""
    # Missing participants
    res = client.post("/conversations", json={"title": "No participants"})
    assert res.status_code == 400

    # Empty participants list
    res = client.post("/conversations", json={"title": "Empty", "participants": []})
    assert res.status_code == 400


def test_create_conversation_unregistered_user_error(client):
    """Verify conversation creation fails if any participant is not registered."""
    _register_users(client, "marcos")
    res = client.post(
        "/conversations",
        json={"title": "Invalid Room", "participants": ["marcos", "unregistered_user"]},
    )
    assert res.status_code == 400
    assert "unregistered_user" in res.get_json()["error"]


def test_list_user_conversations(client):
    """Verify fetching conversation inbox for a specific user."""
    _register_users(client, "marcos", "profe", "lucas")
    # Create two conversations: one with marcos & profe, another with marcos & lucas
    client.post("/conversations", json={"title": "Conv 1", "participants": ["marcos", "profe"]})
    client.post("/conversations", json={"title": "Conv 2", "participants": ["marcos", "lucas"]})
    client.post("/conversations", json={"title": "Conv 3", "participants": ["lucas", "profe"]})

    # marcos should be in 2 conversations
    res = client.get("/users/marcos/conversations")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_conversations"] == 2
    titles = [c["title"] for c in data["conversations"]]
    assert "Conv 1" in titles
    assert "Conv 2" in titles

    # Unknown user should have 0 conversations
    res_unknown = client.get("/users/ghost/conversations")
    assert res_unknown.status_code == 200
    assert res_unknown.get_json()["total_conversations"] == 0


def test_add_participant(client):
    """Verify adding a new participant to an existing conversation."""
    _register_users(client, "marcos", "profe")
    res_create = client.post("/conversations", json={"title": "Room", "participants": ["marcos"]})
    conv_id = res_create.get_json()["conversation_id"]

    # Add new participant
    res_add = client.post(f"/conversations/{conv_id}/participants", json={"username": "profe"})
    assert res_add.status_code == 200
    assert res_add.get_json()["added_username"] == "profe"

    # Verify profe now has this conversation in their list
    res_inbox = client.get("/users/profe/conversations")
    assert res_inbox.get_json()["total_conversations"] == 1

    # Add to non-existent conversation returns 404
    res_not_found = client.post("/conversations/999/participants", json={"username": "anyone"})
    assert res_not_found.status_code == 404


def test_post_and_get_chat_messages(client):
    """Verify posting regular messages and reading conversation history."""
    _register_users(client, "marcos", "profe")
    res_create = client.post(
        "/conversations", json={"title": "Chat Room", "participants": ["marcos", "profe"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    # Post message from marcos
    res_msg1 = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "Hello professor!"},
    )
    assert res_msg1.status_code == 201
    msg1_data = res_msg1.get_json()
    assert msg1_data["type"] == "chat_message"
    assert msg1_data["sender"] == "marcos"
    assert msg1_data["content"] == "Hello professor!"

    # Post reply from profe
    res_msg2 = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "profe", "content": "Hello Marcos, good luck."},
    )
    assert res_msg2.status_code == 201

    # Retrieve messages
    res_history = client.get(f"/conversations/{conv_id}/messages")
    assert res_history.status_code == 200
    history_data = res_history.get_json()
    assert history_data["message_count"] == 2
    assert history_data["messages"][0]["content"] == "Hello professor!"
    assert history_data["messages"][1]["content"] == "Hello Marcos, good luck."


def test_post_message_forbidden_non_participant(client):
    """Verify non-participants cannot post messages into private conversations."""
    _register_users(client, "marcos", "profe")
    res_create = client.post(
        "/conversations", json={"title": "Private", "participants": ["marcos", "profe"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    res = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "intruder", "content": "Let me in!"},
    )
    assert res.status_code == 403
    assert "not a participant" in res.get_json()["error"]


def test_system_directive_help(client):
    """Verify /help returns directives without persisting a chat message."""
    _register_users(client, "marcos")
    res_create = client.post(
        "/conversations", json={"title": "Commands Room", "participants": ["marcos"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    res_cmd = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "/help"},
    )
    assert res_cmd.status_code == 200
    data = res_cmd.get_json()
    assert data["type"] == "system_directive"
    assert data["directive"] == "/help"
    assert len(data["available_directives"]) >= 4

    # Verify database message history remains completely empty
    res_history = client.get(f"/conversations/{conv_id}/messages")
    assert res_history.get_json()["message_count"] == 0


def test_system_directive_title(client):
    """Verify /title renames the conversation and is not stored as a message."""
    _register_users(client, "marcos")
    res_create = client.post(
        "/conversations", json={"title": "Old Title", "participants": ["marcos"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    res_cmd = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "/title Production Release"},
    )
    assert res_cmd.status_code == 200
    assert res_cmd.get_json()["directive"] == "/title"

    # Verify conversation title updated in GET
    res_history = client.get(f"/conversations/{conv_id}/messages")
    assert res_history.get_json()["title"] == "Production Release"
    assert res_history.get_json()["message_count"] == 0

    # Test missing title parameter
    res_err = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "/title"},
    )
    assert res_err.status_code == 400


def test_system_directive_members(client):
    """Verify /members lists all participants."""
    _register_users(client, "marcos", "profe")
    res_create = client.post(
        "/conversations", json={"title": "Team", "participants": ["marcos", "profe"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    res_cmd = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "/members"},
    )
    assert res_cmd.status_code == 200
    data = res_cmd.get_json()
    assert data["directive"] == "/members"
    assert data["total"] == 2
    usernames = [m["username"] for m in data["members"]]
    assert "marcos" in usernames
    assert "profe" in usernames


def test_system_directive_leave(client):
    """Verify /leave removes the participant so they can no longer post."""
    _register_users(client, "marcos", "profe")
    res_create = client.post(
        "/conversations", json={"title": "Leaving Room", "participants": ["marcos", "profe"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    # marcos leaves
    res_leave = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "/leave"},
    )
    assert res_leave.status_code == 200

    # marcos attempts to post again -> 403 Forbidden
    res_blocked = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "I am back?"},
    )
    assert res_blocked.status_code == 403


def test_system_directive_clear(client):
    """Verify /clear wipes message history while keeping conversation intact."""
    _register_users(client, "marcos")
    res_create = client.post(
        "/conversations", json={"title": "Clear Room", "participants": ["marcos"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    # Post 2 regular messages
    client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "Msg 1"},
    )
    client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "Msg 2"},
    )

    # Check messages exist
    res_check = client.get(f"/conversations/{conv_id}/messages")
    assert res_check.get_json()["message_count"] == 2

    # Execute /clear
    res_clear = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "/clear"},
    )
    assert res_clear.status_code == 200

    # History is now 0
    res_empty = client.get(f"/conversations/{conv_id}/messages")
    assert res_empty.get_json()["message_count"] == 0


def test_system_directive_unknown(client):
    """Verify unrecognized directives return 400 with a guiding error."""
    _register_users(client, "marcos")
    res_create = client.post(
        "/conversations", json={"title": "Directives", "participants": ["marcos"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    res = client.post(
        f"/conversations/{conv_id}/messages",
        json={"sender": "marcos", "content": "/destroy_database"},
    )
    assert res.status_code == 400
    assert "Unknown directive" in res.get_json()["error"]


def test_user_registration_and_retrieval(client):
    """Verify user registration, profile query, and list of users."""
    # 1. Register new user
    res = client.post(
        "/auth/register",
        json={"username": "marcos", "display_name": "Marcos Di Matteo"},
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "created"
    assert data["user"]["username"] == "marcos"
    assert data["user"]["display_name"] == "Marcos Di Matteo"

    # 2. Register same user again (idempotent)
    res_dup = client.post(
        "/auth/register",
        json={"username": "marcos", "display_name": "Different Name"},
    )
    assert res_dup.status_code == 200
    assert res_dup.get_json()["status"] == "already_registered"

    # 3. Missing username validation error
    res_err = client.post("/auth/register", json={})
    assert res_err.status_code == 400

    # 4. Register second user
    client.post(
        "/auth/register",
        json={"username": "profe", "display_name": "Profesor Linux"},
    )

    # 5. List all registered users
    res_list = client.get("/users")
    assert res_list.status_code == 200
    list_data = res_list.get_json()
    assert list_data["total_users"] == 2
    usernames = [u["username"] for u in list_data["users"]]
    assert "marcos" in usernames
    assert "profe" in usernames

    # 6. Get single user profile
    res_single = client.get("/users/marcos")
    assert res_single.status_code == 200
    assert res_single.get_json()["user"]["display_name"] == "Marcos Di Matteo"

    # 7. Non-existent user profile returns 404
    res_404 = client.get("/users/ghost_user")
    assert res_404.status_code == 404


def test_websocket_room_broker_broadcast(client):
    """Verify posting a message broadcasts JSON to subscribed WebSocket clients and prunes dead ones."""
    import json

    from chat.ws import room_broker

    class FakeWS:
        def __init__(self, fail: bool = False) -> None:
            self.sent: list[str] = []
            self.fail = fail

        def send(self, data: str) -> None:
            if self.fail:
                raise ConnectionError("socket closed")
            self.sent.append(data)

    _register_users(client, "marcos")
    res_create = client.post(
        "/conversations", json={"title": "WS Room", "participants": ["marcos"]}
    )
    conv_id = res_create.get_json()["conversation_id"]

    live_ws = FakeWS()
    dead_ws = FakeWS(fail=True)
    room_broker.subscribe(conv_id, live_ws)
    room_broker.subscribe(conv_id, dead_ws)

    try:
        res_msg = client.post(
            f"/conversations/{conv_id}/messages",
            json={"sender": "marcos", "content": "Realtime hello"},
        )
        assert res_msg.status_code == 201
        assert len(live_ws.sent) == 1
        payload = json.loads(live_ws.sent[0])
        assert payload["type"] == "chat_message"
        assert payload["sender"] == "marcos"
        assert payload["content"] == "Realtime hello"
    finally:
        room_broker.unsubscribe(conv_id, live_ws)
        room_broker.unsubscribe(conv_id, dead_ws)
