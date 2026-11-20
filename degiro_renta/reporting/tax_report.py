# Standard libraries
from collections.abc import Callable, Sequence
from typing import Final

# 3pps
from rich.console import Console
from rich.rule import Rule

# Own modules
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.currency import (
    render_currency_gains,
    render_unvalued_operations,
)
from degiro_renta.reporting.foreign_assets import foreign_assets_notices
from degiro_renta.reporting.helpers import Notice, bullet_grid
from degiro_renta.reporting.income import (
    other_income_notices,
    render_dividends,
    render_interest_income,
    render_other_income,
)
from degiro_renta.reporting.sales import (
    render_debt_sales,
    render_sales,
)
from degiro_renta.reporting.savings import (
    render_foreign_credit,
    render_loss_carryforward,
)
from degiro_renta.reporting.summary import render_summary
from degiro_renta.reporting.wash_sale import render_wash_sales, wash_sale_notices

Renderer = Callable[[Console, ReportData], None]
NoticeBuilder = Callable[[ReportData], list[Notice]]

# Notes the report raises itself, in the order they are listed.
NOTICE_BUILDERS: Final[tuple[NoticeBuilder, ...]] = (
    wash_sale_notices,
    other_income_notices,
    foreign_assets_notices,
)

# Sections in the order the report prints them. Sales, dividends and the
# summary always print; every other one is skipped when the exercise has
# nothing for it.
SECTIONS: Final[tuple[Renderer, ...]] = (
    render_sales,
    render_debt_sales,
    render_wash_sales,
    render_currency_gains,
    render_dividends,
    render_interest_income,
    render_unvalued_operations,
    render_other_income,
    render_foreign_credit,
    render_loss_carryforward,
    render_summary,
)


def print_notices(console: Console, notices: Sequence[Notice]) -> None:
    """
    Print the notes under the title, grouped by category.

    Categories keep the order in which they first appear.

    Args:
        console: Rich console to print to.
        notices: Notes to print.

    Returns:
        None.
    """

    categories: dict[str, list[Notice]] = {}

    for notice in notices:
        categories.setdefault(notice.category, []).append(notice)

    for category, items in categories.items():
        console.print()
        console.print(f"[bold]{category}[/bold]")
        console.print()
        console.print(
            bullet_grid(
                [(item.message, "red" if item.severe else "yellow") for item in items]
            )
        )


def print_report(
    data: ReportData,
    console: Console | None = None,
    notices: Sequence[Notice] = (),
) -> None:
    """
    Print the fiscal report of one exercise.

    It only lays out the aggregates that ``build_report_data`` already
    computed.

    Args:
        data: Precomputed report aggregates.
        console: Rich console to print to. A default one when omitted.
        notices: Warnings about the statement. They are printed with
            the notes the report raises itself, as bullets grouped by
            category, between the title and the first section.

    Returns:
        None.
    """

    console = console or Console()
    exercise = f" — EJERCICIO {data.year}" if data.year is not None else ""

    console.print(
        Rule(f"[bold]INFORME FISCAL — BASE DEL AHORRO (IRPF España){exercise}[/bold]")
    )

    report_notices = [item for build in NOTICE_BUILDERS for item in build(data)]
    print_notices(console, [*notices, *report_notices])

    for render in SECTIONS:
        render(console, data)

    console.print()
