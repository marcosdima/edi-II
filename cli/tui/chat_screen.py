from typing import Any

import requests
import urllib3
from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Label, RichLog

from ..config import ProxyConfig, get_proxy_config
from .theme import format_chat_message, format_system_event

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ChatScreen(Screen[None]):
    """Chat conversation screen with scrolling history, background workers, and centered input."""

    BINDINGS = [
        Binding("ctrl+r", "refresh", "Refresh", show=False),
        Binding("ctrl+l", "clear_log", "Clear", show=False),
        Binding("escape", "exit_chat", "Back", show=False),
    ]

    def __init__(
        self,
        conv_id: int,
        title: str,
        current_user: str,
        config: ProxyConfig | None = None,
    ) -> None:
        super().__init__()
        self.conv_id = conv_id
        self.conv_title = title
        self.current_user = current_user
        self.config = config or get_proxy_config()
        self.last_seen_id = 0

    def compose(self) -> ComposeResult:
        """Compose the layout: Header, Scrolling Message Log, Centered Input Panel."""
        yield Horizontal(
            Label(
                f"#{self.conv_id} {self.conv_title}", classes="tui-header-title", id="header_title"
            ),
            Label(
                f"user: {self.current_user}  |  https",
                classes="tui-header-meta",
                id="chat_user_meta",
            ),
            classes="tui-header",
        )
        yield Vertical(
            RichLog(
                classes="tui-log", id="message_log", highlight=False, markup=True, auto_scroll=True
            ),
            classes="tui-content",
        )
        with Vertical(classes="tui-bottom-panel"):
            with Vertical(classes="tui-input-wrapper"):
                yield Input(
                    placeholder="Type a message, or: /back, /login <user>, /help...",
                    classes="tui-input",
                    id="chat_input",
                )
                yield Label(
                    " [Esc] Back to Selector  •  [Ctrl+R] Refresh  •  Type /back, /login <user>, /help",
                    classes="tui-status-bar",
                    id="status_bar",
                )

    def on_mount(self) -> None:
        """Focus the input field and load message history on startup."""
        self.query_one(Input).focus()
        app_user = getattr(self.app, "current_user", None)
        if app_user:
            self.current_user = str(app_user)
            self.query_one("#chat_user_meta", Label).update(f"user: {self.current_user}  |  https")

        self.action_refresh()

    def api_get(self, endpoint: str) -> requests.Response | None:
        """Helper to send GET requests to proxy."""
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.get(url, verify=False, timeout=8)
        except requests.RequestException:
            return None

    def api_post(self, endpoint: str, data: dict[str, Any]) -> requests.Response | None:
        """Helper to send POST requests with JSON payload to proxy."""
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.post(url, json=data, verify=False, timeout=15)
        except requests.RequestException:
            return None

    @work(thread=True)
    def action_refresh(self) -> None:
        """Fetch and render new messages from the Reverse Proxy in worker thread."""
        res = self.api_get(f"/api/chat/conversations/{self.conv_id}/messages")
        self.app.call_from_thread(self._handle_refresh_response, res)

    def _handle_refresh_response(self, res: requests.Response | None) -> None:
        log = self.query_one(RichLog)
        status = self.query_one("#status_bar", Label)

        if not res or res.status_code != 200:
            status.update(" [!] Unable to reach server. Press Ctrl+R to retry.")
            return

        try:
            data = res.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            status.update(" [!] Invalid response from server.")
            return

        messages = data.get("messages", [])
        server_title = data.get("title")
        if server_title and server_title != self.conv_title:
            self.conv_title = server_title
            self.query_one("#header_title", Label).update(
                f"#{self.conv_id} {escape(self.conv_title)}"
            )

        new_count = 0
        for m in messages:
            msg_id = m.get("id", 0)
            if msg_id > self.last_seen_id:
                formatted = format_chat_message(
                    sender=m.get("sender", "unknown"),
                    content=m.get("content", ""),
                    created_at=m.get("created_at", ""),
                    current_user=self.current_user,
                )
                log.write(formatted)
                self.last_seen_id = max(self.last_seen_id, msg_id)
                new_count += 1

        status.update(
            f" [Ctrl+R] Refreshed ({new_count} new)  •  [Esc] Back to Inbox  •  Type /help for directives"
        )

    def action_clear_log(self) -> None:
        """Clears the local chat log display."""
        log = self.query_one(RichLog)
        log.clear()
        log.write(format_system_event("Local display cleared. Press Ctrl+R to reload."))

    def action_exit_chat(self) -> None:
        """Exit the conversation and return to inbox."""
        self.app.pop_screen()

    @work(thread=True)
    def send_message_worker(self, text: str) -> None:
        res = self.api_post(
            f"/api/chat/conversations/{self.conv_id}/messages",
            {"sender": self.current_user, "content": text},
        )
        self.app.call_from_thread(self._handle_message_response, res, text)

    def _handle_message_response(self, res: requests.Response | None, text: str) -> None:
        log = self.query_one(RichLog)
        if not res:
            log.write(format_system_event("Failed to connect to Reverse Proxy."))
            return

        if res.status_code == 201:
            try:
                m = res.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                m = {}
            msg_id = m.get("id", self.last_seen_id + 1)
            formatted = format_chat_message(
                sender=self.current_user,
                content=text,
                created_at=m.get("created_at", ""),
                current_user=self.current_user,
            )
            log.write(formatted)
            self.last_seen_id = max(self.last_seen_id, msg_id)
        elif res.status_code == 200:
            try:
                data = res.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                data = {}
            directive = data.get("directive", "")
            if directive == "/title":
                new_title = text.split(maxsplit=1)[1] if " " in text else self.conv_title
                self.conv_title = new_title
                self.query_one("#header_title", Label).update(
                    f"#{self.conv_id} {escape(self.conv_title)}"
                )
                log.write(format_system_event(data.get("message", "Title updated.")))
            elif directive == "/members":
                members = [escape(m.get("username", "")) for m in data.get("members", [])]
                log.write(format_system_event(f"Participants: {', '.join(members)}"))
            elif directive == "/clear":
                log.clear()
                log.write(format_system_event(data.get("message", "History cleared.")))
            elif directive == "/leave":
                log.write(format_system_event(data.get("message", "Left conversation.")))
            elif directive == "/help":
                log.write(format_system_event("Available Directives:"))
                for d in data.get("available_directives", []):
                    log.write(
                        format_system_event(
                            f"  {escape(d.get('command', '')):<20} {escape(d.get('description', ''))}"
                        )
                    )
            else:
                log.write(format_system_event(f"Directive executed: {escape(res.text)}"))
        elif res.status_code == 403:
            log.write(
                format_system_event("Forbidden: You are not an active participant in this chat.")
            )
        elif res.status_code == 429:
            log.write(
                format_system_event("Rate Limited: Nginx throttled requests (HTTP 429). Slow down.")
            )
        else:
            log.write(format_system_event(f"Error ({res.status_code}): {escape(res.text)}"))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Process message submission or system directives."""
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        log = self.query_one(RichLog)

        if text.lower() in ("/back", "/exit", "/quit", "/conversations", "back", "exit", "leave"):
            self.app.pop_screen()
            return
        if text.startswith("/login") or text.startswith("login "):
            parts = text.split()
            if len(parts) > 1:
                self.current_user = parts[1].strip().lower()
                app_state: Any = self.app
                app_state.current_user = self.current_user
                self.api_post(
                    "/api/chat/auth/register",
                    {"username": self.current_user, "display_name": self.current_user.capitalize()},
                )
                self.query_one("#chat_user_meta", Label).update(
                    f"user: {self.current_user}  |  https"
                )
                log.write(
                    format_system_event(f"Active user switched to '{escape(self.current_user)}'.")
                )
            else:
                log.write(format_system_event("Usage: /login <username>"))
            return
        if text.lower() in ("/help", "help", "?"):
            log.write("\n[bold #ffffff]Available Commands & Directives:[/]")
            log.write("  [bold #e5e5e5]/back, /exit, Esc[/]    Return to conversation selector")
            log.write(
                "  [bold #e5e5e5]/login <username>[/]    Switch active user identity in real time"
            )
            log.write("  [bold #e5e5e5]/refresh, Ctrl+R[/]     Fetch latest chat messages")
            log.write("  [bold #e5e5e5]/clear, Ctrl+L[/]       Clear local message display")
            log.write("  [bold #e5e5e5]/title <name>[/]        Rename this conversation")
            log.write("  [bold #e5e5e5]/members[/]             List conversation participants")
            log.write("  [bold #e5e5e5]/leave[/]               Leave this conversation\n")
            return
        if text.lower() in ("/refresh", "/poll"):
            self.action_refresh()
            return

        self.send_message_worker(text)
