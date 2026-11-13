from textual.app import App

from .main_screen import MainScreen
from .theme import OLLAMA_THEME, TUI_CSS


class ProxyApp(App[None]):
    """Unified, minimalist terminal interface for the Nginx Reverse Proxy project."""

    CSS = TUI_CSS
    TITLE = "Nginx Reverse Proxy CLI"

    def __init__(self, initial_view: str = "main", initial_user: str = "marcos") -> None:
        super().__init__()
        self.initial_view = initial_view
        self.current_user = initial_user

    def on_mount(self) -> None:
        """Register theme and display the main dashboard screen."""
        self.register_theme(OLLAMA_THEME)
        self.theme = "ollama-dark"
        self.push_screen(MainScreen())
