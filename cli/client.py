"""Shared HTTP client for communicating with the Nginx Reverse Proxy."""

from typing import Any

import requests
import urllib3

from .config import ProxyConfig, get_proxy_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProxyClient:
    """Thin wrapper around requests for Reverse Proxy HTTPS endpoints."""

    def __init__(self, config: ProxyConfig | None = None) -> None:
        self.config = config or get_proxy_config()

    def _merge_headers(self, extra: dict[str, str] | None = None) -> dict[str, str] | None:
        merged = {**self.config.default_headers, **(extra or {})}
        return merged or None

    def get(
        self,
        endpoint: str,
        timeout: int = 8,
        headers: dict[str, str] | None = None,
    ) -> requests.Response | None:
        """Send a GET request to the reverse proxy."""
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.get(
                url, headers=self._merge_headers(headers), verify=False, timeout=timeout
            )
        except requests.RequestException:
            return None

    def head(
        self,
        endpoint: str,
        timeout: int = 5,
        *,
        use_http: bool = False,
        allow_redirects: bool = False,
        headers: dict[str, str] | None = None,
    ) -> requests.Response | None:
        """Send a HEAD request to the reverse proxy (HTTP or HTTPS)."""
        base = self.config.http_url if use_http else self.config.https_url
        url = f"{base}{endpoint}"
        try:
            return requests.head(
                url,
                headers=self._merge_headers(headers),
                allow_redirects=allow_redirects,
                verify=False,
                timeout=timeout,
            )
        except requests.RequestException:
            return None

    def post(
        self,
        endpoint: str,
        data: dict[str, Any],
        timeout: int = 15,
        headers: dict[str, str] | None = None,
    ) -> requests.Response | None:
        """Send a POST request with JSON payload to the reverse proxy."""
        url = f"{self.config.https_url}{endpoint}"
        try:
            return requests.post(
                url,
                json=data,
                headers=self._merge_headers(headers),
                verify=False,
                timeout=timeout,
            )
        except requests.RequestException:
            return None

    @staticmethod
    def safe_json(res: requests.Response | None) -> dict[str, Any]:
        """Safely parse a JSON response into a dictionary."""
        if not res:
            return {}
        try:
            data = res.json()
            return data if isinstance(data, dict) else {}
        except (ValueError, requests.exceptions.JSONDecodeError):
            return {}
