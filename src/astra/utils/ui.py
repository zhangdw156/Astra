"""
Astra 的 Rich 终端 UI 工具。

提供统一的终端输出：Agent 轨迹、工具调用、欢迎面板等。
"""

from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table


def get_console() -> Console:
    """返回共用的 Rich Console 实例。"""
    return Console()


def welcome_dashboard(version: str = "0.1.0") -> None:
    """
    显示 Astra 欢迎面板。

    Args:
        version: 要显示的 Astra 版本号。
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
    美化打印单次工具调用与响应（Agent 轨迹一步）。

    Args:
        tool_name: 被调用的工具名。
        tool_input: 传入工具的参数字典。
        tool_output: 工具返回结果。
        turn: 可选，对话轮次编号。
    """
    console = get_console()

    turn_str = f" [dim]Turn {turn}[/dim]" if turn is not None else ""
    header = f"[bold blue]Tool Call{turn_str}[/bold blue]: [cyan]{tool_name}[/cyan]"

    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Field", style="dim", width=12)
    table.add_column("Value", style="white")

    # 输入
    input_str = _format_value(tool_input)
    table.add_row("Input", input_str)

    # 输出
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
    """将值格式化为可读字符串，过长时截断。"""
    import json

    try:
        s = json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = str(value)

    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s
