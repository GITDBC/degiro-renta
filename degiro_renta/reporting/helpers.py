# Standard libraries
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

# 3pps
from rich import box
from rich.console import Console
from rich.padding import Padding
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# Own modules
from degiro_renta.domain.money import to_cents

# Spaces the bullets are indented by.
BULLET_INDENT: Final[int] = 2


@dataclass(frozen=True)
class Notice:
    """
    Note about the statement, shown under the title of the report.

    Attributes:
        message: Text of the note.
        category: Heading the note is listed under.
        severe: Whether it is more than a point to review, such as a
            trade the parser could not read, logged as an error, or a
            block over the limit of the modelo 720. It is printed in red
            instead of yellow.
    """

    message: str
    category: str
    severe: bool = False


def format_decimal(value: Decimal) -> str:
    """
    Format a Decimal to two decimals, no thousands separator.

    Every euro figure the reports print goes through here, so the
    rounding of the cent is decided once instead of once per report.

    Args:
        value: Value to format.

    Returns:
        The value as text with two decimals, rounded half up.
    """

    return str(to_cents(value))


def format_date(value: date) -> str:
    """
    Format a date the way the Degiro statement writes it.

    Args:
        value: Date to format.

    Returns:
        The date as ``dd-mm-yyyy``.
    """

    return value.strftime("%d-%m-%Y")


def signed_amount(value: Decimal, *, bold: bool = False, suffix: str = "") -> Text:
    """
    Build a Rich Text colored by the sign of the value.

    Zero counts as positive: a null result is not a loss, so it stays
    green in every report.

    Args:
        value: Signed value to render.
        bold: Whether to add bold to the color.
        suffix: Text appended after the number, such as a percent sign.

    Returns:
        Rich Text in green when the value is zero or positive and red
        when it is negative.
    """

    color = "green" if value >= 0 else "red"

    return Text(
        f"{format_decimal(value)}{suffix}", style=f"bold {color}" if bold else color
    )


def bold_text(text: str, style: str = "bold") -> Text:
    """
    Build a bold Rich Text, for the totals rows of the tables.

    Args:
        text: Text to render.
        style: Rich style to apply.

    Returns:
        The styled Rich Text.
    """

    return Text(text, style=style)


def new_table() -> Table:
    """
    Create the table every section of the report is built on.

    Returns:
        An empty Rich Table with the report style.
    """

    return Table(box=box.ROUNDED, header_style="bold", expand=False)


def print_section(console: Console, title: str, caption: str | None = None) -> None:
    """
    Open a report section with its heading and optional caption.

    A blank line comes before the heading and another after it, so the
    gap between the heading and the table below it is the one the table
    leaves before the next heading.

    Args:
        console: Rich Console instance for output.
        title: Section heading.
        caption: Explanatory text printed under the heading, dimmed.

    Returns:
        None.
    """

    console.print()
    console.print(Rule(f"[bold]{title}[/bold]"))

    if caption is not None:
        console.print(f"[dim]{caption}[/dim]")

    console.print()


def bullet_grid(items: Sequence[tuple[str, str | None]]) -> Padding:
    """
    Lay notes out as bullets, wrapped with a hanging indent.

    Args:
        items: Pairs of text, which may carry Rich markup, and the Rich
            style applied to the bullet and the text.

    Returns:
        A borderless table, indented, with a blank line between the
        bullets.
    """

    grid = Table.grid(padding=(0, 1))
    grid.add_column(no_wrap=True)
    grid.add_column()

    for index, (text, style) in enumerate(items):
        if index:
            grid.add_row("", "")

        grid.add_row(
            Text("•", style=style or ""),
            f"[{style}]{text}[/{style}]" if style else text,
        )

    return Padding(grid, (0, 0, 0, BULLET_INDENT))


def print_bullet(console: Console, text: str, *, style: str | None = None) -> None:
    """
    Print a single note as a bullet.

    Args:
        console: Rich Console instance for output.
        text: Note to print, which may carry Rich markup.
        style: Rich style applied to the bullet and the text.

    Returns:
        None.
    """

    console.print(bullet_grid([(text, style)]))
