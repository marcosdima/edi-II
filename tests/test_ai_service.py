from unittest.mock import MagicMock, patch

import pytest
import requests
from ai.routes import ai_bp
from flask import Flask


@pytest.fixture
def client():
    """Sets up a Flask test client for the AI microservice."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(ai_bp)
    with app.test_client() as client:
        yield client


def test_ai_health_check(client):
    """Verify health endpoint reports status and provider info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-service"
    assert "provider" in data
    assert data["offline_fallback_enabled"] is True


def test_ai_info(client):
    """Verify info endpoint returns operational metadata."""
    response = client.get("/info")
    assert response.status_code == 200
    data = response.get_json()
    assert data["service"] == "ai-service"
    assert "configuration" in data
    assert "proxy_metadata" in data


def test_generate_validation_missing_prompt(client):
    """Verify 400 Bad Request when prompt is empty or omitted."""
    res = client.post("/generate", json={})
    assert res.status_code == 400
    assert "'prompt' field is required" in res.get_json()["error"]

    res_empty = client.post("/generate", json={"prompt": "   "})
    assert res_empty.status_code == 400


def test_generate_validation_invalid_temperature(client):
    """Verify 400 Bad Request when temperature is non-numeric."""
    res = client.post("/generate", json={"prompt": "Hi", "temperature": "hot"})
    assert res.status_code == 400
    assert "numeric value" in res.get_json()["error"]


def test_generate_offline_fallback_without_key(client, monkeypatch):
    """Verify deterministic fallback when no API key is provided."""
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_OFFLINE_MODE", "false")

    res = client.post(
        "/generate",
        json={"prompt": "What is Nginx?"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    resp = data["response"]
    assert resp["is_fallback"] is True
    assert "Simulated AI Response (Offline Mode)" in resp["reply"]


def test_generate_offline_mode_forced(client, monkeypatch):
    """Verify offline mode triggers even if an API key is configured."""
    monkeypatch.setenv("AI_API_KEY", "gsk_fake_key_12345")
    monkeypatch.setenv("AI_OFFLINE_MODE", "true")

    res = client.post(
        "/generate",
        json={"prompt": "Explain reverse proxies"},
    )
    assert res.status_code == 200
    resp = res.get_json()["response"]
    assert resp["is_fallback"] is True
    assert "Offline Mode" in resp["reply"]


@patch("ai.services.requests.post")
def test_generate_online_success_mocked(mock_post, client, monkeypatch):
    """Verify online LLM generation when API provider responds successfully."""
    monkeypatch.setenv("AI_API_KEY", "gsk_valid_mock_key")
    monkeypatch.setenv("AI_OFFLINE_MODE", "false")
    monkeypatch.setenv("AI_PROVIDER", "groq")

    # Mock provider 200 OK response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "A reverse proxy directs client requests to backend servers."}}
        ]
    }
    mock_post.return_value = mock_response

    res = client.post(
        "/generate",
        json={
            "prompt": "What is a reverse proxy?",
            "system_prompt": "Answer concisely",
            "temperature": 0.5,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    resp = data["response"]
    assert resp["is_fallback"] is False
    assert "A reverse proxy directs" in resp["reply"]
    assert resp["provider"] == "groq"


@patch("ai.services.requests.post")
def test_generate_upstream_network_error_triggers_fallback(mock_post, client, monkeypatch):
    """Verify network timeouts or upstream crashes gracefully fallback without crashing."""
    monkeypatch.setenv("AI_API_KEY", "gsk_valid_mock_key")
    monkeypatch.setenv("AI_OFFLINE_MODE", "false")

    # Simulate network timeout
    mock_post.side_effect = requests.RequestException("Connection timed out")

    res = client.post(
        "/generate",
        json={"prompt": "Explain load balancing"},
    )
    assert res.status_code == 200
    resp = res.get_json()["response"]
    assert resp["is_fallback"] is True
    assert "Fallback AI Response - Upstream Provider Unavailable" in resp["reply"]
