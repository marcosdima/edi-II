from typing import Any

from ..config import Colors
from .base import BaseView


class ConversationView(BaseView):
    """View representing an active chat conversation."""

    def __init__(self, conv_id: int, title: str, current_user: str) -> None:
        super().__init__()
        self.conv_id = conv_id
        self.title = title
        self.current_user = current_user
        self.prompt = f'{Colors.BOLD}{Colors.MAGENTA}chat:{self.current_user} [#{self.conv_id} "{self.title}"]>{Colors.RESET} '
        self.last_seen_message_id = 0

    def print_messages(self, messages: list[dict[str, Any]]) -> None:
        """Formats and displays chat messages."""
        if not messages:
            print(Colors.info("No messages in this conversation yet."))
            return

        for m in messages:
            sender = m.get("sender", "unknown")
            content = m.get("content", "")
            created = m.get("created_at", "")[:19].replace("T", " ")
            msg_id = m.get("id", 0)
            self.last_seen_message_id = max(self.last_seen_message_id, msg_id)

            if sender == self.current_user:
                sender_label = f"{Colors.BOLD}{Colors.GREEN}{sender}{Colors.RESET}"
            else:
                sender_label = f"{Colors.BOLD}{Colors.CYAN}{sender}{Colors.RESET}"

            print(f"[{Colors.DIM}{created}{Colors.RESET}] {sender_label}: {content}")

    def fetch_messages(self) -> list[dict[str, Any]]:
        """Fetches messages from the server."""
        res = self.api_get(f"/api/chat/conversations/{self.conv_id}/messages")
        if res and res.status_code == 200:
            return res.json().get("messages", [])
        return []

    def preloop(self) -> None:
        """Runs once before the user prompt loop begins."""
        print(
            f'\n{Colors.BOLD}{Colors.MAGENTA}=== Conversation #{self.conv_id}: "{self.title}" ==={Colors.RESET}'
        )
        print(
            Colors.info(
                "Type any text to send a message. Type /help for directives. Type 'back' to exit.\n"
            )
        )
        messages = self.fetch_messages()
        self.print_messages(messages)
        print()

    def default(self, line: str) -> None:
        """Any text entered is sent as a message (or directive)."""
        text = line.strip()
        if not text:
            return

        res = self.api_post(
            f"/api/chat/conversations/{self.conv_id}/messages",
            {"sender": self.current_user, "content": text},
        )
        if not res:
            return

        if res.status_code == 201:
            data = res.json()
            created = data.get("created_at", "")[:19].replace("T", " ")
            sender_label = f"{Colors.BOLD}{Colors.GREEN}{self.current_user}{Colors.RESET}"
            print(f"[{Colors.DIM}{created}{Colors.RESET}] {sender_label}: {text}")
        elif res.status_code == 200:
            # System directive executed
            data = res.json()
            if data.get("type") == "system_directive":
                directive = data.get("directive", "")
                if directive == "/title":
                    print(Colors.ok(data.get("message", "Title updated.")))
                    self.title = text.split(maxsplit=1)[1] if " " in text else self.title
                    self.prompt = f'{Colors.BOLD}{Colors.MAGENTA}chat:{self.current_user} [#{self.conv_id} "{self.title}"]>{Colors.RESET} '
                elif directive == "/members":
                    members = [m["username"] for m in data.get("members", [])]
                    print(Colors.ok(f"Participants: {members}"))
                elif directive == "/clear":
                    print(Colors.ok(data.get("message", "History cleared.")))
                elif directive == "/leave":
                    print(Colors.warn(data.get("message", "Left conversation.")))
                    return
                elif directive == "/help":
                    print(Colors.header("Available System Directives"))
                    for d in data.get("available_directives", []):
                        print(f"  {d['command']:<20} {d['description']}")
            else:
                print(Colors.info(f"Response: {res.text}"))
        elif res.status_code == 403:
            print(Colors.err("You are not an active participant in this conversation."))
        else:
            print(Colors.err(f"Server responded with error {res.status_code}: {res.text}"))

    def do_poll(self, arg: str) -> None:
        """Fetch and display new messages: poll (or refresh)"""
        messages = self.fetch_messages()
        new_msgs = [m for m in messages if m.get("id", 0) > self.last_seen_message_id]
        if new_msgs:
            self.print_messages(new_msgs)
        else:
            print(Colors.info("No new messages."))

    def do_refresh(self, arg: str) -> None:
        """Alias for poll."""
        self.do_poll(arg)


class ChatView(BaseView):
    """View managing user conversations, contacts, and messaging."""

    def __init__(self, default_user: str = "marcos") -> None:
        super().__init__()
        self.current_user = default_user.strip().lower()
        self.display_name = default_user
        self.update_prompt()

    def update_prompt(self) -> None:
        self.prompt = (
            f"{Colors.BOLD}{Colors.CYAN}proxy-cli [chat:{self.current_user}]>{Colors.RESET} "
        )

    def preloop(self) -> None:
        # Automatically ensure the user exists on entry
        self._ensure_user(self.current_user)
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== Chat View ==={Colors.RESET}")
        print(f"Logged in as: {Colors.BOLD}{self.current_user}{Colors.RESET}")
        print(
            Colors.info(
                "Commands: 'inbox', 'open <id>', 'new <title> <user1,user2>', 'users', 'login <user>', 'back'"
            )
        )
        self.do_inbox("")

    def _ensure_user(self, username: str) -> None:
        """Registers user on server if not present."""
        res = self.api_post(
            "/api/chat/auth/register",
            {"username": username, "display_name": username.capitalize()},
        )
        if res and res.status_code in (200, 201):
            user_data = res.json().get("user", {})
            self.display_name = user_data.get("display_name", username)

    def do_whoami(self, arg: str) -> None:
        """Show current active user identity: whoami"""
        print(f"Active user: {Colors.BOLD}{self.current_user}{Colors.RESET} ({self.display_name})")

    def do_login(self, arg: str) -> None:
        """Switch active user identity: login <username>"""
        username = arg.strip().lower()
        if not username:
            print(Colors.err("Usage: login <username>"))
            return

        self.current_user = username
        self._ensure_user(username)
        self.update_prompt()
        print(Colors.ok(f"Switched identity to '{self.current_user}'."))
        self.do_inbox("")

    def do_users(self, arg: str) -> None:
        """List registered users in the system: users"""
        res = self.api_get("/api/chat/users")
        if not res or res.status_code != 200:
            print(Colors.err("Failed to retrieve users."))
            return

        data = res.json()
        users = data.get("users", [])
        print(Colors.header(f"Registered Users ({len(users)})"))
        for u in users:
            uname = u.get("username", "")
            dname = u.get("display_name", "")
            active_badge = (
                f"{Colors.GREEN}(you){Colors.RESET}" if uname == self.current_user else ""
            )
            print(f"  • {Colors.BOLD}{uname:<15}{Colors.RESET} {dname:<25} {active_badge}")

    def do_inbox(self, arg: str) -> None:
        """List your active conversations: inbox (or list)"""
        res = self.api_get(f"/api/chat/users/{self.current_user}/conversations")
        if not res or res.status_code != 200:
            print(Colors.err("Failed to retrieve inbox."))
            return

        data = res.json()
        convs = data.get("conversations", [])
        print(Colors.header(f"Your Conversations ({len(convs)})"))
        if not convs:
            print(
                Colors.info(
                    "You have no conversations yet. Type 'new <title> <user1,user2>' to create one."
                )
            )
            return

        for c in convs:
            cid = c.get("id")
            title = c.get("title", "Untitled")
            created = c.get("created_at", "")[:10]
            print(
                f"  [{Colors.BOLD}#{cid}{Colors.RESET}] {title:<30} {Colors.DIM}(created: {created}){Colors.RESET}"
            )
        print(Colors.info("Type 'open <id>' to enter a conversation."))

    def do_list(self, arg: str) -> None:
        """Alias for inbox."""
        self.do_inbox(arg)

    def do_new(self, arg: str) -> None:
        """Create a new conversation: new <title> <user1,user2>"""
        parts = arg.strip().split(maxsplit=1)
        if len(parts) < 2:
            print(Colors.err("Usage: new <title> <user1,user2,...>"))
            print('Example: new "Proyecto Final" profe,lucas')
            return

        raw_title = parts[0].strip("\"'")
        raw_users = parts[1].strip()
        participants = [
            u.strip().lower() for u in raw_users.replace(" ", "").split(",") if u.strip()
        ]

        if self.current_user not in participants:
            participants.append(self.current_user)

        res = self.api_post(
            "/api/chat/conversations",
            {"title": raw_title, "participants": participants},
        )
        if not res or res.status_code != 201:
            print(
                Colors.err(f"Failed to create conversation: {res.text if res else 'no response'}")
            )
            return

        data = res.json()
        conv_id = data.get("conversation_id")
        print(
            Colors.ok(
                f"Created conversation #{conv_id} '{raw_title}' with {data.get('participants')}."
            )
        )
        self.do_open(str(conv_id))

    def do_open(self, arg: str) -> None:
        """Open an active conversation: open <conversation_id>"""
        cid_str = arg.strip()
        if not cid_str.isdigit():
            print(Colors.err("Usage: open <conversation_id> (numeric ID)"))
            return

        conv_id = int(cid_str)
        # Fetch conversation details to verify existence
        res = self.api_get(f"/api/chat/conversations/{conv_id}/messages")
        if not res:
            return
        if res.status_code == 404:
            print(Colors.err(f"Conversation #{conv_id} not found."))
            return

        title = res.json().get("title", f"Conversation #{conv_id}")
        conv_view = ConversationView(conv_id=conv_id, title=title, current_user=self.current_user)
        conv_view.cmdloop()
        # Refresh inbox after leaving conversation
        self.do_inbox("")
