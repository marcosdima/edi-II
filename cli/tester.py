import time

import requests
import urllib3

from .config import Colors, get_proxy_config

# Suppress self-signed certificate warnings when querying localhost over TLS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProxyTester:
    """Performs HTTP and HTTPS verification tests against the Nginx Reverse Proxy."""

    def __init__(self) -> None:
        self.config = get_proxy_config()

    def test_http_redirect(self) -> bool:
        """Tests that insecure HTTP traffic is redirected with 301 to HTTPS."""
        print(Colors.header("Test 1: HTTP -> HTTPS Redirection (Port 80)"))
        target = f"{self.config.http_url}/api/chat/health"
        print(Colors.info(f"Sending HEAD request to {target} (allow_redirects=False)..."))

        try:
            res = requests.head(target, allow_redirects=False, timeout=5)
            print(f"Status Code: {Colors.BOLD}{res.status_code}{Colors.RESET}")
            location = res.headers.get("Location", "None")
            print(f"Location Header: {location}")

            if res.status_code == 301 and location.startswith("https://"):
                print(
                    Colors.ok(
                        "HTTP to HTTPS redirection working as expected (301 Moved Permanently)."
                    )
                )
                return True
            else:
                print(Colors.err(f"Unexpected response code {res.status_code}."))
                return False
        except requests.RequestException as err:
            print(Colors.err(f"Connection failed: {err}"))
            return False

    def test_gateway_root(self) -> bool:
        """Tests gateway root overview endpoint."""
        print(Colors.header("Test 2: Gateway Root Endpoint (Port 443)"))
        target = f"{self.config.https_url}/"
        print(Colors.info(f"Sending GET request to {target}..."))

        try:
            start = time.perf_counter()
            res = requests.get(target, verify=False, timeout=5)
            latency = round((time.perf_counter() - start) * 1000, 2)

            print(f"Status: {Colors.BOLD}{res.status_code}{Colors.RESET} ({latency} ms)")
            print(f"Response: {res.text.strip()}")

            if res.status_code == 200:
                print(Colors.ok("Gateway status endpoint reachable via HTTPS."))
                return True
            return False
        except requests.RequestException as err:
            print(Colors.err(f"Gateway connection failed: {err}"))
            return False

    def test_chat_service(self) -> bool:
        """Executes full Chat microservice workflow through the Reverse Proxy."""
        print(Colors.header("Test 3: Chat Service Workflow via /api/chat/"))

        # 1. User Registration & Health Check
        reg_url = f"{self.config.https_url}/api/chat/auth/register"
        print(Colors.info(f"1. Registering test users at {reg_url}..."))
        try:
            requests.post(
                reg_url,
                json={"username": "marcos", "display_name": "Marcos Di Matteo"},
                verify=False,
                timeout=5,
            )
            requests.post(
                reg_url,
                json={"username": "profe", "display_name": "Profesor Linux"},
                verify=False,
                timeout=5,
            )
            u_res = requests.get(f"{self.config.https_url}/api/chat/users", verify=False, timeout=5)
            if u_res.status_code == 200:
                total_u = u_res.json().get("total_users", 0)
                print(Colors.ok(f"Users registered and verified ({total_u} active users)."))
            else:
                print(Colors.warn("User listing returned non-200 status."))
        except requests.RequestException as err:
            print(Colors.err(f"User registration error: {err}"))
            return False

        # 2. Health Check
        health_url = f"{self.config.https_url}/api/chat/health"
        print(Colors.info(f"2. Checking Chat Health: {health_url}"))
        try:
            h_res = requests.get(health_url, verify=False, timeout=5)
            if h_res.status_code != 200:
                print(Colors.err(f"Chat health check failed: {h_res.status_code}"))
                return False
            print(Colors.ok("Chat service reports healthy."))
        except requests.RequestException as err:
            print(Colors.err(f"Failed to reach chat service: {err}"))
            return False

        # 3. Create Conversation
        conv_url = f"{self.config.https_url}/api/chat/conversations"
        payload = {"title": "CLI Integration Test", "participants": ["marcos", "profe"]}
        print(Colors.info(f"3. Creating conversation: POST {conv_url}"))
        try:
            c_res = requests.post(conv_url, json=payload, verify=False, timeout=5)
            if c_res.status_code != 201:
                print(Colors.err(f"Failed to create conversation: {c_res.text}"))
                return False
            c_data = c_res.json()
            conv_id = c_data["conversation_id"]
            print(
                Colors.ok(
                    f"Conversation #{conv_id} created. Forwarded Proto: {c_data.get('proxy_metadata', {}).get('forwarded_proto')}"
                )
            )
        except requests.RequestException as err:
            print(Colors.err(f"Create conversation error: {err}"))
            return False

        # 3. Post Message
        msg_url = f"{self.config.https_url}/api/chat/conversations/{conv_id}/messages"
        msg_payload = {"sender": "marcos", "content": "Message sent via CLI proxy test"}
        print(Colors.info(f"3. Posting message: POST {msg_url}"))
        try:
            m_res = requests.post(msg_url, json=msg_payload, verify=False, timeout=5)
            if m_res.status_code != 201:
                print(Colors.err(f"Failed to post message: {m_res.text}"))
                return False
            print(Colors.ok("Chat message persisted to SQLite via proxy."))
        except requests.RequestException as err:
            print(Colors.err(f"Post message error: {err}"))
            return False

        # 4. Execute Directive
        print(Colors.info("4. Testing directive /members (should not persist as message)"))
        try:
            d_res = requests.post(
                msg_url,
                json={"sender": "marcos", "content": "/members"},
                verify=False,
                timeout=5,
            )
            d_data = d_res.json()
            if d_res.status_code == 200 and d_data.get("type") == "system_directive":
                members = [m["username"] for m in d_data.get("members", [])]
                print(Colors.ok(f"Directive executed. Participants: {members}"))
            else:
                print(Colors.err("Directive execution failed."))
                return False
        except requests.RequestException as err:
            print(Colors.err(f"Directive error: {err}"))
            return False

        # 5. Fetch Messages
        print(Colors.info(f"5. Fetching messages: GET {msg_url}"))
        try:
            list_res = requests.get(msg_url, verify=False, timeout=5)
            msgs = list_res.json().get("messages", [])
            print(
                Colors.ok(
                    f"Retrieved {len(msgs)} persistent messages (system directives excluded)."
                )
            )
        except requests.RequestException as err:
            print(Colors.err(f"Get messages error: {err}"))
            return False

        print(Colors.ok("Full Chat Service workflow passed through Reverse Proxy."))
        return True

    def test_ai_service(self, prompt: str = "Explain reverse proxy in 1 sentence") -> bool:
        """Executes AI generation through the Reverse Proxy."""
        print(Colors.header("Test 4: AI Service Completion via /api/ai/"))

        # 1. Health & Info
        info_url = f"{self.config.https_url}/api/ai/info"
        print(Colors.info(f"Checking AI service configuration: GET {info_url}"))
        try:
            i_res = requests.get(info_url, verify=False, timeout=5)
            if i_res.status_code == 200:
                cfg = i_res.json().get("configuration", {})
                print(
                    f"Provider: {Colors.BOLD}{cfg.get('provider')}{Colors.RESET} | "
                    f"Model: {Colors.BOLD}{cfg.get('default_model')}{Colors.RESET} | "
                    f"API Key: {cfg.get('api_key_configured')}"
                )
            else:
                print(Colors.warn("Could not retrieve AI configuration info."))
        except requests.RequestException as err:
            print(Colors.err(f"Failed to reach AI service: {err}"))
            return False

        # 2. Generation Request
        gen_url = f"{self.config.https_url}/api/ai/generate"
        payload = {"prompt": prompt}
        print(Colors.info(f"Sending prompt to AI via proxy: '{prompt}'"))

        try:
            start = time.perf_counter()
            res = requests.post(gen_url, json=payload, verify=False, timeout=30)
            elapsed = round((time.perf_counter() - start) * 1000, 2)

            if res.status_code != 200:
                print(Colors.err(f"AI generation failed: HTTP {res.status_code} - {res.text}"))
                return False

            data = res.json()
            resp = data.get("response", {})
            reply = resp.get("reply", "").strip()
            is_fallback = resp.get("is_fallback", False)
            model = resp.get("model", "unknown")
            latency = resp.get("latency_ms", elapsed)

            print(f"\n{Colors.BOLD}Model:{Colors.RESET} {model}")
            print(f"{Colors.BOLD}Latency:{Colors.RESET} {latency} ms (Roundtrip: {elapsed} ms)")
            print(
                f"{Colors.BOLD}Mode:{Colors.RESET} {'Fallback/Simulated' if is_fallback else 'Online Provider'}"
            )
            print(f"\n{Colors.BOLD}AI Response:{Colors.RESET}\n{reply}\n")

            print(Colors.ok("AI request successfully routed through Reverse Proxy."))
            return True
        except requests.RequestException as err:
            print(Colors.err(f"AI generation request error: {err}"))
            return False

    def run_all(self) -> bool:
        """Runs the entire suite of verification tests."""
        print(
            f"\n{Colors.BOLD}{Colors.MAGENTA}========================================{Colors.RESET}"
        )
        print(
            f"{Colors.BOLD}{Colors.MAGENTA}  Starting Reverse Proxy End-to-End Suite {Colors.RESET}"
        )
        print(
            f"{Colors.BOLD}{Colors.MAGENTA}========================================{Colors.RESET}"
        )
        print(f"Target Proxy HTTPS URL: {Colors.CYAN}{self.config.https_url}{Colors.RESET}")
        print(f"Target Proxy HTTP URL:  {Colors.CYAN}{self.config.http_url}{Colors.RESET}")

        results: list[tuple[str, bool]] = [
            ("HTTP -> HTTPS Redirection", self.test_http_redirect()),
            ("Gateway Root Endpoint", self.test_gateway_root()),
            ("Chat Service Workflow", self.test_chat_service()),
            ("AI Completion Service", self.test_ai_service()),
        ]

        print(Colors.header("Test Results Summary"))
        all_passed = True
        for name, passed in results:
            badge = Colors.ok("PASSED") if passed else Colors.err("FAILED")
            print(f"  {name:<30} {badge}")
            if not passed:
                all_passed = False

        print(f"\n{Colors.BOLD}{'=' * 40}{Colors.RESET}")
        if all_passed:
            print(Colors.ok("All end-to-end proxy verification tests passed!"))
        else:
            print(Colors.err("Some verification tests failed. Inspect logs with 'cli logs'."))
        return all_passed
