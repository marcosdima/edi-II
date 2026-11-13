import subprocess

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Label, RichLog

from ..config import ProxyConfig, get_proxy_config
from ..tester import ProxyTester
from .ai_screen import AIScreen
from .inbox_screen import InboxScreen
from .theme import format_card, format_system_event


class MainScreen(Screen[None]):
    """Main dashboard menu screen unified with the dark minimalist aesthetic."""

    BINDINGS = [
        Binding("1", "open_chat", "Chat", show=False),
        Binding("2", "open_ai", "AI", show=False),
        Binding("3", "run_security", "Security", show=False),
        Binding("4", "view_audit", "Audit", show=False),
        Binding("5", "view_containers", "Containers", show=False),
        Binding("6", "run_tests", "Test", show=False),
        Binding("escape", "exit_app", "Exit", show=False),
        Binding("ctrl+q", "exit_app", "Quit", show=False),
    ]

    def __init__(self, config: ProxyConfig | None = None) -> None:
        super().__init__()
        self.config = config or get_proxy_config()
        self.tester = ProxyTester()

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label("Final: Edi II", classes="tui-header-title"),
            Label("Proxy Reverso - Nginx", classes="tui-header-meta"),
            classes="tui-header",
        )
        yield Vertical(
            RichLog(
                classes="tui-log", id="main_log", highlight=False, markup=True, auto_scroll=True
            ),
            classes="tui-content",
        )
        with Vertical(classes="tui-bottom-panel"):
            with Vertical(classes="tui-input-wrapper"):
                yield Input(
                    placeholder="Select [1-6] or type: chat, ai, test, security, audit, status, exit...",
                    classes="tui-input",
                    id="main_input",
                )
                yield Label(
                    " [1] Chat  •  [2] AI  •  [3] Security  •  [4] Audit  •  [5] Containers  •  [6] Test  •  [Esc] Exit",
                    classes="tui-status-bar",
                    id="main_status",
                )

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self.print_dashboard()

    def print_dashboard(self) -> None:
        log = self.query_one(RichLog)
        log.clear()
        log.write("[bold #ffffff]Final: Edi II[/]")
        log.write("[dim #737373]Proxy Reverso - Nginx[/]\n")

        log.write(
            format_card(
                "CHAT SYSTEM", "[1]", "Multi-user chat with SQLite persistence and directives"
            )
        )
        log.write(
            format_card("AI ASSISTANT", "[2]", "Groq LLM completions with offline fallback mode")
        )
        log.write(
            format_card(
                "SECURITY SUITE", "[3]", "Perimeter access control (GeoIP) and Rate Limiting (429)"
            )
        )
        log.write(
            format_card(
                "AUDIT LOGS", "[4]", "Live Nginx traffic logging with latency and TLS ciphers"
            )
        )
        log.write(
            format_card("CONTAINERS", "[5]", "Inspect Docker compose container status and health")
        )
        log.write(
            format_card("FULL TEST SUITE", "[6]", "Run 7 end-to-end automated verification tests")
        )
        log.write("")

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
            log.write, "\n[bold #ffffff]─── Running Security Verification Suite ───[/]"
        )

        try:
            h_ok = self.tester.test_security_headers()
            a_ok = self.tester.test_access_control()
            r_ok = self.tester.test_rate_limiting()
            if h_ok and a_ok and r_ok:
                self.app.call_from_thread(
                    log.write, "[bold #ffffff]✓ All security checks passed successfully![/]"
                )
            else:
                self.app.call_from_thread(
                    log.write, "[bold #ffffff]✗ Some security checks failed.[/]"
                )
        except Exception as err:
            self.app.call_from_thread(
                log.write, format_system_event(f"Security check error: {escape(str(err))}")
            )

        self.app.call_from_thread(status.update, " Security tests completed. Ready.")

    @work(thread=True)
    def action_view_audit(self) -> None:
        log = self.query_one(RichLog)
        self.app.call_from_thread(
            log.write, "\n[bold #ffffff]─── Recent Nginx Audit Logs (last 10 entries) ───[/]"
        )
        try:
            res = subprocess.run(
                ["docker", "compose", "logs", "--tail=10", "reverse-proxy"],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in res.stdout.strip().splitlines():
                self.app.call_from_thread(log.write, f"[dim #737373]{escape(line)}[/]")
        except Exception as err:
            self.app.call_from_thread(
                log.write, format_system_event(f"Error fetching logs: {escape(str(err))}")
            )

    @work(thread=True)
    def action_view_containers(self) -> None:
        log = self.query_one(RichLog)
        self.app.call_from_thread(log.write, "\n[bold #ffffff]─── Docker Container Status ───[/]")
        try:
            res = subprocess.run(
                ["docker", "compose", "ps"],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in res.stdout.strip().splitlines():
                self.app.call_from_thread(log.write, f"[#e5e5e5]{escape(line)}[/]")
        except Exception as err:
            self.app.call_from_thread(
                log.write, format_system_event(f"Error checking containers: {escape(str(err))}")
            )

    @work(thread=True)
    def action_run_tests(self) -> None:
        log = self.query_one(RichLog)
        status = self.query_one("#main_status", Label)
        self.app.call_from_thread(status.update, " [•] Running full end-to-end proxy test suite...")
        self.app.call_from_thread(
            log.write, "\n[bold #ffffff]─── Running 7 End-to-End Proxy Verification Tests ───[/]"
        )

        try:
            all_ok = self.tester.run_all()
            if all_ok:
                self.app.call_from_thread(
                    log.write, "[bold #ffffff]✓ All 7 verification tests passed![/]"
                )
            else:
                self.app.call_from_thread(log.write, "[bold #ffffff]✗ Some tests failed.[/]")
        except Exception as err:
            self.app.call_from_thread(
                log.write, format_system_event(f"Test suite error: {escape(str(err))}")
            )

        self.app.call_from_thread(status.update, " Tests completed. Ready.")

    def action_exit_app(self) -> None:
        self.app.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip().lower()
        if not text:
            return

        event.input.value = ""

        if text in ("1", "chat"):
            self.action_open_chat()
        elif text in ("2", "ai"):
            self.action_open_ai()
        elif text in ("3", "security"):
            self.action_run_security()
        elif text in ("4", "audit"):
            self.action_view_audit()
        elif text in ("5", "status", "ps", "containers"):
            self.action_view_containers()
        elif text in ("6", "test", "tests"):
            self.action_run_tests()
        elif text in ("exit", "quit", "q"):
            self.action_exit_app()
        elif text in ("clear", "cls"):
            self.print_dashboard()
        else:
            log = self.query_one(RichLog)
            log.write(
                format_system_event(
                    f"Unknown command '{escape(text)}'. Type [1-6], chat, ai, test, security, or exit."
                )
            )
