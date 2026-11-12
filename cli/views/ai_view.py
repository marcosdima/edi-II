from typing import Any

from ..config import Colors
from .base import BaseView


class AIView(BaseView):
    """Interactive view for AI completions and LLM management."""

    def __init__(self) -> None:
        super().__init__()
        self.provider: str = "unknown"
        self.default_model: str = "loading..."
        self.current_model: str | None = None
        self.system_prompt: str | None = None
        self.temperature: float = 0.7
        self.api_key_configured: bool = False
        self.update_prompt()

    def get_active_model(self) -> str:
        """Returns the currently active model name."""
        return self.current_model or self.default_model

    def update_prompt(self) -> None:
        """Updates the command prompt with the active model."""
        active = self.get_active_model()
        self.prompt = f"{Colors.BOLD}{Colors.YELLOW}proxy-cli [ai:{active}]>{Colors.RESET} "

    def fetch_info(self) -> dict[str, Any] | None:
        """Fetches service configuration from /api/ai/info."""
        res = self.api_get("/api/ai/info")
        if res and res.status_code == 200:
            return res.json()
        return None

    def preloop(self) -> None:
        """Initializes view and fetches service status on entry."""
        data = self.fetch_info()
        if data:
            cfg = data.get("configuration", {})
            self.provider = cfg.get("provider", "unknown")
            self.default_model = cfg.get("default_model", "unknown")
            self.api_key_configured = cfg.get("api_key_configured", False)

        self.update_prompt()

        print(f"\n{Colors.BOLD}{Colors.YELLOW}=== AI Completion Assistant ==={Colors.RESET}")
        print(
            f"Provider: {Colors.BOLD}{self.provider}{Colors.RESET} | "
            f"Model: {Colors.BOLD}{self.get_active_model()}{Colors.RESET} | "
            f"API Key: {'Configured' if self.api_key_configured else 'Missing (Fallback)'}"
        )
        print(
            Colors.info(
                "Commands: 'model <name>', 'sys <prompt>', 'temp <val>', 'info', 'clear', 'back'"
            )
        )
        print(Colors.info("Type any question or prompt directly to generate an answer.\n"))

    def default(self, line: str) -> None:
        """Any text entered is sent to the AI service as a generation prompt."""
        text = line.strip()
        if not text:
            return

        payload: dict[str, Any] = {
            "prompt": text,
            "temperature": self.temperature,
        }
        if self.current_model:
            payload["model"] = self.current_model
        if self.system_prompt:
            payload["system_prompt"] = self.system_prompt

        print(f"{Colors.DIM}Sending prompt to {self.get_active_model()}...{Colors.RESET}")
        res = self.api_post("/api/ai/generate", payload, timeout=60)
        if not res:
            return

        if res.status_code != 200:
            print(Colors.err(f"AI generation failed (HTTP {res.status_code}): {res.text}"))
            return

        data = res.json()
        resp = data.get("response", {})
        reply = resp.get("reply", "").strip()
        is_fallback = resp.get("is_fallback", False)
        model = resp.get("model", self.get_active_model())
        latency = resp.get("latency_ms", 0.0)

        status_tag = (
            f"{Colors.YELLOW}[FALLBACK / OFFLINE]{Colors.RESET}"
            if is_fallback
            else f"{Colors.GREEN}[ONLINE: {model}]{Colors.RESET}"
        )

        print(f"\n{status_tag} {Colors.DIM}(latency: {latency} ms){Colors.RESET}")
        print(f"{Colors.BOLD}{reply}{Colors.RESET}\n")

    def do_model(self, arg: str) -> None:
        """Change active model or reset to default: model [name | reset]"""
        target = arg.strip()
        if not target or target.lower() == "reset":
            self.current_model = None
            print(Colors.ok(f"Reset model to default: '{self.default_model}'"))
        else:
            self.current_model = target
            print(Colors.ok(f"Active model overridden to: '{self.current_model}'"))
        self.update_prompt()

    def do_sys(self, arg: str) -> None:
        """Set or inspect the system prompt: sys [prompt | reset]"""
        target = arg.strip()
        if not target:
            current = self.system_prompt or "None (default sysadmin assistant)"
            print(f"Current system prompt: {Colors.CYAN}{current}{Colors.RESET}")
            return

        if target.lower() in ("reset", "clear", "none"):
            self.system_prompt = None
            print(Colors.ok("System prompt cleared."))
        else:
            self.system_prompt = target
            print(Colors.ok(f"System prompt set to: '{self.system_prompt}'"))

    def do_temp(self, arg: str) -> None:
        """Set generation temperature (0.0 to 2.0): temp <value>"""
        target = arg.strip()
        if not target:
            print(f"Current temperature: {Colors.CYAN}{self.temperature}{Colors.RESET}")
            return

        try:
            val = float(target)
            if not 0.0 <= val <= 2.0:
                print(Colors.err("Temperature must be between 0.0 and 2.0."))
                return
            self.temperature = val
            print(Colors.ok(f"Temperature set to {self.temperature}."))
        except ValueError:
            print(Colors.err("Invalid number. Usage: temp <0.0 - 2.0>"))

    def do_info(self, arg: str) -> None:
        """Show full AI provider and proxy metadata details: info"""
        data = self.fetch_info()
        if not data:
            print(Colors.err("Failed to fetch info from AI service."))
            return

        cfg = data.get("configuration", {})
        meta = data.get("proxy_metadata", {})

        print(Colors.header("AI Service Configuration"))
        print(f"  Provider:         {Colors.BOLD}{cfg.get('provider')}{Colors.RESET}")
        print(f"  Default Model:    {cfg.get('default_model')}")
        print(f"  Current Model:    {self.get_active_model()}")
        print(f"  API Endpoint:     {cfg.get('endpoint')}")
        print(f"  API Key Active:   {cfg.get('api_key_configured')}")
        print(f"  Offline Fallback: {cfg.get('offline_fallback_enabled')}")
        print(f"  Temperature:      {self.temperature}")
        print(f"  System Prompt:    {self.system_prompt or 'None'}")

        print(Colors.header("Reverse Proxy Metadata (Injected Headers)"))
        print(f"  Client IP (X-Real-IP): {meta.get('client_ip')}")
        print(f"  Proto (X-Forwarded):   {meta.get('forwarded_proto')}")
        print(f"  Country (GeoIP):       {meta.get('country')}")
