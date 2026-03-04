"""
Rich UI utilities for Astra.

Provides consistent, beautiful terminal output for agent traces,
tool calls, and dashboards.
"""

from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table


def get_console() -> Console:
    """Return shared Rich Console instance."""
    return Console()


def welcome_dashboard(version: str = "0.1.0") -> None:
    """
    Display the Astra welcome dashboard.

    Args:
        version: Astra package version to display.
    """
    console = get_console()

    title = "[bold cyan]Astra[/bold cyan] — [dim]Agentic Skill & TRAce[/dim]"
    subtitle = "Data factory for high-quality multi-turn tool-use trajectories"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column(style="white")
    table.add_row("Version", version)
    table.add_row("Purpose", "Fine-tune small LMs for agentic capabilities")
    table.add_row("Pipeline", "Skills → Blueprints → Execution → Optimization")

    content = Group(subtitle, "", table)
    panel = Panel(
        content,
        title=title,
        border_style="cyan",
        padding=(1, 2),
        expand=False,
    )
    console.print(panel)
    console.print()


def print_trace(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: Any,
    *,
    turn: int | None = None,
) -> None:
    """
    Pretty-print a single tool call and response (agent trace step).

    Args:
        tool_name: Name of the tool that was called.
        tool_input: Input parameters passed to the tool.
        tool_output: Response from the tool.
        turn: Optional turn number in the conversation.
    """
    console = get_console()

    turn_str = f" [dim]Turn {turn}[/dim]" if turn is not None else ""
    header = f"[bold blue]Tool Call{turn_str}[/bold blue]: [cyan]{tool_name}[/cyan]"

    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Field", style="dim", width=12)
    table.add_column("Value", style="white")

    # Format input
    input_str = _format_value(tool_input)
    table.add_row("Input", input_str)

    # Format output
    output_str = _format_value(tool_output)
    table.add_row("Output", output_str)

    panel = Panel(
        table,
        title=header,
        border_style="blue",
        padding=(0, 1),
        expand=False,
    )
    console.print(panel)


def _format_value(value: Any, max_len: int = 200) -> str:
    """Format a value for display, truncating if needed."""
    import json

    try:
        s = json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = str(value)

    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s
