from enum import StrEnum
from typing import Any

from flask import Response, jsonify

from .services import ConversationService, ParticipantService


class DirectiveType(StrEnum):
    TITLE = "/title"
    MEMBERS = "/members"
    LEAVE = "/leave"
    CLEAR = "/clear"
    HELP = "/help"


def _directive_success(directive: DirectiveType, payload: dict[str, Any]) -> tuple[Response, int]:
    """Standardizes successful system directive responses."""
    return (
        jsonify(
            {
                "type": "system_directive",
                "directive": directive.value,
                "status": "success",
                **payload,
            }
        ),
        200,
    )


def _directive_error(message: str, status_code: int = 400) -> tuple[Response, int]:
    """Standardizes error responses for system directives."""
    return (
        jsonify(
            {
                "type": "system_directive",
                "error": message,
            }
        ),
        status_code,
    )


def execute_system_directive(conv_id: int, sender: str, raw_command: str) -> tuple[Response, int]:
    """
    Executes a system directive instead of storing a message.
    Directives modify conversation state or return operational metadata.
    """
    parts = raw_command.strip().split(maxsplit=1)
    raw_cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    conversation = ConversationService.get_by_id(conv_id)
    if not conversation:
        return jsonify({"error": f"Conversation {conv_id} not found."}), 404

    try:
        directive = DirectiveType(raw_cmd)
    except ValueError:
        return _directive_error(
            f"Unknown directive '{raw_cmd}'. Type /help for available commands."
        )

    match directive:
        case DirectiveType.TITLE:
            if not arg:
                return _directive_error("Usage: /title <new title>")
            ConversationService.update_title(conv_id, arg)
            return _directive_success(
                directive, {"message": f"Conversation title updated to '{arg}'"}
            )

        case DirectiveType.MEMBERS:
            members = [p.to_dict() for p in ParticipantService.get_participants(conv_id)]
            return _directive_success(directive, {"total": len(members), "members": members})

        case DirectiveType.LEAVE:
            ParticipantService.remove_participant(conv_id, sender)
            return _directive_success(
                directive,
                {"message": f"User '{sender}' has left conversation {conv_id}."},
            )

        case DirectiveType.CLEAR:
            ConversationService.clear_messages(conv_id)
            return _directive_success(
                directive,
                {"message": f"Message history cleared for conversation {conv_id}."},
            )

        case DirectiveType.HELP:
            available = [
                {"command": "/title <name>", "description": "Rename the conversation"},
                {
                    "command": "/members",
                    "description": "List all current conversation participants",
                },
                {"command": "/leave", "description": "Leave this conversation"},
                {
                    "command": "/clear",
                    "description": "Wipe message history in this conversation",
                },
                {"command": "/help", "description": "List available directives"},
            ]
            return _directive_success(directive, {"available_directives": available})
