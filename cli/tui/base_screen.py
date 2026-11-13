"""Shared base screen providing common layout composition, command selector, and HTTP helpers."""

from dataclasses import dataclass
from typing import Any

import requests
from textual import events
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Label, OptionList, RichLog
from textual.widgets.option_list import Option

from ..client import ProxyClient
from ..config import ProxyConfig, get_proxy_config
from .theme import COLOR_DIM, COLOR_PRIMARY, format_command_help


@dataclass(frozen=True)
class CommandSpec:
    """Declarative specification for a TUI slash/text command."""

    name: str
    description: str
    aliases: tuple[str, ...] = ()
    args: str = ""

    @property
    def usage(self) -> str:
        return f"{self.name} {self.args}".strip()


class BaseTUIScreen(Screen[None]):
    """Base Textual screen with unified layout composition, slash-command selector, and HTTP helpers."""

    SCREEN_COMMANDS: list[CommandSpec] = []

    def __init__(self, config: ProxyConfig | None = None) -> None:
        super().__init__()
        self.config = config or get_proxy_config()
        self.client = ProxyClient(self.config)
        self._input_widget_id = "input"
        self._status_widget_id = "status_bar"
        self._default_status_text = ""
        self._input_history: list[str] = []
        self._history_index: int | None = None
        self._history_draft = ""
        self._suppress_palette_once = False

    def record_input_history(self, text: str) -> None:
        """Store submitted input in history and reset navigation cursor."""
        cleaned = text.strip()
        if cleaned and (not self._input_history or self._input_history[-1] != cleaned):
            self._input_history.append(cleaned)
        self._history_index = None
        self._history_draft = ""

    def get_commands(self) -> list[CommandSpec]:
        """Return available commands for this screen."""
        return list(self.SCREEN_COMMANDS)

    def compose_header(
        self,
        title: str,
        meta: str,
        *,
        title_id: str | None = None,
        meta_id: str | None = None,
    ) -> Horizontal:
        """Build the standard top monochrome header bar."""
        return Horizontal(
            Label(title, classes="tui-header-title", id=title_id),
            Label(meta, classes="tui-header-meta", id=meta_id),
            classes="tui-header",
        )

    def compose_log_body(self, log_id: str) -> Vertical:
        """Build the standard scrollable RichLog content area with line wrapping."""
        return Vertical(
            RichLog(
                classes="tui-log",
                id=log_id,
                wrap=True,
                min_width=20,
                highlight=False,
                markup=True,
                auto_scroll=True,
            ),
            classes="tui-content",
        )

    def compose_bottom_panel(
        self,
        placeholder: str,
        status_text: str,
        *,
        input_id: str,
        status_id: str,
    ) -> Vertical:
        """Build the bottom dock with slash-command selector popup + input panel."""
        self._input_widget_id = input_id
        self._status_widget_id = status_id
        self._default_status_text = status_text
        return Vertical(
            OptionList(id="command_palette"),
            Vertical(
                Vertical(
                    Input(placeholder=placeholder, classes="tui-input", id=input_id),
                    Label(status_text, classes="tui-status-bar", id=status_id),
                    classes="tui-input-wrapper",
                ),
                classes="tui-bottom-panel",
            ),
            classes="tui-bottom-dock",
        )

    def _update_status_bar(self, text: str) -> None:
        try:
            self.query_one(f"#{self._status_widget_id}", Label).update(text)
        except Exception:
            pass

    def _hide_command_palette(self) -> None:
        try:
            palette = self.query_one("#command_palette", OptionList)
            palette.display = False
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Show live slash-command selector when typing '/'."""
        if self._suppress_palette_once:
            self._suppress_palette_once = False
            return
        raw = event.value.lstrip()
        if not raw.startswith("/"):
            self._hide_command_palette()
            self._update_status_bar(self._default_status_text)
            return

        commands = self.get_commands()
        if not commands:
            return

        prefix = raw.split()[0].lower()
        matches = [
            c
            for c in commands
            if c.name.lower().startswith(prefix)
            or any(f"/{a.lstrip('/')}".startswith(prefix) for a in c.aliases)
        ]

        try:
            palette = self.query_one("#command_palette", OptionList)
        except Exception:
            return

        palette.clear_options()
        if not matches:
            palette.display = False
            self._update_status_bar(" No matching command. Type /help for available commands.")
            return

        for cmd in matches:
            label = (
                f"[bold {COLOR_PRIMARY}]{cmd.usage:<22}[/]  [dim {COLOR_DIM}]{cmd.description}[/]"
            )
            palette.add_option(Option(label, id=cmd.name))

        palette.display = True
        palette.highlighted = 0
        self._update_status_bar(
            " [↑/↓] Navigate  •  [Tab] Autocomplete  •  [Enter / Click] Run  •  [Esc] Close"
        )

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Fill or execute the selected slash command from the command selector."""
        if event.option_list.id != "command_palette":
            return

        cmd_name = event.option_id
        cmd_spec = next((c for c in self.get_commands() if c.name == cmd_name), None)
        self._hide_command_palette()
        self._update_status_bar(self._default_status_text)

        inp = self.query_one(f"#{self._input_widget_id}", Input)
        inp.focus()
        if not cmd_spec:
            return

        if cmd_spec.args:
            self._suppress_palette_once = True
            inp.value = f"{cmd_spec.name} "
            inp.cursor_position = len(inp.value)
        else:
            self._suppress_palette_once = True
            inp.value = cmd_spec.name
            await inp.action_submit()

    def on_key(self, event: events.Key) -> None:
        """Handle slash-command palette navigation and Up/Down input history."""
        try:
            palette = self.query_one("#command_palette", OptionList)
        except Exception:
            palette = None

        if palette is not None and palette.display:
            if event.key == "down" and not palette.has_focus:
                palette.focus()
                event.stop()
            elif event.key == "tab":
                idx = palette.highlighted if palette.highlighted is not None else 0
                if 0 <= idx < palette.option_count:
                    opt = palette.get_option_at_index(idx)
                    cmd_spec = next((c for c in self.get_commands() if c.name == opt.id), None)
                    self._hide_command_palette()
                    self._update_status_bar(self._default_status_text)
                    inp = self.query_one(f"#{self._input_widget_id}", Input)
                    inp.focus()
                    if cmd_spec:
                        self._suppress_palette_once = True
                        inp.value = f"{cmd_spec.name} " if cmd_spec.args else cmd_spec.name
                        inp.cursor_position = len(inp.value)
                event.prevent_default()
                event.stop()
            elif event.key == "escape":
                self._hide_command_palette()
                self._update_status_bar(self._default_status_text)
                self.query_one(f"#{self._input_widget_id}", Input).focus()
                event.stop()
            return

        try:
            inp = self.query_one(f"#{self._input_widget_id}", Input)
        except Exception:
            return

        if not inp.has_focus or not self._input_history:
            return

        if event.key == "up":
            if self._history_index is None:
                self._history_draft = inp.value
                self._history_index = len(self._input_history) - 1
            elif self._history_index > 0:
                self._history_index -= 1
            inp.value = self._input_history[self._history_index]
            inp.cursor_position = len(inp.value)
            event.stop()
        elif event.key == "down" and self._history_index is not None:
            if self._history_index < len(self._input_history) - 1:
                self._history_index += 1
                inp.value = self._input_history[self._history_index]
            else:
                self._history_index = None
                inp.value = self._history_draft
            inp.cursor_position = len(inp.value)
            event.stop()

    def show_help(self, header: str = "Available Commands:") -> None:
        """Write the screen's registered commands to its RichLog."""
        log = self.query_one(RichLog)
        rows = [(c.usage, c.description) for c in self.get_commands()]
        for line in format_command_help(header, rows):
            log.write(line)

    def handle_common_command(self, raw_text: str) -> bool:
        """Handle universal commands (/help, /clear, /back, /exit, /quit). Returns True if handled."""
        self._hide_command_palette()
        cmd = raw_text.strip().split()[0].lower()
        if cmd in ("/help", "help", "?"):
            self.show_help()
            return True
        if cmd in ("/clear", "clear", "cls"):
            clear_action = getattr(self, "action_clear_log", None)
            if callable(clear_action):
                clear_action()
            else:
                self.query_one(RichLog).clear()
            return True
        if cmd in ("/back", "/exit", "/quit"):
            if len(self.app.screen_stack) > 1:
                self.app.pop_screen()
            else:
                self.app.exit()
            return True
        return False

    def api_get(self, endpoint: str, timeout: int = 8) -> requests.Response | None:
        """Send a GET request to the reverse proxy."""
        return self.client.get(endpoint, timeout=timeout)

    def api_post(
        self, endpoint: str, data: dict[str, Any], timeout: int = 15
    ) -> requests.Response | None:
        """Send a POST request with JSON payload to the reverse proxy."""
        return self.client.post(endpoint, data, timeout=timeout)
