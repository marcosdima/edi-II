import subprocess
from collections.abc import Callable

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, RichLog, Static

from ..config import ProxyConfig
from ..tester import ProxyTester
from .ai_screen import AIScreen
from .base_screen import BaseTUIScreen, CommandSpec
from .inbox_screen import InboxScreen
from .theme import (
    COLOR_FOREGROUND,
    COLOR_MUTED,
    COLOR_PRIMARY,
    format_section_header,
    format_status_err,
    format_status_ok,
    format_system_event,
)

DASHBOARD_CARDS: list[tuple[str, str, str, str]] = [
    ("1", "CHAT SYSTEM", "Multi-user rooms & directives", "action_open_chat"),
    ("2", "AI ASSISTANT", "Groq LLM & offline fallback", "action_open_ai"),
    ("3", "SECURITY SUITE", "GeoIP & Rate Limiting (429)", "action_run_security"),
    ("4", "AUDIT LOGS", "Live Nginx traffic & TLS logs", "action_view_audit"),
    ("5", "CONTAINERS", "Docker compose health & status", "action_view_containers"),
    ("6", "FULL TEST SUITE", "7 end-to-end proxy checks", "action_run_tests"),
]


class MenuCard(Static):
    """Clickable compact dashboard card matching the InboxScreen card aesthetic."""

    def __init__(self, shortcut: str, title: str, description: str, action_name: str) -> None:
        content = (
            f"[bold {COLOR_PRIMARY}][{shortcut}][/] "
            f"[bold {COLOR_FOREGROUND}]{escape(title)}[/] "
            f"[dim {COLOR_MUTED}]• {escape(description)}[/]"
        )
        super().__init__(content, classes="conv-card menu-card")
        self.action_name = action_name

    def on_click(self) -> None:
        """Trigger the card's associated screen action on mouse click."""
        handler: Callable[[], None] | None = getattr(self.screen, self.action_name, None)
        if callable(handler):
            handler()


class MainScreen(BaseTUIScreen):
    """Main dashboard menu screen unified with the dark minimalist aesthetic."""

    SCREEN_COMMANDS = [
        CommandSpec("/help", "Show available commands", aliases=("help", "?")),
        CommandSpec("/chat", "Open multi-user chat inbox (or 1)", aliases=("1", "chat")),
        CommandSpec("/ai", "Open AI completion assistant (or 2)", aliases=("2", "ai")),
        CommandSpec(
            "/security", "Run security verification suite (or 3)", aliases=("3", "security")
        ),
        CommandSpec("/audit", "Show recent Nginx audit logs (or 4)", aliases=("4", "audit")),
        CommandSpec("/status", "Inspect Docker containers (or 5)", aliases=("5", "status", "ps")),
        CommandSpec("/test", "Run 7 end-to-end proxy tests (or 6)", aliases=("6", "test", "tests")),
        CommandSpec("/clear", "Clear output log", aliases=("clear", "cls")),
        CommandSpec("/exit", "Exit application", aliases=("exit", "quit", "q")),
    ]

    BINDINGS = [
        Binding("1", "open_chat", "Chat", show=False),
        Binding("2", "open_ai", "AI", show=False),
        Binding("3", "run_security", "Security", show=False),
        Binding("4", "view_audit", "Audit", show=False),
        Binding("5", "view_containers", "Containers", show=False),
        Binding("6", "run_tests", "Test", show=False),
        Binding("ctrl+l", "clear_log", "Clear", show=False),
        Binding("escape", "exit_app", "Exit", show=False),
        Binding("ctrl+q", "exit_app", "Quit", show=False),
    ]

    def __init__(self, config: ProxyConfig | None = None) -> None:
        super().__init__(config=config)
        self.tester = ProxyTester()

    def compose(self) -> ComposeResult:
        yield self.compose_header("SISTEMAS OPERATIVOS • FINAL EDI II", "Proxy Reverso - Nginx")
        yield Static(
            f"[bold {COLOR_PRIMARY}]REVERSE PROXY GATEWAY[/]\n"
            f"[dim {COLOR_MUTED}]Select a module card below or type a command  •  Type / for command hints[/]",
            classes="main-hero",
        )
        with Horizontal(id="main_workspace"):
            with Vertical(id="main_menu_list"):
                for shortcut, title, desc, action_name in DASHBOARD_CARDS:
                    yield MenuCard(shortcut, title, desc, action_name)
            with Vertical(id="main_output_container"):
                yield RichLog(
                    classes="tui-log",
                    id="main_log",
                    wrap=True,
                    min_width=20,
                    highlight=False,
                    markup=True,
                    auto_scroll=True,
                )
        yield self.compose_bottom_panel(
            placeholder="Select [1-6], click a card, or type /help, chat, ai, audit, test...",
            status_text=" [1-6] Modules  •  Type / for Commands  •  [Ctrl+L] Clear Output  •  [Esc] Exit",
            input_id="main_input",
            status_id="main_status",
        )

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        log = self.query_one(RichLog)
        log.write(format_system_event("Ready. Output and container logs will appear here."))

    def action_clear_log(self) -> None:
        """Clear only the isolated output log block."""
        self.query_one(RichLog).clear()

    def action_open_chat(self) -> None:
        user = getattr(self.app, "current_user", "marcos")
        self.app.push_screen(InboxScreen(current_user=user, config=self.config))

    def action_open_ai(self) -> None:
        self.app.push_screen(AIScreen(config=self.config))

    @work(thread=True)
    def action_run_security(self) -> None:
        log = self.query_one(RichLog)
        status = self.query_one("#main_status", Label)
        self.app.call_from_thread(
            status.update, " [•] Running security verification tests against proxy..."
        )
        self.app.call_from_thread(
            log.write, format_section_header("Running Security Verification Suite")
        )

        try:
            h_ok = self.tester.test_security_headers()
            a_ok = self.tester.test_access_control()
            r_ok = self.tester.test_rate_limiting()
            if h_ok and a_ok and r_ok:
                self.app.call_from_thread(
                    log.write, format_status_ok("All security checks passed successfully!")
                )
            else:
                self.app.call_from_thread(
                    log.write, format_status_err("Some security checks failed.")
                )
        except Exception as err:
            self.app.call_from_thread(
                log.write, format_system_event(f"Security check error: {escape(str(err))}")
            )

        self.app.call_from_thread(status.update, " Security tests completed. Ready.")

    def _run_docker_command(self, header: str, args: list[str], color: str) -> None:
        """Execute a docker compose subcommand and stream its output to the log."""
        log = self.query_one(RichLog)
        self.app.call_from_thread(log.write, format_section_header(header))
        try:
            res = subprocess.run(
                ["docker", "compose", *args],
                capture_output=True,
                text=True,
                check=False,
            )
            output = res.stdout.strip() or res.stderr.strip()
            for line in output.splitlines():
                self.app.call_from_thread(log.write, f"[{color}]{escape(line)}[/]")
        except Exception as err:
            self.app.call_from_thread(
                log.write, format_system_event(f"Command error: {escape(str(err))}")
            )

    @work(thread=True)
    def action_view_audit(self) -> None:
        self._run_docker_command(
            "Recent Nginx Audit Logs (last 10 entries)",
            ["logs", "--tail=10", "reverse-proxy"],
            f"dim {COLOR_MUTED}",
        )

    @work(thread=True)
    def action_view_containers(self) -> None:
        self._run_docker_command("Docker Container Status", ["ps"], COLOR_FOREGROUND)

    @work(thread=True)
    def action_run_tests(self) -> None:
        log = self.query_one(RichLog)
        status = self.query_one("#main_status", Label)
        self.app.call_from_thread(status.update, " [•] Running full end-to-end proxy test suite...")
        self.app.call_from_thread(
            log.write, format_section_header("Running 7 End-to-End Proxy Verification Tests")
        )

        try:
            all_ok = self.tester.run_all()
            if all_ok:
                self.app.call_from_thread(
                    log.write, format_status_ok("All 7 verification tests passed!")
                )
            else:
                self.app.call_from_thread(log.write, format_status_err("Some tests failed."))
        except Exception as err:
            self.app.call_from_thread(
                log.write, format_system_event(f"Test suite error: {escape(str(err))}")
            )

        self.app.call_from_thread(status.update, " Tests completed. Ready.")

    def action_exit_app(self) -> None:
        self.app.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw_text = event.value.strip()
        if not raw_text:
            return

        event.input.value = ""
        self.record_input_history(raw_text)
        if self.handle_common_command(raw_text):
            return

        cmd = raw_text.lstrip("/").lower()
        if cmd in ("1", "chat"):
            self.action_open_chat()
        elif cmd in ("2", "ai"):
            self.action_open_ai()
        elif cmd in ("3", "security"):
            self.action_run_security()
        elif cmd in ("4", "audit"):
            self.action_view_audit()
        elif cmd in ("5", "status", "ps", "containers"):
            self.action_view_containers()
        elif cmd in ("6", "test", "tests"):
            self.action_run_tests()
        elif cmd in ("exit", "quit", "q"):
            self.action_exit_app()
        else:
            log = self.query_one(RichLog)
            log.write(
                format_system_event(
                    f"Unknown command '{escape(raw_text)}'. Type /help or select [1-6]."
                )
            )
