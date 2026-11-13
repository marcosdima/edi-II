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
from .theme import format_system_event

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AIScreen(Screen[None]):
    """Interactive AI completion screen with non-blocking workers and monochrome formatting."""

    BINDINGS = [
        Binding("escape", "exit_ai", "Back", show=False),
        Binding("ctrl+l", "clear_log", "Clear", show=False),
    ]

    def __init__(self, config: ProxyConfig | None = None) -> None:
        super().__init__()
        self.config = config or get_proxy_config()
        self.provider = "unknown"
        self.default_model = "loading..."
        self.current_model: str | None = None
        self.temperature: float = 0.7
        self.system_prompt: str | None = None

    def get_active_model(self) -> str:
        return self.current_model or self.default_model

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label("AI COMPLETION ASSISTANT", classes="tui-header-title"),
            Label(f"model: {self.get_active_model()}", classes="tui-header-meta", id="ai_meta"),
            classes="tui-header",
        )
        yield Vertical(
            RichLog(classes="tui-log", id="ai_log", highlight=False, markup=True, auto_scroll=True),
            classes="tui-content",
        )
        with Vertical(classes="tui-bottom-panel"):
            with Vertical(classes="tui-input-wrapper"):
                yield Input(
                    placeholder="Type a prompt or /model <name>, /temp <0.0-2.0>, /sys <prompt>...",
                    classes="tui-input",
                    id="ai_input",
                )
                yield Label(
                    " [Esc] Back to Menu  •  [Ctrl+L] Clear  •  Type any question to query AI via proxy",
                    classes="tui-status-bar",
                    id="ai_status",
                )

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self.fetch_info()

    def api_get(self, endpoint: str) -> requests.Response | None:
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.get(url, verify=False, timeout=8)
        except requests.RequestException:
            return None

    def api_post(self, endpoint: str, data: dict[str, Any]) -> requests.Response | None:
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.post(url, json=data, verify=False, timeout=60)
        except requests.RequestException:
            return None

    @work(thread=True)
    def fetch_info(self) -> None:
        res = self.api_get("/api/ai/info")
        log = self.query_one(RichLog)
        if res and res.status_code == 200:
            try:
                data = res.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                data = {}
            cfg = data.get("configuration", {})
            self.provider = cfg.get("provider", "unknown")
            self.default_model = cfg.get("default_model", "unknown")
            key_ok = cfg.get("api_key_configured", False)
            self.app.call_from_thread(self._on_info_loaded, key_ok)
        else:
            self.app.call_from_thread(
                log.write, format_system_event("Warning: Unable to reach AI service on proxy.")
            )

    def _on_info_loaded(self, key_ok: bool) -> None:
        self.query_one("#ai_meta", Label).update(f"model: {self.get_active_model()}")
        log = self.query_one(RichLog)
        log.write("[bold #ffffff]AI Completion Service Active[/]")
        log.write(
            f"[dim #737373]Provider: {self.provider}  •  Model: {self.get_active_model()}  •  API Key: {'Configured' if key_ok else 'Fallback'}[/]\n"
        )

    def action_exit_ai(self) -> None:
        self.app.pop_screen()

    def action_clear_log(self) -> None:
        self.query_one(RichLog).clear()

    @work(thread=True)
    def query_ai_worker(self, payload: dict[str, Any]) -> None:
        res = self.api_post("/api/ai/generate", payload)
        self.app.call_from_thread(self._handle_ai_response, res)

    def _handle_ai_response(self, res: requests.Response | None) -> None:
        log = self.query_one(RichLog)
        status = self.query_one("#ai_status", Label)

        if not res:
            log.write(format_system_event("Network error reaching reverse proxy."))
            status.update(" [!] Connection failed.")
            return

        if res.status_code == 200:
            try:
                data = res.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                data = {}
            resp = data.get("response", {})
            reply = resp.get("reply", "").strip()
            latency = resp.get("latency_ms", 0.0)
            is_fallback = resp.get("is_fallback", False)

            tag = (
                "[dim #525252](fallback offline)[/]"
                if is_fallback
                else f"[dim #525252]({latency} ms)[/]"
            )
            log.write(f"{escape(reply)}\n  {tag}")
            status.update(" [Esc] Back to Menu  •  Ready")
        elif res.status_code == 429:
            log.write(format_system_event("HTTP 429: Rate limited by Nginx. Slow down."))
            status.update(" [!] Rate limited.")
        else:
            log.write(format_system_event(f"Error {res.status_code}: {escape(res.text)}"))
            status.update(" [!] Request error.")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        log = self.query_one(RichLog)

        if text.lower() in ("/back", "/exit", "/quit"):
            self.app.pop_screen()
            return
        elif text.lower() == "/clear":
            log.clear()
            return
        elif text.startswith("/model"):
            parts = text.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip() != "reset":
                self.current_model = parts[1].strip()
                log.write(format_system_event(f"Active model set to '{self.current_model}'"))
            else:
                self.current_model = None
                log.write(format_system_event(f"Model reset to default '{self.default_model}'"))
            self.query_one("#ai_meta", Label).update(f"model: {self.get_active_model()}")
            return
        elif text.startswith("/temp"):
            parts = text.split()
            if len(parts) > 1:
                try:
                    self.temperature = float(parts[1])
                    log.write(format_system_event(f"Temperature set to {self.temperature}"))
                except ValueError:
                    log.write(format_system_event("Invalid temperature."))
            return
        elif text.startswith("/sys"):
            parts = text.split(maxsplit=1)
            self.system_prompt = parts[1].strip() if len(parts) > 1 else None
            log.write(format_system_event(f"System prompt: {self.system_prompt or 'Default'}"))
            return

        # Regular AI Query (non-blocking worker)
        log.write(f"\n[bold #ffffff]>>> {escape(text)}[/]")
        status = self.query_one("#ai_status", Label)
        status.update(" [•] Querying upstream AI model through Reverse Proxy...")

        payload: dict[str, Any] = {
            "prompt": text,
            "temperature": self.temperature,
        }
        if self.current_model:
            payload["model"] = self.current_model
        if self.system_prompt:
            payload["system_prompt"] = self.system_prompt

        self.query_ai_worker(payload)
