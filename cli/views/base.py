import cmd
import os
from typing import Any

import requests

from ..client import ProxyClient
from ..config import Colors, get_proxy_config


class BaseView(cmd.Cmd):
    """Base class for interactive CLI views."""

    def __init__(self) -> None:
        super().__init__()
        self.config = get_proxy_config()
        self.client = ProxyClient(self.config)

    def do_clear(self, arg: str) -> None:
        """Clear the terminal screen: clear"""
        os.system("clear")

    def do_back(self, arg: str) -> bool:
        """Return to the previous view: back"""
        return True

    def do_exit(self, arg: str) -> bool:
        """Return to the previous view: exit"""
        return self.do_back(arg)

    def do_quit(self, arg: str) -> bool:
        """Return to the previous view: quit"""
        return self.do_back(arg)

    def do_EOF(self, arg: str) -> bool:
        """Handle Ctrl+D to return cleanly."""
        print()
        return self.do_back(arg)

    def emptyline(self) -> bool:
        """Do nothing on empty line entry."""
        return False

    def api_get(self, endpoint: str, timeout: int = 10) -> requests.Response | None:
        """Helper to send a GET request to the reverse proxy."""
        res = self.client.get(endpoint, timeout=timeout)
        if res is None:
            print(Colors.err("Request failed: unable to reach reverse proxy."))
        return res

    def api_post(
        self, endpoint: str, data: dict[str, Any], timeout: int = 30
    ) -> requests.Response | None:
        """Helper to send a POST request with JSON payload to the reverse proxy."""
        res = self.client.post(endpoint, data, timeout=timeout)
        if res is None:
            print(Colors.err("Request failed: unable to reach reverse proxy."))
        return res
