import asyncio
from unittest.mock import MagicMock, patch

from textual.app import App
from textual.widgets import Input

from cli.tui.ai_screen import AIScreen
from cli.tui.app import ProxyApp
from cli.tui.chat_screen import ChatScreen
from cli.tui.inbox_screen import InboxScreen
from cli.tui.main_screen import MainScreen
from cli.tui.theme import format_card, format_chat_message, format_dot_matrix, format_system_event


def test_theme_formatting():
    """Verify formatters generate correct monochrome markup strings."""
    # Current user
    msg_me = format_chat_message(
        sender="marcos",
        content="Testing message",
        created_at="2026-11-12T12:00:00",
        current_user="marcos",
    )
    assert "marcos" in msg_me
    assert "Testing message" in msg_me
    assert "#ffffff" in msg_me

    # Other user
    msg_other = format_chat_message(
        sender="profe",
        content="Other user message",
        created_at="2026-11-12T12:01:00",
        current_user="marcos",
    )
    assert "profe" in msg_other
    assert "#a3a3a3" in msg_other

    # System event
    sys_event = format_system_event("Title updated")
    assert "Title updated" in sys_event
    assert "#737373" in sys_event

    # Card
    card = format_card("CHAT SYSTEM", "[1]", "SQLite relational store")
    assert "CHAT SYSTEM" in card
    assert "[1]" in card

    # Dot Matrix
    dots_single = format_dot_matrix(0, 1)
    assert "●" in dots_single

    dots_multi = format_dot_matrix(1, 3)
    assert "PAGE 2/3" in dots_multi
    assert "●" in dots_multi
    assert "○" in dots_multi


def test_chat_screen_lifecycle_and_messaging():
    """Verify ChatScreen message rendering and submission."""

    async def _test():
        with (
            patch.object(ChatScreen, "api_get") as mock_get,
            patch.object(ChatScreen, "api_post") as mock_post,
        ):
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "title": "Exam Prep",
                    "messages": [
                        {
                            "id": 1,
                            "sender": "profe",
                            "content": "Welcome",
                            "created_at": "2026-11-12T10:00:00",
                        }
                    ],
                },
            )

            mock_post.return_value = MagicMock(
                status_code=201,
                json=lambda: {
                    "id": 2,
                    "sender": "marcos",
                    "content": "Hi",
                    "created_at": "2026-11-12T10:01:00",
                },
            )

            screen = ChatScreen(conv_id=5, title="Exam Prep", current_user="marcos")
            app: App[None] = App()

            async with app.run_test() as pilot:
                await app.push_screen(screen)
                assert screen.conv_title == "Exam Prep"
                assert screen.last_seen_id == 1

                inp = screen.query_one(Input)
                inp.value = "Hi"
                await pilot.press("enter")
                assert screen.last_seen_id == 2

    asyncio.run(_test())


def test_proxy_app_main_navigation():
    """Verify ProxyApp loads MainScreen and navigates to screens via input."""

    async def _test():
        with (
            patch("requests.get") as mock_get,
            patch("requests.post") as mock_post,
        ):
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {"conversations": [], "configuration": {}},
            )
            mock_post.return_value = MagicMock(status_code=200, json=lambda: {})

            app = ProxyApp()
            async with app.run_test() as pilot:
                assert isinstance(app.screen, MainScreen)

                # Test navigating to Chat
                main_inp = app.screen.query_one(Input)
                main_inp.value = "1"
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, InboxScreen)

                # Back to MainScreen
                await pilot.press("escape")
                await pilot.pause()
                assert isinstance(app.screen, MainScreen)

                # Test navigating to AI
                main_inp = app.screen.query_one(Input)
                main_inp.value = "2"
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, AIScreen)

                # Back to MainScreen
                await pilot.press("escape")
                await pilot.pause()
                assert isinstance(app.screen, MainScreen)

    asyncio.run(_test())


def test_inbox_screen_actions():
    """Verify InboxScreen lists conversations, renders messages, and handles pagination."""

    async def _test():
        with (
            patch.object(InboxScreen, "api_get") as mock_get,
            patch.object(InboxScreen, "api_post") as mock_post,
        ):
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "conversations": [
                        {
                            "id": 1,
                            "title": "Project",
                            "created_at": "2026-11-12T00:00:00",
                            "last_messages": [
                                {
                                    "sender": "profe",
                                    "content": "Hello class",
                                    "created_at": "2026-11-12T10:00:00",
                                }
                            ],
                        },
                        {"id": 2, "title": "Lab", "created_at": "2026-11-12T00:00:00"},
                        {"id": 3, "title": "Exam", "created_at": "2026-11-12T00:00:00"},
                        {"id": 4, "title": "Final", "created_at": "2026-11-12T00:00:00"},
                    ]
                },
            )
            mock_post.return_value = MagicMock(status_code=200, json=lambda: {})

            screen = InboxScreen(current_user="marcos")
            app: App[None] = App()
            async with app.run_test() as pilot:
                await app.push_screen(screen)
                grid = screen.query_one("#conversations_grid")
                assert grid is not None
                dots = screen.query_one("#pagination_dots")
                assert dots is not None

                # 4 convs + 1 (Card 0) = 5 items => 2 pages (3 items/page)
                assert screen.total_pages == 2
                assert screen.current_page == 0

                # Navigate next page
                screen.action_next_page()
                assert screen.current_page == 1

                # Navigate prev page
                screen.action_prev_page()
                assert screen.current_page == 0

                # Test typing users
                mock_get.return_value = MagicMock(
                    status_code=200,
                    json=lambda: {"users": [{"username": "marcos", "display_name": "Marcos"}]},
                )
                inp = screen.query_one(Input)
                inp.value = "users"
                await pilot.press("enter")

                # Test switching user with /login
                inp.value = "/login profe"
                await pilot.press("enter")
                assert screen.current_user == "profe"

    asyncio.run(_test())


def test_main_screen_cards_and_ai_slash_commands():
    """Verify MainScreen renders 6 MenuCards, slash OptionList selector, and AIScreen /help."""
    from textual.widgets import OptionList

    from cli.tui.main_screen import MenuCard

    async def _test():
        with (
            patch.object(AIScreen, "api_get") as mock_ai_get,
            patch.object(AIScreen, "api_post") as mock_ai_post,
        ):
            mock_ai_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "configuration": {
                        "provider": "groq",
                        "default_model": "llama-3.3-70b",
                        "api_key_configured": True,
                    }
                },
            )

            app = ProxyApp()
            async with app.run_test() as pilot:
                assert isinstance(app.screen, MainScreen)
                cards = app.screen.query(MenuCard)
                assert len(cards) == 6

                # Typing '/' shows the OptionList command selector popup
                main_inp = app.screen.query_one(Input)
                palette = app.screen.query_one("#command_palette", OptionList)
                assert palette.display is False
                main_inp.value = "/"
                await pilot.pause()
                assert palette.display is True
                assert palette.option_count == len(MainScreen.SCREEN_COMMANDS)

                main_inp.value = "/au"
                await pilot.pause()
                assert palette.display is True
                await pilot.press("tab")
                await pilot.pause()
                assert main_inp.value == "/audit"
                assert palette.display is False

                main_inp.value = ""
                await pilot.pause()
                assert palette.display is False

                # Navigate to AI Screen
                main_inp.value = "2"
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, AIScreen)

                # Typing /help must NOT trigger api_post
                ai_inp = app.screen.query_one(Input)
                ai_inp.value = "/help"
                await pilot.press("enter")
                await pilot.pause()
                mock_ai_post.assert_not_called()

                # Typing unknown slash command must NOT trigger api_post
                ai_inp.value = "/unknown"
                await pilot.press("enter")
                await pilot.pause()
                mock_ai_post.assert_not_called()

    asyncio.run(_test())
