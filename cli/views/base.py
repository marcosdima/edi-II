import cmd
import os
from typing import Any

import requests
import urllib3

from ..config import Colors, get_proxy_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaseView(cmd.Cmd):
    """Base class for interactive CLI views."""

    def __init__(self) -> None:
        super().__init__()
        self.config = get_proxy_config()

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
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.get(url, verify=False, timeout=timeout)
        except requests.RequestException as err:
            print(Colors.err(f"Request failed: {err}"))
            return None

    def api_post(
        self, endpoint: str, data: dict[str, Any], timeout: int = 30
    ) -> requests.Response | None:
        """Helper to send a POST request with JSON payload to the reverse proxy."""
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.post(url, json=data, verify=False, timeout=timeout)
        except requests.RequestException as err:
            print(Colors.err(f"Request failed: {err}"))
            return None
