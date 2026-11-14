from typing import Any

import requests
from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RichLog, Static

from ..client import ProxyClient
from ..config import ProxyConfig, get_proxy_config, parse_new_conversation_args
from .base_screen import BaseTUIScreen, CommandSpec
from .chat_screen import ChatScreen
from .theme import (
    COLOR_DIM,
    COLOR_FOREGROUND,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_RULE,
    format_dot_matrix,
    format_message_preview,
    format_system_event,
)


class UserChip(Static):
    """Clickable rectangular chip representing a user in the conversation creator."""

    def __init__(
        self,
        username: str,
        *,
        selected: bool = False,
        locked: bool = False,
        id: str | None = None,
    ) -> None:
        self.username = username
        self.selected = selected or locked
        self.locked = locked
        classes = (
            "user-chip locked" if locked else ("user-chip selected" if selected else "user-chip")
        )
        super().__init__(self._render_label(), classes=classes, id=id)

    def _render_label(self) -> str:
        if self.locked:
            return f"● Me ({escape(self.username)})"
        prefix = "✓" if self.selected else "+"
        return f"{prefix} {escape(self.username)}"

    def on_click(self) -> None:
        if self.locked:
            return
        self.selected = not self.selected
        self.set_class(self.selected, "selected")
        self.update(self._render_label())


class NewConversationModal(ModalScreen[tuple[str, list[str]] | None]):
    """Minimalist modal dialog to create a new chat conversation with user chips."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, current_user: str, config: ProxyConfig | None = None) -> None:
        super().__init__()
        self.current_user = current_user
        self.config = config or get_proxy_config()
        self.client = ProxyClient(self.config)

    def api_get(self, endpoint: str, timeout: int = 8) -> requests.Response | None:
        """Fetch helper delegating to ProxyClient (easy to mock in tests)."""
        return self.client.get(endpoint, timeout=timeout)

    def compose(self) -> ComposeResult:
        with Vertical(id="new_conv_dialog"):
            yield Label("NEW CONVERSATION", classes="modal-title")
            yield Label("Room title (optional)", classes="modal-label")
            yield Input(
                placeholder="e.g. Proyecto Final (blank = Conver #ID)",
                classes="tui-input",
                id="modal_title",
            )
            yield Label("Participants (click to select)", classes="modal-label")
            with Grid(id="user_chips_grid"):
                yield UserChip(self.current_user, selected=True, locked=True, id="chip_me")
            yield Label("Loading users...", id="modal_users_status", classes="modal-hint")
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="btn_cancel")
                yield Button("Create", id="btn_create", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#modal_title", Input).focus()
        self._load_users_worker()

    @work(thread=True)
    def _load_users_worker(self) -> None:
        res = self.api_get("/api/chat/users")
        usernames: list[str] = []
        ok = False
        if res and res.status_code == 200:
            ok = True
            users = self.client.safe_json(res).get("users", [])
            usernames = [
                str(u.get("username", "")).strip().lower()
                for u in users
                if u.get("username") and str(u.get("username")).strip().lower() != self.current_user
            ]
        self.app.call_from_thread(self._populate_user_chips, usernames, ok)

    def _populate_user_chips(self, usernames: list[str], ok: bool) -> None:
        grid = self.query_one("#user_chips_grid", Grid)
        status = self.query_one("#modal_users_status", Label)
        for uname in usernames:
            grid.mount(UserChip(uname, id=f"chip_{uname}"))
        if not ok:
            status.update("Could not load other users (creating solo room).")
        elif not usernames:
            status.update("No other registered users yet.")
        else:
            status.update(f"{len(usernames)} other user(s) available.")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        title = self.query_one("#modal_title", Input).value.strip()
        participants = [chip.username for chip in self.query(UserChip) if chip.selected]
        self.dismiss((title, participants))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "modal_title":
            self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_create":
            self._submit()
        else:
            self.dismiss(None)


class ConversationCard(Static):
    """Clickable card representing a conversation or new room."""

    def __init__(self, conv_id: int, content: str, classes: str = "conv-card") -> None:
        super().__init__(content, classes=classes)
        self.conv_id = conv_id

    def on_click(self) -> None:
        """Handle mouse click on the conversation card."""
        screen = self.screen
        if isinstance(screen, InboxScreen):
            screen.select_conversation(self.conv_id)


class InboxScreen(BaseTUIScreen):
    """Inbox screen with spacious rectangular cards in a horizontal dot-matrix carousel."""

    SCREEN_COMMANDS = [
        CommandSpec("/help", "Show available commands", aliases=("help", "?")),
        CommandSpec("/register", "Create a new user account", args="<username> [name]"),
        CommandSpec("/login", "Switch active user (auto-creates if new)", args="<username>"),
        CommandSpec("/new", "Create new chat room", args='"Title" u1,u2'),
        CommandSpec("/users", "List registered users on server", aliases=("users",)),
        CommandSpec("/refresh", "Reload conversations", aliases=("refresh", "poll")),
        CommandSpec("/next", "Next page in carousel", aliases=("next", "n")),
        CommandSpec("/prev", "Previous page in carousel", aliases=("prev", "p")),
        CommandSpec("/back", "Return to main menu", aliases=("back", "exit", "quit")),
    ]

    BINDINGS = [
        Binding("pageup", "prev_page", "Prev Page", show=False),
        Binding("pagedown", "next_page", "Next Page", show=False),
        Binding("ctrl+left", "prev_page", "Prev Page", show=False),
        Binding("ctrl+right", "next_page", "Next Page", show=False),
        Binding("left", "prev_page", "Prev Page", show=False),
        Binding("right", "next_page", "Next Page", show=False),
        Binding("ctrl+r", "refresh", "Refresh", show=False),
        Binding("escape", "exit_inbox", "Back", show=False),
    ]

    ITEMS_PER_PAGE = 3

    def __init__(self, current_user: str = "marcos", config: ProxyConfig | None = None) -> None:
        super().__init__(config=config)
        self.current_user = current_user.strip().lower()
        self.cached_conversations: list[dict[str, Any]] = []
        self.current_page = 0
        self.total_pages = 1

    def compose(self) -> ComposeResult:
        """Compose layout: Header, Cards Grid, Dot Matrix Bar, Feedback Area, Bottom Panel."""
        yield self.compose_header(
            "CONVERSATION SELECTOR",
            f"user: {self.current_user}",
            meta_id="inbox_user_meta",
        )
        yield Grid(id="conversations_grid")
        yield Label("", id="pagination_dots")
        with Vertical(id="inbox_log_container"):
            yield RichLog(
                classes="tui-log",
                id="inbox_log",
                wrap=True,
                min_width=20,
                highlight=False,
                markup=True,
                auto_scroll=True,
            )
        yield self.compose_bottom_panel(
            placeholder="Enter conversation ID (e.g. 12, 0 for new), or: /login <user>, users...",
            status_text=" [0] + New Room  •  Type ID or click card  •  [PgUp/PgDn] Page  •  [Ctrl+R] Refresh  •  [Esc] Back",
            input_id="inbox_input",
            status_id="inbox_status",
        )

    def on_mount(self) -> None:
        """Fetch inbox and focus input on startup."""
        self.query_one(Input).focus()
        self._sync_user_from_app()
        self.action_refresh()

    def on_screen_resume(self) -> None:
        """Refresh conversations and active user when returning from a chat room."""
        self.query_one(Input).focus()
        self._sync_user_from_app()
        self.action_refresh()

    def _sync_user_from_app(self) -> None:
        app_user = getattr(self.app, "current_user", None)
        if app_user:
            self.current_user = str(app_user)
            self.query_one("#inbox_user_meta", Label).update(f"user: {self.current_user}")

    def _ensure_user(self, username: str) -> None:
        self.api_post(
            "/api/chat/auth/register",
            {"username": username, "display_name": username.capitalize()},
        )

    @work(thread=True)
    def action_refresh(self) -> None:
        """Fetch conversations from server in background worker and update UI."""
        self._ensure_user(self.current_user)
        res = self.api_get(f"/api/chat/users/{self.current_user}/conversations")
        if not res or res.status_code != 200:
            self.app.call_from_thread(self._handle_refresh_error)
            return

        data = self.client.safe_json(res)
        conversations = data.get("conversations", [])
        self.app.call_from_thread(self._apply_conversations, conversations)

    def _handle_refresh_error(self) -> None:
        grid = self.query_one("#conversations_grid", Grid)
        grid.remove_children()
        grid.mount(
            Static(f"[dim {COLOR_MUTED}]Unable to reach Reverse Proxy.[/]", classes="conv-card")
        )

    def _apply_conversations(self, conversations: list[dict[str, Any]]) -> None:
        self.cached_conversations = conversations
        total_items = 1 + len(self.cached_conversations)  # Card 0 + conversations
        self.total_pages = max(1, (total_items + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        self.current_page = min(self.current_page, self.total_pages - 1)
        self.render_grid()

    def render_grid(self) -> None:
        """Render spacious cards for current page and update dot matrix indicator."""
        grid = self.query_one("#conversations_grid", Grid)
        grid.remove_children()

        all_cards: list[ConversationCard] = []

        card_0_content = (
            f"[bold {COLOR_PRIMARY}][ 0 ][/]\n"
            f"[bold {COLOR_FOREGROUND}]New Room[/]\n\n"
            f"[bold {COLOR_PRIMARY}]+[/]\n\n"
            f"[dim {COLOR_MUTED}]Click or type '0'[/]\n"
            f"[dim {COLOR_DIM}]to create a room[/]"
        )
        all_cards.append(
            ConversationCard(conv_id=0, content=card_0_content, classes="conv-card card-new")
        )

        for c in self.cached_conversations:
            cid = c.get("id", 0)
            raw_title = c.get("title", "Untitled")
            title = raw_title[:18] + "..." if len(raw_title) > 18 else raw_title
            last_msgs = c.get("last_messages", [])

            lines: list[str] = [
                f"[bold {COLOR_PRIMARY}]#{cid}[/]  [bold #f5f5f5]{escape(title)}[/]",
                f"[dim {COLOR_RULE}]────────────────────────────[/]",
            ]

            if last_msgs:
                for m in last_msgs[-3:]:
                    lines.append(
                        format_message_preview(
                            sender=m.get("sender", "unknown"),
                            content=m.get("content", ""),
                            created_at=m.get("created_at", ""),
                            current_user=self.current_user,
                        )
                    )
            else:
                lines.append("")
                lines.append(f"       [dim {COLOR_DIM}](empty room)[/]")
                lines.append(f"    [dim {COLOR_RULE}]No messages yet[/]")

            all_cards.append(
                ConversationCard(conv_id=cid, content="\n".join(lines), classes="conv-card")
            )

        start = self.current_page * self.ITEMS_PER_PAGE
        end = min(start + self.ITEMS_PER_PAGE, len(all_cards))

        for card in all_cards[start:end]:
            grid.mount(card)

        dots_label = self.query_one("#pagination_dots", Label)
        dots_label.update(format_dot_matrix(self.current_page, self.total_pages))

    def action_next_page(self) -> None:
        """Switch to next page in carousel."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.render_grid()

    def action_prev_page(self) -> None:
        """Switch to previous page in carousel."""
        if self.current_page > 0:
            self.current_page -= 1
            self.render_grid()

    def action_exit_inbox(self) -> None:
        self.app.pop_screen()

    def select_conversation(self, conv_id: int) -> None:
        """Opens a conversation by ID or launches the New Room modal if 0."""
        if conv_id == 0:
            self.app.push_screen(
                NewConversationModal(self.current_user, config=self.config),
                callback=self._on_new_modal_result,
            )
            return
        self._open_conversation_worker(conv_id)

    def _on_new_modal_result(self, result: tuple[str, list[str]] | None) -> None:
        if result is None:
            return
        title, participants = result
        self._create_conversation_worker(title, participants)

    @work(thread=True)
    def _open_conversation_worker(self, conv_id: int) -> None:
        res = self.api_get(f"/api/chat/conversations/{conv_id}/messages")
        self.app.call_from_thread(self._handle_open_conversation, conv_id, res)

    def _handle_open_conversation(self, conv_id: int, res: requests.Response | None) -> None:
        log = self.query_one(RichLog)
        if res and res.status_code == 200:
            data = self.client.safe_json(res)
            title = data.get("title", f"Conversation #{conv_id}")
            self.app.push_screen(
                ChatScreen(
                    conv_id=conv_id,
                    title=title,
                    current_user=self.current_user,
                    config=self.config,
                )
            )
        else:
            log.write(format_system_event(f"Conversation #{conv_id} not found."))

    @work(thread=True)
    def _create_conversation_worker(self, title: str, participants: list[str]) -> None:
        final_participants = list(participants)
        if self.current_user not in final_participants:
            final_participants.append(self.current_user)
        res = self.api_post(
            "/api/chat/conversations",
            {"title": title, "participants": final_participants},
        )
        self.app.call_from_thread(self._handle_create_conversation, res)

    def _handle_create_conversation(self, res: requests.Response | None) -> None:
        log = self.query_one(RichLog)
        if res and res.status_code == 201:
            cid = int(self.client.safe_json(res).get("conversation_id", 0))
            self.action_refresh()
            if cid > 0:
                self._open_conversation_worker(cid)
        else:
            err_msg = self.client.safe_json(res).get("error") or "Failed to create conversation."
            log.write(format_system_event(escape(str(err_msg))))

    @work(thread=True)
    def _register_user_worker(self, new_user: str, display_name: str) -> None:
        res = self.api_post(
            "/api/chat/auth/register",
            {"username": new_user, "display_name": display_name},
        )
        self.app.call_from_thread(self._handle_register_result, new_user, res)

    def _handle_register_result(self, new_user: str, res: requests.Response | None) -> None:
        log = self.query_one(RichLog)
        if res and res.status_code in (200, 201):
            self.current_user = new_user
            app_state: Any = self.app
            app_state.current_user = self.current_user
            self.query_one("#inbox_user_meta", Label).update(f"user: {self.current_user}")
            self.current_page = 0
            self.action_refresh()
            status_msg = self.client.safe_json(res).get("status", "registered")
            log.write(
                format_system_event(
                    f"User '{escape(new_user)}' ({status_msg}). Active user switched."
                )
            )
        else:
            log.write(format_system_event("Failed to register user."))

    @work(thread=True)
    def _fetch_users_worker(self) -> None:
        res = self.api_get("/api/chat/users")
        self.app.call_from_thread(self._handle_users_result, res)

    def _handle_users_result(self, res: requests.Response | None) -> None:
        log = self.query_one(RichLog)
        if not res or res.status_code != 200:
            log.write(format_system_event("Failed to retrieve users."))
            return
        users = self.client.safe_json(res).get("users", [])
        if not users:
            log.write(format_system_event("No registered users found."))
            return
        items: list[str] = []
        for u in users:
            un = u.get("username", "")
            badge = f" [bold {COLOR_PRIMARY}](you)[/]" if un == self.current_user else ""
            items.append(f"[bold {COLOR_FOREGROUND}]{escape(un)}[/]{badge}")
        log.write(
            f"[bold {COLOR_PRIMARY}]Registered Users ({len(users)}):[/] " + "  •  ".join(items)
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw_text = event.value.strip()
        if not raw_text:
            return

        event.input.value = ""
        self.record_input_history(raw_text)
        log = self.query_one(RichLog)
        if self.handle_common_command(raw_text):
            return

        text = raw_text.lstrip("/")
        parts = text.split()
        if not parts:
            self.show_help()
            return
        cmd = parts[0].lower()

        if cmd in ("exit", "back", "quit"):
            self.app.pop_screen()
            return
        elif cmd in ("refresh", "poll"):
            self.action_refresh()
            return
        elif cmd in ("next", "n"):
            self.action_next_page()
            return
        elif cmd in ("prev", "p"):
            self.action_prev_page()
            return
        elif cmd == "0":
            self.select_conversation(0)
            return
        elif cmd.isdigit():
            self.select_conversation(int(cmd))
            return
        elif cmd == "open" and len(parts) > 1 and parts[1].isdigit():
            self.select_conversation(int(parts[1]))
            return
        elif cmd == "register":
            if len(parts) < 2:
                log.write(format_system_event("Usage: /register <username> [display_name]"))
                return
            new_user = parts[1].strip().lower()
            display_name = " ".join(parts[2:]).strip() or new_user.capitalize()
            self._register_user_worker(new_user, display_name)
            return
        elif cmd == "login":
            if len(parts) < 2:
                log.write(format_system_event("Usage: /login <username>"))
                return
            self.current_user = parts[1].lower()
            app_state: Any = self.app
            app_state.current_user = self.current_user
            self.query_one("#inbox_user_meta", Label).update(f"user: {self.current_user}")
            self.current_page = 0
            self.action_refresh()
            log.write(
                format_system_event(f"Active user switched to '{escape(self.current_user)}'.")
            )
            return
        elif cmd == "users":
            self._fetch_users_worker()
            return
        elif cmd == "new":
            raw = text[4:].strip()
            parsed = parse_new_conversation_args(raw)
            if not parsed:
                self.select_conversation(0)
                return
            title, participants = parsed
            self._create_conversation_worker(title, participants)
            return
        else:
            log.write(
                format_system_event(
                    f"Unknown command '{escape(raw_text)}'. Enter conversation ID (e.g. 12, 0) or 'login <user>'."
                )
            )
