"""Minimalist, monochrome terminal theme inspired by Ollama and modern CLI tools."""

from rich.markup import escape
from textual.theme import Theme

# Centralized monochrome color tokens
COLOR_PRIMARY = "#ffffff"
COLOR_FOREGROUND = "#e5e5e5"
COLOR_TEXT = "#d4d4d4"
COLOR_SECONDARY = "#a3a3a3"
COLOR_MUTED = "#737373"
COLOR_DIM = "#525252"
COLOR_SUBTLE = "#444444"
COLOR_RULE = "#333333"

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

/* Main dashboard centered hero + vertical left buttons + wider right log block */
.main-hero {
    width: 100%;
    height: auto;
    background: #000000;
    padding: 0 4;
    content-align: center middle;
    text-align: center;
}

#main_workspace {
    height: 1fr;
    background: #000000;
    padding: 1 4 0 4;
}

#main_menu_list {
    width: 2fr;
    height: 100%;
    overflow-y: auto;
    background: #000000;
    padding-right: 2;
    scrollbar-color: #333333 #000000;
    scrollbar-size: 1 1;
}

#main_menu_list > .menu-card {
    height: auto;
    min-height: 3;
    max-height: 4;
    width: 100%;
    margin: 0 0 1 0;
    padding: 0 2;
    content-align: left middle;
}

#main_output_container {
    width: 3fr;
    height: 100%;
    background: #000000;
    border-left: solid #1f1f1f;
    padding-left: 2;
}

#main_log {
    height: 100%;
    background: #000000;
    padding: 0 1;
}

/* Slash command selector popup above bottom input panel */
#command_palette {
    height: auto;
    max-height: 9;
    margin: 0 4;
    background: #080808;
    border: solid #262626;
    color: #e5e5e5;
    display: none;
    scrollbar-color: #333333 #080808;
    scrollbar-size: 1 1;
}

#command_palette > .option-list--option-highlighted {
    background: #1a1a1a;
    color: #ffffff;
    text-style: bold;
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

/* Bottom dock containing optional slash command palette + 5-row input panel */
.tui-bottom-dock {
    dock: bottom;
    height: auto;
    background: #000000;
}

.tui-bottom-panel {
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

/* Modal dialog for creating a new conversation */
NewConversationModal {
    align: center middle;
    background: rgba(0, 0, 0, 0.78);
}

#new_conv_dialog {
    width: 58;
    height: auto;
    background: #080808;
    border: solid #333333;
    padding: 1 2;
}

.modal-title {
    text-style: bold;
    color: #ffffff;
    margin-bottom: 1;
}

.modal-label {
    color: #a3a3a3;
    margin-top: 1;
}

.modal-hint {
    color: #666666;
    margin-top: 1;
    margin-bottom: 1;
}

.modal-error {
    color: #ffffff;
    text-style: bold;
    height: auto;
    margin-bottom: 1;
}

.modal-buttons {
    height: auto;
    align: right middle;
    margin-top: 1;
}

.modal-buttons > Button {
    margin-left: 1;
    background: #141414;
    color: #e5e5e5;
    border: solid #333333;
}

.modal-buttons > Button:hover {
    background: #1f1f1f;
    border: solid #737373;
}

.modal-buttons > Button.-primary {
    background: #ffffff;
    color: #000000;
    border: solid #ffffff;
    text-style: bold;
}

#user_chips_grid {
    layout: grid;
    grid-size: 3;
    grid-gutter: 1;
    height: auto;
    max-height: 9;
    overflow-y: auto;
    margin-top: 1;
    margin-bottom: 1;
    scrollbar-color: #333333 #080808;
    scrollbar-size: 1 1;
}

.user-chip {
    width: 100%;
    height: 3;
    background: #121212;
    color: #a3a3a3;
    border: solid #333333;
    content-align: center middle;
    text-align: center;
}

.user-chip:hover {
    border: solid #737373;
    color: #ffffff;
}

.user-chip.selected {
    background: #ffffff;
    color: #000000;
    border: solid #ffffff;
    text-style: bold;
}

.user-chip.locked {
    background: #e5e5e5;
    color: #000000;
    border: solid #ffffff;
    text-style: bold;
}
"""


def _sender_and_content_tags(sender: str, content: str, current_user: str) -> tuple[str, str]:
    """Return Rich-formatted (sender_tag, content_tag) using monochrome hierarchy."""
    safe_sender = escape(sender)
    safe_content = escape(content)
    if sender == current_user:
        return f"[bold {COLOR_PRIMARY}]{safe_sender}[/]", f"[{COLOR_PRIMARY}]{safe_content}[/]"
    return f"[bold {COLOR_SECONDARY}]{safe_sender}[/]", f"[{COLOR_TEXT}]{safe_content}[/]"


def format_chat_message(sender: str, content: str, created_at: str, current_user: str) -> str:
    """Renders a chat message with sober, high-contrast monospace formatting."""
    time_str = created_at[11:19] if len(created_at) >= 19 else created_at
    user_tag, msg_text = _sender_and_content_tags(sender, content, current_user)
    return f"[dim {COLOR_MUTED}]{time_str}[/]  {user_tag}  {msg_text}"


def format_message_preview(sender: str, content: str, created_at: str, current_user: str) -> str:
    """Renders a compact one-line message preview for inbox cards."""
    raw_content = content.replace("\n", " ").strip()
    preview = raw_content[:26] + ("..." if len(raw_content) > 26 else "")
    time_str = created_at[11:16] if len(created_at) >= 16 else ""
    time_tag = f"[dim #666666]{time_str}[/] " if time_str else ""
    sender_tag, content_tag = _sender_and_content_tags(sender[:10], preview, current_user)
    return f"{time_tag}{sender_tag}: {content_tag}"


def format_system_event(text: str) -> str:
    """Renders system directives or info messages in a muted style."""
    return f"[italic {COLOR_MUTED}]✦ {text}[/]"


def format_section_header(title: str) -> str:
    """Renders a monochrome section divider header."""
    return f"\n[bold {COLOR_PRIMARY}]─── {escape(title)} ───[/]"


def format_status_ok(text: str) -> str:
    """Renders a success indicator line."""
    return f"[bold {COLOR_PRIMARY}]✓ {escape(text)}[/]"


def format_status_err(text: str) -> str:
    """Renders an error indicator line."""
    return f"[bold {COLOR_PRIMARY}]✗ {escape(text)}[/]"


def format_command_help(header: str, commands: list[tuple[str, str]]) -> list[str]:
    """Formats a consistent command help block for RichLog."""
    lines = [f"\n[bold {COLOR_PRIMARY}]{escape(header)}[/]"]
    for cmd_name, desc in commands:
        lines.append(f"  [bold {COLOR_FOREGROUND}]{escape(cmd_name):<20}[/] {escape(desc)}")
    lines.append("")
    return lines


def format_card(title: str, shortcut: str, description: str) -> str:
    """Formats a menu card in the sober terminal dashboard."""
    return (
        f"[bold {COLOR_PRIMARY}]{shortcut}[/] "
        f"[bold {COLOR_FOREGROUND}]{title:<18}[/] "
        f"[dim {COLOR_MUTED}]{description}[/]"
    )


def format_dot_matrix(current_page: int, total_pages: int) -> str:
    """Renders a dot matrix pagination carousel indicator."""
    if total_pages <= 1:
        return f"[bold {COLOR_PRIMARY}]●[/]"
    dots = [
        f"[bold {COLOR_PRIMARY}]●[/]" if i == current_page else f"[dim {COLOR_SUBTLE}]○[/]"
        for i in range(total_pages)
    ]
    dots_str = "   ".join(dots)
    return (
        f"[dim {COLOR_DIM}]PAGE {current_page + 1}/{total_pages}   •   [/]"
        f"{dots_str}"
        f"[dim {COLOR_DIM}]   •   [← / PgUp] Prev  •  [→ / PgDn] Next[/]"
    )
