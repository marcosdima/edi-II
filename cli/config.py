import os
import shlex
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
    host: str = "localhost"

    @property
    def wss_url(self) -> str:
        """WebSocket Secure base URL derived from https_url."""
        return self.https_url.replace("https://", "wss://", 1)

    @property
    def default_headers(self) -> dict[str, str]:
        """Optional headers (auto-enabled only for ngrok tunnels or explicit env flag)."""
        skip_env = os.getenv("PROXY_NGROK_SKIP_WARNING", "").strip().lower()
        if "ngrok" in self.host.lower() or skip_env in ("1", "true", "yes"):
            return {"ngrok-skip-browser-warning": "true"}
        return {}


def get_proxy_config() -> ProxyConfig:
    """Resolves proxy URLs based on environment variables or defaults."""
    raw_host = os.getenv("PROXY_HOST", "localhost").strip()
    host = raw_host.removeprefix("https://").removeprefix("http://").rstrip("/") or "localhost"
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

    http_url = f"http://{host}" if http_port == 80 else f"http://{host}:{http_port}"
    https_url = f"https://{host}" if https_port == 443 else f"https://{host}:{https_port}"

    return ProxyConfig(
        http_port=http_port,
        https_port=https_port,
        http_url=http_url,
        https_url=https_url,
        host=host,
    )


def parse_new_conversation_args(raw: str) -> tuple[str, list[str]] | None:
    """Parse `<title> [user1,user2,...]` supporting quoted titles and spaced commas."""
    text = raw.strip()
    if not text:
        return None
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()
    if not tokens:
        return None
    if len(tokens) == 1:
        return tokens[0].strip("\"'"), []

    # Merge trailing comma-separated participant tokens (e.g. `profe, lucas`)
    idx = len(tokens) - 1
    while idx > 1 and tokens[idx - 1].endswith(","):
        idx -= 1
    users_part = "".join(tokens[idx:])
    title = " ".join(tokens[:idx]).strip("\"'")
    participants = [u.strip().lower() for u in users_part.replace(" ", "").split(",") if u.strip()]
    return title, participants
