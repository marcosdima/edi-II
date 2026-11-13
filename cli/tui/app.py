from textual.app import App
from textual.screen import Screen

from .main_screen import MainScreen
from .theme import OLLAMA_THEME, TUI_CSS


class ProxyApp(App[None]):
    """Unified, minimalist terminal interface for the Nginx Reverse Proxy project."""

    CSS = TUI_CSS
    TITLE = "Nginx Reverse Proxy CLI"

    def __init__(
        self,
        initial_view: str = "main",
        initial_user: str = "marcos",
        initial_screen: Screen[None] | None = None,
    ) -> None:
        super().__init__()
        self.initial_view = initial_view
        self.current_user = initial_user
        self.initial_screen = initial_screen

    def on_mount(self) -> None:
        """Register theme and display the initial screen."""
        self.register_theme(OLLAMA_THEME)
        self.theme = "ollama-dark"
        self.push_screen(self.initial_screen or MainScreen())
