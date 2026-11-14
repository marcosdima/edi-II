from flask import Blueprint, jsonify, request

from .directives import execute_system_directive
from .services import (
    ConversationService,
    MessageService,
    ParticipantService,
    UserService,
)
from .ws import room_broker

chat_bp = Blueprint("chat", __name__)


def get_proxy_metadata():
    """Extracts reverse proxy headers sent by Nginx for auditing demonstration."""
    return {
        "client_ip": request.headers.get("X-Real-IP", request.remote_addr),
        "forwarded_proto": request.headers.get("X-Forwarded-Proto", "http"),
        "country": request.headers.get("X-Country-Code", "UNKNOWN"),
    }


@chat_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker and Nginx reverse proxy."""
    return jsonify({"service": "chat-service", "status": "healthy"}), 200


def _json_dict() -> dict:
    """Return parsed JSON body as a dict, or empty dict if missing/invalid."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _clean_str(value: object) -> str:
    """Safely strip a string value, returning empty string for non-strings."""
    return value.strip() if isinstance(value, str) else ""


# -----------------------------------------------------------------------------
# User Identity & Authentication Endpoints
# -----------------------------------------------------------------------------


@chat_bp.route("/auth/register", methods=["POST"])
def register_user():
    """
    Registers a new user in the system.
    Payload: {"username": "marcos", "display_name": "Marcos Di Matteo"}
    """
    data = _json_dict()
    username = _clean_str(data.get("username"))
    display_name = _clean_str(data.get("display_name")) or None

    if not username:
        return jsonify({"error": "'username' is required."}), 400

    user, was_created = UserService.register(username=username, display_name=display_name)

    status_code = 201 if was_created else 200
    return (
        jsonify(
            {
                "status": "created" if was_created else "already_registered",
                "user": user.to_dict(),
                "proxy_metadata": get_proxy_metadata(),
            }
        ),
        status_code,
    )


@chat_bp.route("/users", methods=["GET"])
def list_users():
    """Returns all registered users in the system."""
    users = UserService.list_users()
    return (
        jsonify(
            {
                "total_users": len(users),
                "users": [u.to_dict() for u in users],
                "proxy_metadata": get_proxy_metadata(),
            }
        ),
        200,
    )


@chat_bp.route("/users/<username>", methods=["GET"])
def get_user_profile(username: str):
    """Retrieves profile details for a given username."""
    user = UserService.get_by_username(username)
    if not user:
        return jsonify({"error": f"User '{username}' not found."}), 404

    return (
        jsonify({"user": user.to_dict(), "proxy_metadata": get_proxy_metadata()}),
        200,
    )


# -----------------------------------------------------------------------------
# Conversation & Messaging Endpoints
# -----------------------------------------------------------------------------


@chat_bp.route("/conversations", methods=["POST"])
def create_conversation():
    """
    Creates a new conversation with initial participants.
    Payload: {"title": "Team Chat", "participants": ["marcos", "profe"]}
    """
    data = _json_dict()
    title = _clean_str(data.get("title"))
    participants = data.get("participants", [])

    if not isinstance(participants, list) or len(participants) < 1:
        return (
            jsonify({"error": "'participants' must be a list containing at least 1 username."}),
            400,
        )

    clean_participants = sorted(
        {_clean_str(p).lower() for p in participants if isinstance(p, str) and p.strip()}
    )
    if not clean_participants:
        return jsonify({"error": "At least 1 valid username is required."}), 400

    try:
        conversation = ConversationService.create(title=title, participants=clean_participants)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    return (
        jsonify(
            {
                "status": "created",
                "conversation_id": conversation.id,
                "title": conversation.title,
                "participants": clean_participants,
                "proxy_metadata": get_proxy_metadata(),
            }
        ),
        201,
    )


@chat_bp.route("/users/<username>/conversations", methods=["GET"])
def list_user_conversations(username: str):
    """Returns all conversations a user is part of (user's inbox)."""
    clean_user = username.strip().lower()

    user_participations = ParticipantService.list_user_participations(clean_user)

    conversations = [
        {
            "id": p.conversation.id,
            "title": p.conversation.title,
            "created_at": p.conversation.created_at.isoformat(),
            "joined_at": p.joined_at.isoformat(),
            "last_messages": [
                {
                    "sender": m.sender,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in MessageService.get_last_messages(p.conversation.id, limit=3)
            ],
        }
        for p in user_participations
    ]

    return (
        jsonify(
            {
                "username": clean_user,
                "total_conversations": len(conversations),
                "conversations": conversations,
                "proxy_metadata": get_proxy_metadata(),
            }
        ),
        200,
    )


@chat_bp.route("/conversations/<int:conv_id>/participants", methods=["POST"])
def add_participant(conv_id: int):
    """Adds a participant to an existing conversation."""
    data = _json_dict()
    username = _clean_str(data.get("username")).lower()

    if not username:
        return jsonify({"error": "'username' is required."}), 400

    if not ConversationService.get_by_id(conv_id):
        return jsonify({"error": f"Conversation {conv_id} not found."}), 404

    ParticipantService.add_participant(conv_id=conv_id, username=username)

    return (
        jsonify(
            {
                "status": "success",
                "conversation_id": conv_id,
                "added_username": username,
            }
        ),
        200,
    )


@chat_bp.route("/conversations/<int:conv_id>/messages", methods=["GET"])
def get_conversation_messages(conv_id: int):
    """Retrieves all chat messages for a conversation in chronological order."""
    try:
        raw_limit = int(request.args.get("limit", 50))
    except (ValueError, TypeError):
        return jsonify({"error": "'limit' must be a valid integer."}), 400
    limit = max(1, min(raw_limit, 100))

    conversation = ConversationService.get_by_id(conv_id)
    if not conversation:
        return jsonify({"error": f"Conversation {conv_id} not found."}), 404

    messages = MessageService.get_messages(conv_id=conv_id, limit=limit)

    return (
        jsonify(
            {
                "conversation_id": conversation.id,
                "title": conversation.title,
                "message_count": len(messages),
                "messages": [m.to_dict() for m in messages],
                "proxy_metadata": get_proxy_metadata(),
            }
        ),
        200,
    )


@chat_bp.route("/conversations/<int:conv_id>/messages", methods=["POST"])
def post_message(conv_id: int):
    """
    Handles posting to a conversation.
    - If content begins with '/', it executes as a system directive and is NOT saved.
    - Otherwise, saves as a persistent chat message.
    Payload: {"sender": "marcos", "content": "Hello world" | "/command"}
    """
    data = _json_dict()
    sender = _clean_str(data.get("sender")).lower()
    content = _clean_str(data.get("content"))

    if not sender or not content:
        return jsonify({"error": "'sender' and 'content' are required fields."}), 400

    if not ConversationService.get_by_id(conv_id):
        return jsonify({"error": f"Conversation {conv_id} not found."}), 404

    if not ParticipantService.is_participant(conv_id=conv_id, username=sender):
        return (
            jsonify(
                {"error": f"Sender '{sender}' is not a participant in conversation {conv_id}."}
            ),
            403,
        )

    # Intercept system directive (will NOT be stored in messages)
    if content.startswith("/"):
        return execute_system_directive(conv_id, sender, content)

    # Persist chat message via service
    message = MessageService.create_message(conv_id=conv_id, sender=sender, content=content)
    event_payload = {
        "type": "chat_message",
        "id": message.id,
        "conversation_id": conv_id,
        "sender": sender,
        "content": content,
        "created_at": message.created_at.isoformat(),
    }
    room_broker.broadcast(conv_id, event_payload)

    return (
        jsonify(
            {
                **event_payload,
                "proxy_metadata": get_proxy_metadata(),
            }
        ),
        201,
    )
