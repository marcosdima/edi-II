import argparse
import cmd
import os
import sys

from .config import Colors, get_proxy_config
from .manager import DockerManager
from .tester import ProxyTester
from .views import AIView, ChatView


class InteractiveTerminal(cmd.Cmd):
    """Interactive command-line terminal to manage containers and test the Reverse Proxy."""

    intro = f"""
{Colors.BOLD}{Colors.CYAN}======================================================{Colors.RESET}
{Colors.BOLD}{Colors.CYAN}       Nginx Reverse Proxy Management & Test CLI      {Colors.RESET}
{Colors.BOLD}{Colors.CYAN}======================================================{Colors.RESET}
Type {Colors.BOLD}'chat'{Colors.RESET} to enter the interactive Chat system (or 'chat test').
Type {Colors.BOLD}'ai'{Colors.RESET} to enter the interactive AI assistant view (or 'ai <prompt>').
Type {Colors.BOLD}'security'{Colors.RESET} to test rate limiting, GeoIP blocking & headers.
Type {Colors.BOLD}'audit'{Colors.RESET} to view live Nginx audit logs.
Type {Colors.BOLD}'status'{Colors.RESET} to inspect container health.
Type {Colors.BOLD}'test'{Colors.RESET} to run the complete end-to-end proxy test suite.
Type {Colors.BOLD}'help'{Colors.RESET} to list available commands. Type {Colors.BOLD}'exit'{Colors.RESET} or Ctrl+D to quit.
"""
    prompt = f"{Colors.BOLD}{Colors.CYAN}proxy-cli>{Colors.RESET} "

    def __init__(self) -> None:
        super().__init__()
        self.tester = ProxyTester()

    # --- Container Management Commands ---

    def do_status(self, arg: str) -> None:
        """Inspect running container status: status (or ps)"""
        DockerManager.status()

    def do_ps(self, arg: str) -> None:
        """Alias for status."""
        self.do_status(arg)

    def do_up(self, arg: str) -> None:
        """Start the container stack: up [--build]"""
        build = "--build" in arg.split()
        DockerManager.start(build=build)

    def do_down(self, arg: str) -> None:
        """Stop and remove the container stack: down"""
        DockerManager.stop()

    def do_restart(self, arg: str) -> None:
        """Restart containers: restart [service_name]"""
        service = arg.strip() or None
        DockerManager.restart(service)

    def do_logs(self, arg: str) -> None:
        """View container logs: logs [service_name] [-f] [--tail=N]"""
        parts = arg.split()
        follow = "-f" in parts
        tail = 50
        service = None

        for part in parts:
            if part.startswith("--tail="):
                try:
                    tail = int(part.split("=")[1])
                except ValueError:
                    pass
            elif part != "-f":
                service = part

        DockerManager.logs(service=service, tail=tail, follow=follow)

    # --- Verification & Testing Commands ---

    def do_test(self, arg: str) -> None:
        """Run all verification tests through the Reverse Proxy: test"""
        self.tester.run_all()

    def do_gateway(self, arg: str) -> None:
        """Test the Gateway root endpoint over HTTPS: gateway"""
        self.tester.test_gateway_root()

    def do_redirect(self, arg: str) -> None:
        """Test HTTP to HTTPS 301 redirection on port 80: redirect"""
        self.tester.test_http_redirect()

    def do_chat(self, arg: str) -> None:
        """Enter interactive Chat view or run automated test: chat [test | <username>]"""
        parts = arg.strip().split()
        if parts and parts[0].lower() == "test":
            self.tester.test_chat_service()
        else:
            username = parts[0] if parts else "marcos"
            ChatView(default_user=username).cmdloop()

    def do_ai(self, arg: str) -> None:
        """Enter interactive AI assistant or run prompt: ai [test | <prompt>]"""
        text = arg.strip()
        if not text:
            AIView().cmdloop()
        elif text.lower() == "test":
            self.tester.test_ai_service()
        else:
            self.tester.test_ai_service(prompt=text)

    def do_security(self, arg: str) -> None:
        """Run security verification (headers, GeoIP blocking, rate limiting): security"""
        self.tester.test_security()

    def do_audit(self, arg: str) -> None:
        """View live Nginx reverse proxy audit logs: audit [--tail=N]"""
        tail = 25
        parts = arg.strip().split()
        for p in parts:
            if p.startswith("--tail="):
                try:
                    tail = int(p.split("=")[1])
                except ValueError:
                    pass
            elif p.isdigit():
                tail = int(p)
        print(Colors.header(f"Nginx Audit Logs (last {tail} entries)"))
        DockerManager.logs(service="reverse-proxy", tail=tail, follow=False)

    # --- Utility Commands ---

    def do_clear(self, arg: str) -> None:
        """Clear the terminal screen: clear"""
        os.system("clear")

    def do_urls(self, arg: str) -> None:
        """Show configured target proxy URLs: urls"""
        cfg = get_proxy_config()
        print(f"Proxy HTTPS: {Colors.CYAN}{cfg.https_url}{Colors.RESET}")
        print(f"Proxy HTTP:  {Colors.CYAN}{cfg.http_url}{Colors.RESET}")

    def do_exit(self, arg: str) -> bool:
        """Exit the interactive terminal: exit"""
        print(Colors.info("Exiting CLI. Goodbye!"))
        return True

    def do_quit(self, arg: str) -> bool:
        """Exit the interactive terminal: quit"""
        return self.do_exit(arg)

    def do_EOF(self, arg: str) -> bool:
        """Handle Ctrl+D to exit cleanly."""
        print()
        return self.do_exit(arg)

    def emptyline(self) -> bool:
        """Do nothing on empty line entry."""
        return False


def build_parser() -> argparse.ArgumentParser:
    """Creates argument parser for non-interactive CLI usage."""
    parser = argparse.ArgumentParser(
        description="Nginx Reverse Proxy Management & Test CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Container commands
    subparsers.add_parser("status", help="Inspect container stack status (docker compose ps)")

    up_parser = subparsers.add_parser("up", help="Start containers in background")
    up_parser.add_argument("--build", action="store_true", help="Rebuild container images")

    subparsers.add_parser("down", help="Stop containers")

    restart_parser = subparsers.add_parser("restart", help="Restart containers")
    restart_parser.add_argument("service", nargs="?", default=None, help="Service name")

    logs_parser = subparsers.add_parser("logs", help="View container logs")
    logs_parser.add_argument("service", nargs="?", default=None, help="Service name")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    logs_parser.add_argument("--tail", type=int, default=50, help="Number of log lines")

    # Testing and security commands
    subparsers.add_parser("test", help="Run full end-to-end proxy verification suite")
    subparsers.add_parser("security", help="Run security verification (headers, GeoIP, rate limit)")
    audit_parser = subparsers.add_parser("audit", help="Inspect Nginx reverse proxy audit logs")
    audit_parser.add_argument("--tail", type=int, default=25, help="Number of audit log entries")
    subparsers.add_parser("gateway", help="Test gateway root endpoint")
    subparsers.add_parser("redirect", help="Test HTTP (80) -> HTTPS (443) 301 redirection")
    chat_parser = subparsers.add_parser(
        "chat", help="Launch interactive Chat view or run automated tests"
    )
    chat_parser.add_argument(
        "--test", action="store_true", help="Run automated chat test suite via proxy"
    )
    chat_parser.add_argument(
        "-u", "--user", default="marcos", help="Username for interactive chat (default: marcos)"
    )

    ai_parser = subparsers.add_parser("ai", help="Query AI service or launch interactive view")
    ai_parser.add_argument(
        "prompt",
        nargs="*",
        default=[],
        help="Prompt text for AI (if omitted, launches interactive AI view)",
    )
    ai_parser.add_argument("--test", action="store_true", help="Run automated AI service test")

    return parser


def main() -> int:
    """CLI entrypoint supporting both direct arguments and interactive shell."""
    parser = build_parser()

    # If no arguments passed, launch interactive terminal
    if len(sys.argv) == 1:
        InteractiveTerminal().cmdloop()
        return 0

    args = parser.parse_args()
    tester = ProxyTester()

    if args.command == "status":
        return DockerManager.status()
    elif args.command == "up":
        return DockerManager.start(build=args.build)
    elif args.command == "down":
        return DockerManager.stop()
    elif args.command == "restart":
        return DockerManager.restart(args.service)
    elif args.command == "logs":
        return DockerManager.logs(service=args.service, tail=args.tail, follow=args.follow)
    elif args.command == "audit":
        return DockerManager.logs(service="reverse-proxy", tail=args.tail, follow=False)
    elif args.command == "test":
        return 0 if tester.run_all() else 1
    elif args.command == "security":
        return 0 if tester.test_security() else 1
    elif args.command == "gateway":
        return 0 if tester.test_gateway_root() else 1
    elif args.command == "redirect":
        return 0 if tester.test_http_redirect() else 1
    elif args.command == "chat":
        if args.test:
            return 0 if tester.test_chat_service() else 1
        ChatView(default_user=args.user).cmdloop()
        return 0
    elif args.command == "ai":
        if args.test:
            return 0 if tester.test_ai_service() else 1
        if not args.prompt:
            AIView().cmdloop()
            return 0
        prompt_text = " ".join(args.prompt)
        return 0 if tester.test_ai_service(prompt=prompt_text) else 1
    else:
        parser.print_help()
        return 1
