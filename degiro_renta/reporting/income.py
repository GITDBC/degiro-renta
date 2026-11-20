# Standard libraries
from typing import Final

# 3pps
from rich.console import Console

# Own modules
from degiro_renta.calculation.dividends import total_dividend_income
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.helpers import (
    Notice,
    bold_text,
    format_date,
    format_decimal,
    new_table,
    print_section,
)

# Heading the note about the amounts credited is listed under.
OTHER_INCOME_CATEGORY: Final[str] = "Otros importes abonados"


def render_dividends(console: Console, data: ReportData) -> None:
    """
    Render the dividends collected and the tax withheld at source.

    The origin column is what tells a payment on account from a foreign
    tax: the first subtracts from the quota (arts. 79 and 99 LIRPF), the
    second only opens the right to the double-taxation deduction (art.
    80).

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    print_section(console, "Dividendos cobrados")

    if not data.dividends:
        console.print("[dim]Sin dividendos en el ejercicio.[/dim]")
        return

    table = new_table()
    table.add_column("Fecha")
    table.add_column("ISIN")
    table.add_column("Producto", overflow="fold")
    table.add_column("Bruto", justify="right")
    table.add_column("Retención", justify="right")
    table.add_column("Origen")
    table.add_column("Neto", justify="right")

    for dividend in data.dividends:
        table.add_row(
            format_date(dividend.date),
            dividend.isin,
            dividend.product,
            format_decimal(dividend.gross_eur),
            format_decimal(-dividend.withholding_eur),
            "España" if dividend.domestic else "Extranjero",
            format_decimal(dividend.net_eur),
        )

    gross = total_dividend_income(data.dividends)
    withheld = data.domestic_withholdings + data.foreign_withholdings

    table.add_section()
    table.add_row(
        "",
        "",
        bold_text("TOTAL"),
        bold_text(format_decimal(gross)),
        bold_text(format_decimal(-withheld)),
        "",
        bold_text(format_decimal(gross - withheld)),
    )

    console.print(table)

    if data.foreign_withholdings > 0:
        console.print(
            f"[yellow]{format_decimal(data.foreign_withholdings)} EUR de "
            f"retención extranjera: no es pago a cuenta, no se resta de la "
            f"cuota. Va a la deducción por doble imposición internacional "
            f"(art. 80 LIRPF), limitada al menor de la retención soportada, el "
            f"tope del convenio y el tipo medio efectivo de tu "
            f"declaración.[/yellow]"
        )


def render_interest_income(console: Console, data: ReportData) -> None:
    """
    Render the credit interest integrated into the savings base.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    interest = data.savings_base.interest_income

    if not interest:
        return

    print_section(
        console,
        "Intereses de la cuenta",
        "Rendimientos del capital mobiliario (art. 25.2 LIRPF), integrados en "
        "la base del ahorro junto con los dividendos",
    )
    console.print(f"Intereses abonados: {format_decimal(interest)} EUR")


def render_other_income(console: Console, data: ReportData) -> None:
    """
    Render the amounts credited that no fiscal block claims.

    Promotions and rebates depend on what the broker paid them for, so
    they are shown verbatim and left out of the base instead of being
    integrated into one they may not belong to. ``other_income_notices``
    says so under the title.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    if not data.other_income:
        return

    print_section(console, "Otros importes abonados")

    table = new_table()
    table.add_column("Fecha")
    table.add_column("Concepto", max_width=48, overflow="ellipsis")
    table.add_column("EUR", justify="right")

    for item in data.other_income:
        table.add_row(
            format_date(item.date), item.description, format_decimal(item.amount_eur)
        )

    console.print(table)


def other_income_notices(data: ReportData) -> list[Notice]:
    """
    Note that the amounts credited are left for the user to qualify.

    Promotions and rebates depend on what the broker paid them for, so
    they are shown verbatim and left out of the base.

    Args:
        data: Report data of the exercise.

    Returns:
        One notice when the exercise has such amounts, none otherwise.
    """

    if not data.other_income:
        return []

    return [
        Notice(
            "Decide su tratamiento: una promoción suele ser ganancia "
            "patrimonial de la base general; un reembolso, un menor gasto.",
            OTHER_INCOME_CATEGORY,
        )
    ]
