"""Minimalist, monochrome terminal theme inspired by Ollama and modern CLI tools."""

from rich.markup import escape
from textual.theme import Theme

# Custom sober theme eliminating all default purple/violet accents
OLLAMA_THEME = Theme(
    name="ollama-dark",
    primary="#ffffff",
    secondary="#737373",
    accent="#ffffff",
    foreground="#e5e5e5",
    background="#000000",
    surface="#0a0a0a",
    panel="#000000",
    boost="#141414",
    dark=True,
)

TUI_CSS = """
Screen {
    background: #000000;
    color: #ffffff;
    layout: vertical;
}

/* Header bar */
.tui-header {
    dock: top;
    height: 3;
    background: #000000;
    border-bottom: solid #1f1f1f;
    padding: 0 4;
}

.tui-header-title {
    width: 1fr;
    height: 100%;
    content-align: left middle;
    text-style: bold;
    color: #ffffff;
}

.tui-header-meta {
    width: auto;
    height: 100%;
    content-align: right middle;
    color: #666666;
}

/* Content log container */
.tui-content {
    height: 1fr;
    background: #000000;
    padding: 1 4;
}

.tui-log {
    background: #000000;
    color: #d4d4d4;
    scrollbar-color: #333333 #000000;
    scrollbar-size: 1 1;
}

/* 3-column spacious cards grid for carousel */
#conversations_grid {
    layout: grid;
    grid-size: 3 1;
    grid-gutter: 2;
    height: 1fr;
    padding: 1 4 0 4;
    background: #000000;
}

.conv-card {
    height: 100%;
    width: 100%;
    background: #080808;
    border: solid #262626;
    padding: 1 2;
    overflow-y: hidden;
}

.conv-card:hover {
    border: solid #555555;
    background: #0f0f0f;
}

.conv-card:focus {
    border: solid #ffffff;
    background: #141414;
}

.card-new {
    border: dashed #333333;
    content-align: center middle;
    text-align: center;
}

.card-new:hover {
    border: dashed #737373;
    background: #0f0f0f;
}

/* Dot matrix pagination bar */
#pagination_dots {
    width: 100%;
    height: 1;
    text-align: center;
    background: #000000;
    color: #ffffff;
    margin: 0;
}

/* Compact feedback log container below carousel */
#inbox_log_container {
    height: 3;
    background: #000000;
    padding: 0 4;
}

#inbox_log {
    height: 100%;
    background: #000000;
    color: #888888;
}

/* Bottom centered input panel (strictly 5 rows high, never clips) */
.tui-bottom-panel {
    dock: bottom;
    height: 5;
    background: #000000;
    border-top: solid #1f1f1f;
    align: center middle;
    padding: 0;
}

.tui-input-wrapper {
    width: 80%;
    height: auto;
    align: center middle;
}

.tui-input {
    width: 100%;
    height: 3;
    background: #0c0c0c;
    border: solid #262626;
    color: #ffffff;
    padding: 0 2;
}

.tui-input:focus {
    border: solid #525252;
    background: #121212;
}

.tui-input > .input--placeholder {
    color: #525252;
    text-style: italic;
}

.tui-status-bar {
    width: 100%;
    height: 1;
    text-align: center;
    color: #525252;
    margin-top: 0;
}
"""


def format_chat_message(sender: str, content: str, created_at: str, current_user: str) -> str:
    """Renders a chat message with sober, high-contrast monospace formatting."""
    time_str = created_at[11:19] if len(created_at) >= 19 else created_at
    safe_content = escape(content)
    safe_sender = escape(sender)
    if sender == current_user:
        user_tag = f"[bold #ffffff]{safe_sender}[/]"
        msg_text = f"[#ffffff]{safe_content}[/]"
    else:
        user_tag = f"[bold #a3a3a3]{safe_sender}[/]"
        msg_text = f"[#d4d4d4]{safe_content}[/]"
    return f"[dim #737373]{time_str}[/]  {user_tag}  {msg_text}"


def format_system_event(text: str) -> str:
    """Renders system directives or info messages in a muted style."""
    return f"[italic #737373]✦ {text}[/]"


def format_card(title: str, shortcut: str, description: str) -> str:
    """Formats a menu card in the sober terminal dashboard."""
    return f"[bold #ffffff]{shortcut}[/] [bold #e5e5e5]{title:<18}[/] [dim #737373]{description}[/]"


def format_dot_matrix(current_page: int, total_pages: int) -> str:
    """Renders a dot matrix pagination carousel indicator."""
    if total_pages <= 1:
        return "[bold #ffffff]●[/]"
    dots = [
        "[bold #ffffff]●[/]" if i == current_page else "[dim #444444]○[/]"
        for i in range(total_pages)
    ]
    dots_str = "   ".join(dots)
    return (
        f"[dim #525252]PAGE {current_page + 1}/{total_pages}   •   [/]"
        f"{dots_str}"
        f"[dim #525252]   •   [← / PgUp] Prev  •  [→ / PgDn] Next[/]"
    )
