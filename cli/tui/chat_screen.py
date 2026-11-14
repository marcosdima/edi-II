import json
import ssl
from typing import Any

import requests
import websockets
from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Input, Label, RichLog
from textual.worker import Worker

from ..config import ProxyConfig
from .base_screen import BaseTUIScreen, CommandSpec
from .theme import format_chat_message, format_system_event


class ChatScreen(BaseTUIScreen):
    """Chat conversation screen with scrolling history, background workers, and centered input."""

    SCREEN_COMMANDS = [
        CommandSpec("/help", "Show available commands & directives", aliases=("help", "?")),
        CommandSpec("/login", "Switch active user identity", args="<username>"),
        CommandSpec("/refresh", "Fetch latest chat messages", aliases=("poll",)),
        CommandSpec("/clear", "Clear local message display", aliases=("clear", "cls")),
        CommandSpec("/title", "Rename this conversation (server)", args="<name>"),
        CommandSpec("/members", "List conversation participants (server)"),
        CommandSpec("/leave", "Leave this conversation (server)"),
        CommandSpec("/back", "Return to conversation selector", aliases=("/exit", "/quit")),
    ]

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
        super().__init__(config=config)
        self.conv_id = conv_id
        self.conv_title = title
        self.current_user = current_user
        self.last_seen_id = 0
        self._ws_worker: Worker[None] | None = None

    def compose(self) -> ComposeResult:
        """Compose the layout: Header, Scrolling Message Log, Centered Input Panel."""
        yield self.compose_header(
            f"#{self.conv_id} {self.conv_title}",
            f"user: {self.current_user}  |  https",
            title_id="header_title",
            meta_id="chat_user_meta",
        )
        yield self.compose_log_body("message_log")
        yield self.compose_bottom_panel(
            placeholder="Type a message, or: /back, /login <user>, /help...",
            status_text=" [Esc] Back to Selector  •  [Ctrl+R] Refresh  •  Type /back, /login <user>, /help",
            input_id="chat_input",
            status_id="status_bar",
        )

    def on_mount(self) -> None:
        """Focus the input field and load message history on startup."""
        self.query_one(Input).focus()
        app_user = getattr(self.app, "current_user", None)
        if app_user:
            self.current_user = str(app_user)
            self.query_one("#chat_user_meta", Label).update(f"user: {self.current_user}  |  https")

        self.action_refresh()
        self._ws_worker = self.listen_websocket()

    def on_unmount(self) -> None:
        """Cancel active WebSocket listener when leaving the chat screen."""
        if self._ws_worker is not None:
            self._ws_worker.cancel()

    @work(exclusive=True, group="ws_listener")
    async def listen_websocket(self) -> None:
        """Stream real-time incoming messages over WSS through Nginx."""
        ws_url = f"{self.config.wss_url}/api/chat/ws/conversations/{self.conv_id}"
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            headers = self.config.default_headers
            async with websockets.connect(
                ws_url,
                ssl=ssl_ctx,
                additional_headers=headers or None,
            ) as ws:
                async for raw_msg in ws:
                    if not isinstance(raw_msg, str):
                        continue
                    try:
                        data = json.loads(raw_msg)
                    except ValueError:
                        continue
                    if data.get("type") != "chat_message":
                        continue
                    msg_id = int(data.get("id", 0))
                    if msg_id > self.last_seen_id:
                        formatted = format_chat_message(
                            sender=data.get("sender", "unknown"),
                            content=data.get("content", ""),
                            created_at=data.get("created_at", ""),
                            current_user=self.current_user,
                        )
                        self.query_one(RichLog).write(formatted)
                        self.last_seen_id = max(self.last_seen_id, msg_id)
        except Exception:
            # Graceful fallback: manual Ctrl+R refresh remains available
            pass

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

        data = self.client.safe_json(res)
        if not data:
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
            m = self.client.safe_json(res)
            msg_id = int(m.get("id", 0))
            if msg_id > self.last_seen_id:
                formatted = format_chat_message(
                    sender=self.current_user,
                    content=text,
                    created_at=m.get("created_at", ""),
                    current_user=self.current_user,
                )
                log.write(formatted)
                self.last_seen_id = max(self.last_seen_id, msg_id)
        elif res.status_code == 200:
            data = self.client.safe_json(res)
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
            elif directive == "/leave":
                log.write(format_system_event(data.get("message", "Left conversation.")))
            else:
                log.write(format_system_event(f"Directive executed: {escape(res.text)}"))
        elif res.status_code == 400:
            err_msg = self.client.safe_json(res).get("error") or res.text
            log.write(format_system_event(escape(str(err_msg))))
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

    @work(thread=True)
    def _switch_user_worker(self, username: str) -> None:
        self.api_post(
            "/api/chat/auth/register",
            {"username": username, "display_name": username.capitalize()},
        )
        res = self.api_get(f"/api/chat/users/{username}/conversations")
        is_member = True
        if res and res.status_code == 200:
            convs = self.client.safe_json(res).get("conversations", [])
            is_member = any(c.get("id") == self.conv_id for c in convs)
        self.app.call_from_thread(self._handle_switch_user_result, username, is_member)

    def _handle_switch_user_result(self, username: str, is_member: bool) -> None:
        if not is_member:
            if len(self.app.screen_stack) > 1:
                self.app.pop_screen()
                try:
                    self.app.screen.query_one(RichLog).write(
                        format_system_event(
                            f"User '{escape(username)}' is not a participant in '{escape(self.conv_title)}'."
                        )
                    )
                except Exception:
                    pass
            return

        self.query_one(RichLog).write(
            format_system_event(f"Active user switched to '{escape(username)}'.")
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Process message submission or system directives."""
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        self.record_input_history(text)
        log = self.query_one(RichLog)

        if text.lower() in ("/back", "/exit", "/quit", "/conversations", "back", "exit", "leave"):
            self.app.pop_screen()
            return
        if text.startswith("/login") or text.startswith("login "):
            parts = text.split()
            if len(parts) > 1:
                new_user = parts[1].strip().lower()
                self.current_user = new_user
                app_state: Any = self.app
                app_state.current_user = new_user
                self.query_one("#chat_user_meta", Label).update(
                    f"user: {self.current_user}  |  https"
                )
                self._switch_user_worker(new_user)
            else:
                log.write(format_system_event("Usage: /login <username>"))
            return
        if text.lower() in ("/help", "help", "?"):
            self.show_help("Available Commands & Directives:")
            return
        if text.lower() == "/clear":
            self.action_clear_log()
            return
        if text.lower() in ("/refresh", "/poll"):
            self.action_refresh()
            return
        if text.startswith("/"):
            cmd_token = text.split()[0].lower()
            server_directives = {"/title", "/members", "/leave"}
            if cmd_token not in server_directives:
                log.write(
                    format_system_event(
                        f"Unknown command '{escape(cmd_token)}'. Type /help for available commands."
                    )
                )
                return

        self.send_message_worker(text)
