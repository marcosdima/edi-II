import os
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import requests
from dotenv import find_dotenv, load_dotenv

# Load environment variables from .env if present
load_dotenv(find_dotenv(usecwd=True))


class AIProvider(StrEnum):
    GROQ = "groq"
    OPENROUTER = "openrouter"


PROVIDER_ENDPOINTS = {
    AIProvider.GROQ: "https://api.groq.com/openai/v1/chat/completions",
    AIProvider.OPENROUTER: "https://openrouter.ai/api/v1/chat/completions",
}

DEFAULT_MODELS = {
    AIProvider.GROQ: "llama-3.3-70b-versatile",
    AIProvider.OPENROUTER: "meta-llama/llama-3-8b-instruct:free",
}


@dataclass
class AIResponse:
    reply: str
    provider: str
    model: str
    is_fallback: bool
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "provider": self.provider,
            "model": self.model,
            "is_fallback": self.is_fallback,
            "latency_ms": self.latency_ms,
        }


class AIService:
    """Business service orchestrating AI LLM completions with automatic offline fallback."""

    @staticmethod
    def get_provider() -> AIProvider:
        raw_provider = os.getenv("AI_PROVIDER", "groq").strip().lower()
        try:
            return AIProvider(raw_provider)
        except ValueError:
            return AIProvider.GROQ

    @staticmethod
    def get_api_key() -> str:
        return os.getenv("AI_API_KEY", "").strip()

    @staticmethod
    def is_offline_mode() -> bool:
        return os.getenv("AI_OFFLINE_MODE", "false").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    @staticmethod
    def get_timeout() -> float:
        try:
            return float(os.getenv("AI_TIMEOUT_SECONDS", "10.0"))
        except ValueError:
            return 10.0

    @classmethod
    def get_service_info(cls) -> dict[str, Any]:
        provider = cls.get_provider()
        api_key = cls.get_api_key()
        return {
            "provider": provider.value,
            "default_model": os.getenv("AI_MODEL", DEFAULT_MODELS[provider]),
            "endpoint": PROVIDER_ENDPOINTS[provider],
            "api_key_configured": bool(api_key),
            "offline_fallback_enabled": True,
            "offline_mode_forced": cls.is_offline_mode(),
            "timeout_seconds": cls.get_timeout(),
        }

    @classmethod
    def generate(
        cls,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AIResponse:
        start_time = time.perf_counter()
        provider = cls.get_provider()
        selected_model = model or os.getenv("AI_MODEL") or DEFAULT_MODELS[provider]
        api_key = cls.get_api_key()
        offline_mode = cls.is_offline_mode()

        # Deterministic offline fallback if offline mode forced or API key is absent
        if offline_mode or not api_key:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            simulated_reply = (
                f"[Simulated AI Response (Offline Mode)]\n"
                f"Prompt received: '{prompt}'\n"
                f"Provider: {provider.value} | Model: {selected_model}\n"
                f"Note: Server operating in offline fallback mode."
            )
            return AIResponse(
                reply=simulated_reply,
                provider=provider.value,
                model=selected_model,
                is_fallback=True,
                latency_ms=elapsed_ms,
            )

        endpoint = PROVIDER_ENDPOINTS[provider]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider == AIProvider.OPENROUTER:
            headers["HTTP-Referer"] = "https://proyecto.local"
            headers["X-Title"] = "Reverse Proxy Final Project"

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": max(0.0, min(temperature, 2.0)),
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=cls.get_timeout(),
            )
            response.raise_for_status()
            data = response.json()
            reply_text = data["choices"][0]["message"]["content"]
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return AIResponse(
                reply=reply_text,
                provider=provider.value,
                model=selected_model,
                is_fallback=False,
                latency_ms=elapsed_ms,
            )

        except (
            requests.RequestException,
            KeyError,
            IndexError,
            ValueError,
        ) as err:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            fallback_reply = (
                f"[Fallback AI Response - Upstream Provider Unavailable]\n"
                f"Prompt: '{prompt}'\n"
                f"Provider '{provider.value}' encountered an issue: {type(err).__name__}.\n"
                f"Reverse proxy demonstration fallback engaged successfully."
            )
            return AIResponse(
                reply=fallback_reply,
                provider=provider.value,
                model=selected_model,
                is_fallback=True,
                latency_ms=elapsed_ms,
            )
