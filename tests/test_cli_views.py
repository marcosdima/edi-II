from unittest.mock import MagicMock, patch

import requests

from cli.views.ai_view import AIView
from cli.views.base import BaseView
from cli.views.chat_view import ChatView, ConversationView


def test_base_view_navigation():
    """Verify BaseView command handling for back, exit, EOF."""
    view = BaseView()
    assert view.do_back("") is True
    assert view.do_exit("") is True
    assert view.do_quit("") is True
    assert view.do_EOF("") is True
    assert view.emptyline() is False


@patch("cli.views.base.requests.get")
@patch("cli.views.base.requests.post")
def test_base_view_api_requests(mock_post, mock_get):
    """Verify BaseView handles HTTP success and request exceptions gracefully."""
    mock_get_res = MagicMock()
    mock_get_res.status_code = 200
    mock_get.return_value = mock_get_res

    view = BaseView()
    res = view.api_get("/test")
    assert res is not None
    assert res.status_code == 200

    mock_get.side_effect = requests.RequestException("Network down")
    assert view.api_get("/test") is None

    mock_post_res = MagicMock()
    mock_post_res.status_code = 201
    mock_post.return_value = mock_post_res

    res_p = view.api_post("/test", {"data": 123})
    assert res_p is not None
    assert res_p.status_code == 201

    mock_post.side_effect = requests.RequestException("Timeout")
    assert view.api_post("/test", {}) is None


@patch.object(ChatView, "api_post")
@patch.object(ChatView, "api_get")
def test_chat_view_user_management(mock_get, mock_post, capsys):
    """Verify ChatView user registration, login, and listing."""
    mock_post.return_value = MagicMock(
        status_code=200, json=lambda: {"user": {"display_name": "Marcos"}}
    )
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"users": [{"username": "marcos", "display_name": "Marcos"}]},
    )

    cv = ChatView(default_user="marcos")
    assert cv.current_user == "marcos"

    cv.do_whoami("")
    captured = capsys.readouterr().out
    assert "marcos" in captured

    cv.do_login("lucas")
    assert cv.current_user == "lucas"

    cv.do_users("")
    captured = capsys.readouterr().out
    assert "Registered Users" in captured


@patch.object(ChatView, "api_post")
@patch.object(ChatView, "api_get")
def test_chat_view_inbox_and_new(mock_get, mock_post, capsys):
    """Verify ChatView inbox listing and conversation creation."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "conversations": [{"id": 1, "title": "General", "created_at": "2026-11-12T10:00:00"}]
        },
    )
    cv = ChatView(default_user="marcos")
    cv.do_inbox("")
    captured = capsys.readouterr().out
    assert "General" in captured

    mock_post.return_value = MagicMock(
        status_code=201,
        json=lambda: {"conversation_id": 2, "participants": ["marcos", "profe"]},
    )
    with patch.object(cv, "do_open") as mock_open:
        cv.do_new("Exam Prep profe")
        mock_open.assert_called_once_with("2")


@patch.object(ConversationView, "api_get")
@patch.object(ConversationView, "api_post")
def test_conversation_view_messaging_and_directives(mock_post, mock_get, capsys):
    """Verify sending regular messages and system directives inside a conversation."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "messages": [
                {
                    "id": 1,
                    "sender": "marcos",
                    "content": "Hello",
                    "created_at": "2026-11-12T10:00:00",
                }
            ]
        },
    )

    conv = ConversationView(conv_id=1, title="Test Chat", current_user="marcos")
    msgs = conv.fetch_messages()
    assert len(msgs) == 1

    # Normal message
    mock_post.return_value = MagicMock(
        status_code=201,
        json=lambda: {
            "id": 2,
            "sender": "marcos",
            "content": "Hi",
            "created_at": "2026-11-12T10:01:00",
        },
    )
    conv.default("Hi")
    captured = capsys.readouterr().out
    assert "marcos" in captured
    assert "Hi" in captured

    # System directive /title
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "type": "system_directive",
            "directive": "/title",
            "message": "Title updated to NewTitle.",
        },
    )
    conv.default("/title NewTitle")
    assert conv.title == "NewTitle"

    # System directive /help
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "type": "system_directive",
            "directive": "/help",
            "available_directives": [
                {"command": "/title <new_title>", "description": "Rename conversation"}
            ],
        },
    )
    conv.default("/help")
    captured = capsys.readouterr().out
    assert "Available System Directives" in captured


@patch.object(AIView, "api_get")
@patch.object(AIView, "api_post")
def test_ai_view_workflow(mock_post, mock_get, capsys):
    """Verify AIView configuration fetching, model override, and completion generation."""
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "configuration": {
                "provider": "groq",
                "default_model": "llama-3.3-70b-versatile",
                "api_key_configured": True,
                "offline_fallback_enabled": True,
                "endpoint": "https://api.groq.com",
            },
            "proxy_metadata": {
                "client_ip": "127.0.0.1",
                "forwarded_proto": "https",
                "country": "AR",
            },
        },
    )

    ai = AIView()
    ai.preloop()
    assert ai.provider == "groq"
    assert ai.default_model == "llama-3.3-70b-versatile"

    # Model switching
    ai.do_model("mixtral-8x7b")
    assert ai.get_active_model() == "mixtral-8x7b"
    ai.do_model("reset")
    assert ai.get_active_model() == "llama-3.3-70b-versatile"

    # Temperature configuration
    ai.do_temp("0.2")
    assert ai.temperature == 0.2
    ai.do_temp("99")  # Invalid
    assert ai.temperature == 0.2

    # Info display
    ai.do_info("")
    captured = capsys.readouterr().out
    assert "AI Service Configuration" in captured
    assert "Reverse Proxy Metadata" in captured

    # Prompt generation
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "status": "success",
            "response": {
                "reply": "A reverse proxy routes requests to backends.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "is_fallback": False,
                "latency_ms": 120.5,
            },
        },
    )
    ai.default("What is a reverse proxy?")
    captured = capsys.readouterr().out
    assert "A reverse proxy routes requests to backends." in captured
