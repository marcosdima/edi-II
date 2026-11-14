import time
from concurrent.futures import ThreadPoolExecutor

from .client import ProxyClient
from .config import Colors, get_proxy_config


class ProxyTester:
    """Performs HTTP and HTTPS verification tests against the Nginx Reverse Proxy."""

    def __init__(self) -> None:
        self.config = get_proxy_config()
        self.client = ProxyClient(self.config)

    def test_http_redirect(self) -> bool:
        """Tests that insecure HTTP traffic is redirected with 301 to HTTPS."""
        print(Colors.header("Test 1: HTTP -> HTTPS Redirection (Port 80)"))
        target = f"{self.config.http_url}/api/chat/health"
        print(Colors.info(f"Sending HEAD request to {target} (allow_redirects=False)..."))

        res = self.client.head("/api/chat/health", use_http=True, allow_redirects=False, timeout=5)
        if res is None:
            print(Colors.err("Connection failed."))
            return False

        print(f"Status Code: {Colors.BOLD}{res.status_code}{Colors.RESET}")
        location = res.headers.get("Location", "None")
        print(f"Location Header: {location}")

        if res.status_code == 301 and location.startswith("https://"):
            print(
                Colors.ok("HTTP to HTTPS redirection working as expected (301 Moved Permanently).")
            )
            return True

        print(Colors.err(f"Unexpected response code {res.status_code}."))
        return False

    def test_gateway_root(self) -> bool:
        """Tests gateway root overview endpoint."""
        print(Colors.header("Test 2: Gateway Root Endpoint (Port 443)"))
        target = f"{self.config.https_url}/"
        print(Colors.info(f"Sending GET request to {target}..."))

        start = time.perf_counter()
        res = self.client.get("/", timeout=5)
        latency = round((time.perf_counter() - start) * 1000, 2)

        if res is None:
            print(Colors.err("Gateway connection failed."))
            return False

        print(f"Status: {Colors.BOLD}{res.status_code}{Colors.RESET} ({latency} ms)")
        print(f"Response: {res.text.strip()}")

        if res.status_code == 200:
            print(Colors.ok("Gateway status endpoint reachable via HTTPS."))
            return True
        return False

    def test_chat_service(self) -> bool:
        """Executes full Chat microservice workflow through the Reverse Proxy."""
        print(Colors.header("Test 3: Chat Service Workflow via /api/chat/"))

        # 1. User Registration
        print(
            Colors.info(
                f"1. Registering test users at {self.config.https_url}/api/chat/auth/register..."
            )
        )
        r1 = self.client.post(
            "/api/chat/auth/register",
            {"username": "marcos", "display_name": "Marcos Di Matteo"},
            timeout=5,
        )
        r2 = self.client.post(
            "/api/chat/auth/register",
            {"username": "profe", "display_name": "Profesor Linux"},
            timeout=5,
        )
        u_res = self.client.get("/api/chat/users", timeout=5)
        if r1 is None or r2 is None or u_res is None:
            print(Colors.err("User registration error: unable to reach reverse proxy."))
            return False

        if u_res.status_code == 200:
            total_u = self.client.safe_json(u_res).get("total_users", 0)
            print(Colors.ok(f"Users registered and verified ({total_u} active users)."))
        else:
            print(Colors.warn("User listing returned non-200 status."))

        # 2. Health Check
        print(Colors.info(f"2. Checking Chat Health: {self.config.https_url}/api/chat/health"))
        h_res = self.client.get("/api/chat/health", timeout=5)
        if h_res is None:
            print(Colors.err("Failed to reach chat service."))
            return False
        if h_res.status_code != 200:
            print(Colors.err(f"Chat health check failed: {h_res.status_code}"))
            return False
        print(Colors.ok("Chat service reports healthy."))

        # 3. Create Conversation
        payload = {"title": "CLI Integration Test", "participants": ["marcos", "profe"]}
        print(
            Colors.info(
                f"3. Creating conversation: POST {self.config.https_url}/api/chat/conversations"
            )
        )
        c_res = self.client.post("/api/chat/conversations", payload, timeout=5)
        if c_res is None:
            print(Colors.err("Create conversation error: unable to reach reverse proxy."))
            return False
        if c_res.status_code != 201:
            print(Colors.err(f"Failed to create conversation: {c_res.text}"))
            return False
        c_data = self.client.safe_json(c_res)
        conv_id = c_data["conversation_id"]
        print(
            Colors.ok(
                f"Conversation #{conv_id} created. Forwarded Proto: {c_data.get('proxy_metadata', {}).get('forwarded_proto')}"
            )
        )

        # 4. Post Message
        msg_endpoint = f"/api/chat/conversations/{conv_id}/messages"
        msg_payload = {"sender": "marcos", "content": "Message sent via CLI proxy test"}
        print(Colors.info(f"4. Posting message: POST {self.config.https_url}{msg_endpoint}"))
        m_res = self.client.post(msg_endpoint, msg_payload, timeout=5)
        if m_res is None or m_res.status_code != 201:
            detail = m_res.text if m_res is not None else "no response"
            print(Colors.err(f"Failed to post message: {detail}"))
            return False
        print(Colors.ok("Chat message persisted to SQLite via proxy."))

        # 5. Execute Directive
        print(Colors.info("5. Testing directive /members (should not persist as message)"))
        d_res = self.client.post(
            msg_endpoint, {"sender": "marcos", "content": "/members"}, timeout=5
        )
        d_data = self.client.safe_json(d_res)
        if (
            d_res is not None
            and d_res.status_code == 200
            and d_data.get("type") == "system_directive"
        ):
            members = [m["username"] for m in d_data.get("members", [])]
            print(Colors.ok(f"Directive executed. Participants: {members}"))
        else:
            print(Colors.err("Directive execution failed."))
            return False

        # 6. Fetch Messages
        print(Colors.info(f"6. Fetching messages: GET {self.config.https_url}{msg_endpoint}"))
        list_res = self.client.get(msg_endpoint, timeout=5)
        if list_res is None or list_res.status_code != 200:
            print(Colors.err("Get messages error."))
            return False
        msgs = self.client.safe_json(list_res).get("messages", [])
        print(Colors.ok(f"Retrieved {len(msgs)} persistent messages (system directives excluded)."))

        print(Colors.ok("Full Chat Service workflow passed through Reverse Proxy."))
        return True

    def test_ai_service(self, prompt: str = "Explain reverse proxy in 1 sentence") -> bool:
        """Executes AI generation through the Reverse Proxy."""
        print(Colors.header("Test 4: AI Service Completion via /api/ai/"))

        # 1. Health & Info
        print(
            Colors.info(
                f"Checking AI service configuration: GET {self.config.https_url}/api/ai/info"
            )
        )
        i_res = self.client.get("/api/ai/info", timeout=5)
        if i_res is None:
            print(Colors.err("Failed to reach AI service."))
            return False
        if i_res.status_code == 200:
            cfg = self.client.safe_json(i_res).get("configuration", {})
            print(
                f"Provider: {Colors.BOLD}{cfg.get('provider')}{Colors.RESET} | "
                f"Model: {Colors.BOLD}{cfg.get('default_model')}{Colors.RESET} | "
                f"API Key: {cfg.get('api_key_configured')}"
            )
        else:
            print(Colors.warn("Could not retrieve AI configuration info."))

        # 2. Generation Request
        print(Colors.info(f"Sending prompt to AI via proxy: '{prompt}'"))
        start = time.perf_counter()
        res = self.client.post("/api/ai/generate", {"prompt": prompt}, timeout=30)
        elapsed = round((time.perf_counter() - start) * 1000, 2)

        if res is None:
            print(Colors.err("AI generation request error: unable to reach reverse proxy."))
            return False
        if res.status_code != 200:
            print(Colors.err(f"AI generation failed: HTTP {res.status_code} - {res.text}"))
            return False

        data = self.client.safe_json(res)
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

    def test_security_headers(self) -> bool:
        """Verifies OWASP security headers and server version masking on HTTPS."""
        print(Colors.header("Test 5: Nginx Security Headers & Version Masking"))
        res = self.client.get("/", timeout=5)
        if res is None:
            print(Colors.err("Security header check failed: unable to reach reverse proxy."))
            return False

        headers = res.headers
        server_header = headers.get("Server", "")
        if "/" in server_header:
            print(Colors.err(f"Server header exposes version: '{server_header}'"))
            return False
        print(Colors.ok(f"Server header masked properly: '{server_header}'"))

        expected_headers = [
            ("X-Frame-Options", "SAMEORIGIN"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-XSS-Protection", "1; mode=block"),
        ]
        for h_name, expected_val in expected_headers:
            actual = headers.get(h_name)
            if not actual or expected_val not in actual:
                print(Colors.err(f"Missing or invalid security header: {h_name}"))
                return False
            print(Colors.ok(f"Security header verified: {h_name}: {actual}"))

        return True

    def test_access_control(self) -> bool:
        """Verifies Perimeter Geo-blocking and IP Blacklisting return 403 Forbidden."""
        print(Colors.header("Test 6: Perimeter Access Control (GeoIP & IP Blocking)"))

        # 1. Geo-blocking with simulated sanctioned country
        print(Colors.info("1. Testing Geo-blocking with X-Country-Code: BLOCKED"))
        res_geo = self.client.get(
            "/api/chat/health", headers={"X-Country-Code": "BLOCKED"}, timeout=5
        )
        if res_geo is None:
            print(Colors.err("Geo-blocking request error: unable to reach reverse proxy."))
            return False
        if res_geo.status_code != 403:
            print(Colors.err(f"Expected 403 Forbidden, got {res_geo.status_code}"))
            return False
        print(Colors.ok("Geo-blocked request rejected with HTTP 403 Forbidden by Nginx."))

        # 2. IP Blocking simulation
        print(Colors.info("2. Testing IP Blacklist policy with X-Simulate-Blocked-IP: 1"))
        res_ip = self.client.get(
            "/api/ai/health", headers={"X-Simulate-Blocked-IP": "1"}, timeout=5
        )
        if res_ip is None:
            print(Colors.err("IP-blocking request error: unable to reach reverse proxy."))
            return False
        if res_ip.status_code != 403:
            print(Colors.err(f"Expected 403 Forbidden, got {res_ip.status_code}"))
            return False
        print(Colors.ok("IP-restricted request rejected with HTTP 403 Forbidden by Nginx."))

        # 3. Legitimate request with allowed country code
        print(Colors.info("3. Testing legitimate request with X-Country-Code: AR"))
        res_ok = self.client.get("/api/chat/health", headers={"X-Country-Code": "AR"}, timeout=5)
        if res_ok is None:
            print(Colors.err("Legitimate request error: unable to reach reverse proxy."))
            return False
        if res_ok.status_code != 200:
            print(Colors.err(f"Legitimate request failed with status {res_ok.status_code}"))
            return False
        print(Colors.ok("Legitimate request allowed through reverse proxy (HTTP 200)."))
        return True

    def test_rate_limiting(self) -> bool:
        """Verifies Nginx Rate Limiting returns HTTP 429 Too Many Requests under burst."""
        print(Colors.header("Test 7: Nginx Rate Limiting (limit_req & HTTP 429)"))
        target = f"{self.config.https_url}/api/ai/health"
        print(Colors.info(f"Firing concurrent burst of 25 requests to {target}..."))

        with ThreadPoolExecutor(max_workers=10) as pool:
            responses = list(
                pool.map(lambda _: self.client.get("/api/ai/health", timeout=3), range(25))
            )

        status_codes = [r.status_code for r in responses if r is not None]
        if not status_codes:
            print(Colors.err("Rate limiting request error: unable to reach reverse proxy."))
            return False

        count_200 = status_codes.count(200)
        count_429 = status_codes.count(429)
        print(
            f"Results: {Colors.GREEN}{count_200} allowed (200){Colors.RESET}, {Colors.YELLOW}{count_429} rate-limited (429){Colors.RESET}"
        )

        if count_429 == 0:
            print(Colors.err("Rate limiting did not trigger any 429 responses."))
            return False

        print(Colors.ok("Rate limiting successfully throttled traffic with HTTP 429."))
        return True

    def test_security(self) -> bool:
        """Runs the complete security test suite."""
        h_ok = self.test_security_headers()
        a_ok = self.test_access_control()
        r_ok = self.test_rate_limiting()
        return h_ok and a_ok and r_ok

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
            ("Security Headers & Masking", self.test_security_headers()),
            ("Perimeter Access Control", self.test_access_control()),
            ("Rate Limiting (429)", self.test_rate_limiting()),
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
