import subprocess
from unittest.mock import MagicMock, patch

import requests

from cli.config import get_proxy_config
from cli.manager import DockerManager
from cli.terminal import build_parser
from cli.tester import ProxyTester


def test_proxy_config_default_ports(monkeypatch):
    """Verify default ports resolve to 80 and 443 without trailing port numbers."""
    monkeypatch.delenv("PROXY_HTTP_PORT", raising=False)
    monkeypatch.delenv("PROXY_HTTPS_PORT", raising=False)

    cfg = get_proxy_config()
    assert cfg.http_port == 80
    assert cfg.https_port == 443
    assert cfg.http_url == "http://localhost"
    assert cfg.https_url == "https://localhost"


def test_proxy_config_custom_ports(monkeypatch):
    """Verify custom ports are properly appended to target URLs."""
    monkeypatch.setenv("PROXY_HTTP_PORT", "8080")
    monkeypatch.setenv("PROXY_HTTPS_PORT", "8443")

    cfg = get_proxy_config()
    assert cfg.http_port == 8080
    assert cfg.https_port == 8443
    assert cfg.http_url == "http://localhost:8080"
    assert cfg.https_url == "https://localhost:8443"


@patch("cli.manager.subprocess.run")
@patch("cli.manager.shutil.which")
def test_docker_manager_start(mock_which, mock_run):
    """Verify DockerManager.start calls docker compose up -d."""
    mock_which.return_value = "/usr/bin/docker"
    mock_run.return_value = subprocess.CompletedProcess(
        ["docker", "compose", "up", "-d"], 0, "", ""
    )

    code = DockerManager.start(build=False)
    assert code == 0
    mock_run.assert_any_call(
        ["docker", "compose", "up", "-d"],
        text=True,
        capture_output=False,
        check=False,
    )


@patch("cli.tester.requests.head")
def test_proxy_tester_redirect_success(mock_head):
    """Verify test_http_redirect succeeds when receiving 301 to https."""
    mock_res = MagicMock()
    mock_res.status_code = 301
    mock_res.headers = {"Location": "https://localhost/api/chat/health"}
    mock_head.return_value = mock_res

    tester = ProxyTester()
    assert tester.test_http_redirect() is True


@patch("cli.tester.requests.head")
def test_proxy_tester_redirect_failure(mock_head):
    """Verify test_http_redirect fails when server returns 200 or connection error."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_head.return_value = mock_res

    tester = ProxyTester()
    assert tester.test_http_redirect() is False

    mock_head.side_effect = requests.RequestException("Offline")
    assert tester.test_http_redirect() is False


@patch("cli.tester.requests.get")
def test_proxy_tester_gateway_root(mock_get):
    """Verify gateway root test handles 200 OK."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.text = '{"status":"active"}'
    mock_get.return_value = mock_res

    tester = ProxyTester()
    assert tester.test_gateway_root() is True


def test_cli_parser():
    """Verify CLI argument parser correctly parses subcommands."""
    parser = build_parser()

    args_status = parser.parse_args(["status"])
    assert args_status.command == "status"

    args_up = parser.parse_args(["up", "--build"])
    assert args_up.command == "up"
    assert args_up.build is True

    args_ai = parser.parse_args(["ai", "What", "is", "Nginx?"])
    assert args_ai.command == "ai"
    assert args_ai.prompt == ["What", "is", "Nginx?"]

    args_sec = parser.parse_args(["security"])
    assert args_sec.command == "security"

    args_aud = parser.parse_args(["audit", "--tail", "15"])
    assert args_aud.command == "audit"
    assert args_aud.tail == 15


@patch("cli.tester.requests.get")
def test_proxy_tester_security_headers(mock_get):
    """Verify security headers validation logic."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.headers = {
        "Server": "nginx",
        "X-Frame-Options": "SAMEORIGIN",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
    }
    mock_get.return_value = mock_res

    tester = ProxyTester()
    assert tester.test_security_headers() is True


@patch("cli.tester.requests.get")
def test_proxy_tester_access_control(mock_get):
    """Verify perimeter access control tests for GeoIP and IP blocks."""
    tester = ProxyTester()

    # Blocked requests return 403, legitimate return 200
    mock_403 = MagicMock(status_code=403)
    mock_200 = MagicMock(status_code=200)
    mock_get.side_effect = [mock_403, mock_403, mock_200]

    assert tester.test_access_control() is True


@patch("cli.tester.requests.get")
def test_proxy_tester_rate_limiting(mock_get):
    """Verify rate limiting detection under burst traffic."""
    tester = ProxyTester()

    # Mock 10 allowed (200) followed by 15 rate-limited (429)
    mock_responses = [MagicMock(status_code=200) for _ in range(10)] + [
        MagicMock(status_code=429) for _ in range(15)
    ]
    mock_get.side_effect = mock_responses

    assert tester.test_rate_limiting() is True
