"""Terminal color theme inspired by the user's waybar config (Dracula-like)."""

from rich.theme import Theme


WAYBAR_THEME = Theme(
    {
        "agent.bg": "on #0f1116",
        "agent.text": "#c5cdd9",
        "agent.accent": "#ff79c6",
        "agent.accent2": "#bd93f9",
        "agent.success": "#50fa7b",
        "agent.info": "#8be9fd",
        "agent.warn": "#ffb86c",
        "agent.danger": "#ff5555",
        "agent.muted": "#6272a4",
        "agent.highlight": "#f1fa8c",
    }
)

COLORS = {
    "bg": "#0f1116",
    "text": "#c5cdd9",
    "accent": "#ff79c6",
    "accent2": "#bd93f9",
    "success": "#50fa7b",
    "info": "#8be9fd",
    "warn": "#ffb86c",
    "danger": "#ff5555",
    "muted": "#6272a4",
    "highlight": "#f1fa8c",
}
