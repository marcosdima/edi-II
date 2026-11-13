import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

# Ensure .env is loaded
load_dotenv(find_dotenv(usecwd=True))


class Colors:
    """ANSI color escape codes for terminal formatting (minimalist monochrome)."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    @classmethod
    def ok(cls, text: str) -> str:
        return f"{cls.BOLD}✓ {text}{cls.RESET}"

    @classmethod
    def err(cls, text: str) -> str:
        return f"{cls.BOLD}✗ {text}{cls.RESET}"

    @classmethod
    def info(cls, text: str) -> str:
        return f"{cls.DIM}• {text}{cls.RESET}"

    @classmethod
    def warn(cls, text: str) -> str:
        return f"{cls.BOLD}! {text}{cls.RESET}"

    @classmethod
    def header(cls, text: str) -> str:
        return f"\n{cls.BOLD}─── {text} ───{cls.RESET}"


@dataclass
class ProxyConfig:
    """Holds target URLs and port configuration for the Reverse Proxy."""

    http_port: int
    https_port: int
    http_url: str
    https_url: str

    @property
    def wss_url(self) -> str:
        """WebSocket Secure base URL derived from https_url."""
        return self.https_url.replace("https://", "wss://", 1)


def get_proxy_config() -> ProxyConfig:
    """Resolves proxy URLs based on environment variables or defaults."""
    raw_http = os.getenv("PROXY_HTTP_PORT", "80").strip()
    raw_https = os.getenv("PROXY_HTTPS_PORT", "443").strip()

    try:
        http_port = int(raw_http)
    except ValueError:
        http_port = 80

    try:
        https_port = int(raw_https)
    except ValueError:
        https_port = 443

    http_url = "http://localhost" if http_port == 80 else f"http://localhost:{http_port}"
    https_url = "https://localhost" if https_port == 443 else f"https://localhost:{https_port}"

    return ProxyConfig(
        http_port=http_port,
        https_port=https_port,
        http_url=http_url,
        https_url=https_url,
    )
