from textual.app import App

from ..config import ProxyConfig, get_proxy_config
from .chat_screen import ChatScreen
from .theme import OLLAMA_THEME, TUI_CSS


class ChatApp(App[None]):
    """Standalone Chat application wrapping ChatScreen."""

    CSS = TUI_CSS
    TITLE = "Reverse Proxy Chat"

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

    def on_mount(self) -> None:
        """Register dark theme and display the chat screen."""
        self.register_theme(OLLAMA_THEME)
        self.theme = "ollama-dark"
        self.push_screen(
            ChatScreen(
                conv_id=self.conv_id,
                title=self.conv_title,
                current_user=self.current_user,
                config=self.config,
            )
        )
