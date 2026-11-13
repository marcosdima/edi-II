from typing import Any

import requests
import urllib3
from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Label, RichLog, Static

from ..config import ProxyConfig, get_proxy_config
from .chat_screen import ChatScreen
from .theme import format_dot_matrix, format_system_event

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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


class InboxScreen(Screen[None]):
    """Inbox screen with spacious rectangular cards in a horizontal dot-matrix carousel."""

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
        super().__init__()
        self.current_user = current_user.strip().lower()
        self.config = config or get_proxy_config()
        self.cached_conversations: list[dict[str, Any]] = []
        self.current_page = 0
        self.total_pages = 1

    def compose(self) -> ComposeResult:
        """Compose layout: Header, Cards Grid, Dot Matrix Bar, Feedback Area, Bottom Panel."""
        yield Horizontal(
            Label("CONVERSATION SELECTOR", classes="tui-header-title"),
            Label(f"user: {self.current_user}", classes="tui-header-meta", id="inbox_user_meta"),
            classes="tui-header",
        )
        yield Grid(id="conversations_grid")
        yield Label("", id="pagination_dots")
        with Vertical(id="inbox_log_container"):
            yield RichLog(
                classes="tui-log", id="inbox_log", highlight=False, markup=True, auto_scroll=True
            )
        with Vertical(classes="tui-bottom-panel"):
            with Vertical(classes="tui-input-wrapper"):
                yield Input(
                    placeholder="Enter conversation ID (e.g. 12, 0 for new), or: /login <user>, users...",
                    classes="tui-input",
                    id="inbox_input",
                )
                yield Label(
                    " [0] + New Room  •  Type ID or click card  •  [PgUp/PgDn] Page  •  [Ctrl+R] Refresh  •  [Esc] Back",
                    classes="tui-status-bar",
                    id="inbox_status",
                )

    def on_mount(self) -> None:
        """Fetch inbox and focus input on startup."""
        self.query_one(Input).focus()
        app_user = getattr(self.app, "current_user", None)
        if app_user:
            self.current_user = str(app_user)
            self.query_one("#inbox_user_meta", Label).update(f"user: {self.current_user}")

        self.action_refresh()

    def api_get(self, endpoint: str) -> requests.Response | None:
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.get(url, verify=False, timeout=8)
        except requests.RequestException:
            return None

    def api_post(self, endpoint: str, data: dict[str, Any]) -> requests.Response | None:
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.post(url, json=data, verify=False, timeout=15)
        except requests.RequestException:
            return None

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

        try:
            data = res.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            data = {}

        conversations = data.get("conversations", [])
        self.app.call_from_thread(self._apply_conversations, conversations)

    def _handle_refresh_error(self) -> None:
        grid = self.query_one("#conversations_grid", Grid)
        grid.remove_children()
        grid.mount(Static("[dim #737373]Unable to reach Reverse Proxy.[/]", classes="conv-card"))

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

        # Card 0 (+ New Room)
        card_0_content = (
            "[bold #ffffff][ 0 ][/]\n"
            "[bold #e5e5e5]New Room[/]\n\n"
            "[bold #ffffff]+[/]\n\n"
            "[dim #737373]Click or type '0'[/]\n"
            "[dim #525252]to create a room[/]"
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
                f"[bold #ffffff]#{cid}[/]  [bold #f5f5f5]{escape(title)}[/]",
                "[dim #333333]────────────────────────────[/]",
            ]

            if last_msgs:
                for m in last_msgs[-3:]:
                    sender = m.get("sender", "unknown")[:10]
                    raw_content = m.get("content", "").replace("\n", " ").strip()
                    preview = raw_content[:26] + ("..." if len(raw_content) > 26 else "")
                    raw_time = m.get("created_at", "")
                    time_str = raw_time[11:16] if len(raw_time) >= 16 else ""

                    time_tag = f"[dim #666666]{time_str}[/] " if time_str else ""
                    if sender == self.current_user:
                        sender_tag = f"[bold #ffffff]{escape(sender)}[/]"
                        content_tag = f"[#ffffff]{escape(preview)}[/]"
                    else:
                        sender_tag = f"[bold #a3a3a3]{escape(sender)}[/]"
                        content_tag = f"[#d4d4d4]{escape(preview)}[/]"

                    lines.append(f"{time_tag}{sender_tag}: {content_tag}")
            else:
                lines.append("")
                lines.append("       [dim #525252](empty room)[/]")
                lines.append("    [dim #333333]No messages yet[/]")

            all_cards.append(
                ConversationCard(conv_id=cid, content="\n".join(lines), classes="conv-card")
            )

        start = self.current_page * self.ITEMS_PER_PAGE
        end = min(start + self.ITEMS_PER_PAGE, len(all_cards))

        for card in all_cards[start:end]:
            grid.mount(card)

        # Update dot matrix carousel
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
        """Opens a conversation by ID or triggers creation if 0."""
        log = self.query_one(RichLog)
        if conv_id == 0:
            log.write(
                '\n[bold #ffffff]Create new room:[/] type [bold #e5e5e5]new "Title" user1,user2[/]'
            )
            return

        res = self.api_get(f"/api/chat/conversations/{conv_id}/messages")
        if res and res.status_code == 200:
            try:
                title = res.json().get("title", f"Conversation #{conv_id}")
            except (ValueError, requests.exceptions.JSONDecodeError):
                title = f"Conversation #{conv_id}"

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

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw_text = event.value.strip()
        if not raw_text:
            return

        event.input.value = ""
        log = self.query_one(RichLog)
        text = raw_text.lstrip("/")
        parts = text.split()
        cmd = parts[0].lower()

        if cmd in ("exit", "back", "quit"):
            self.app.pop_screen()
            return
        elif cmd in ("help", "?"):
            log.write("\n[bold #ffffff]Available Commands in Inbox:[/]")
            log.write("  [bold #e5e5e5]<id>[/]               Open conversation by ID (e.g. 12)")
            log.write("  [bold #e5e5e5]0[/]                  Create a new conversation room")
            log.write("  [bold #e5e5e5]next / n, right[/]    Next page in carousel")
            log.write("  [bold #e5e5e5]prev / p, left[/]     Previous page in carousel")
            log.write("  [bold #e5e5e5]/login <username>[/]  Switch active user identity")
            log.write("  [bold #e5e5e5]users[/]              List registered users on server")
            log.write("  [bold #e5e5e5]new <title> <users>[/] Create new chat room")
            log.write("  [bold #e5e5e5]/back, /exit, Esc[/]  Return to main menu\n")
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
        elif cmd == "login" and len(parts) > 1:
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
            res = self.api_get("/api/chat/users")
            if res and res.status_code == 200:
                try:
                    users = res.json().get("users", [])
                except (ValueError, requests.exceptions.JSONDecodeError):
                    users = []
                log.write("\n[bold #ffffff]Registered Users:[/]")
                for u in users:
                    un = u.get("username", "")
                    dn = u.get("display_name", "")
                    badge = "[bold #ffffff](you)[/]" if un == self.current_user else ""
                    log.write(
                        f"  • [bold #e5e5e5]{escape(un):<15}[/] [dim #737373]{escape(dn):<25}[/] {badge}"
                    )
                log.write("")
            return
        elif cmd == "new":
            raw = text[4:].strip()
            if not raw:
                log.write(format_system_event('Usage: new "Title" user1,user2'))
                return
            n_parts = raw.rsplit(maxsplit=1)
            title = n_parts[0].strip("\"'")
            users_part = n_parts[1] if len(n_parts) > 1 else ""
            participants = [
                u.strip().lower() for u in users_part.replace(" ", "").split(",") if u.strip()
            ]
            if self.current_user not in participants:
                participants.append(self.current_user)

            res = self.api_post(
                "/api/chat/conversations",
                {"title": title, "participants": participants},
            )
            if res and res.status_code == 201:
                try:
                    cid = res.json().get("conversation_id", 0)
                except (ValueError, requests.exceptions.JSONDecodeError):
                    cid = 0
                self.action_refresh()
                self.select_conversation(cid)
            else:
                log.write(format_system_event("Failed to create conversation."))
            return
        else:
            log.write(
                format_system_event(
                    f"Unknown command '{escape(raw_text)}'. Enter conversation ID (e.g. 12, 0) or 'login <user>'."
                )
            )
