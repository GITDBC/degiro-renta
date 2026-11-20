# Standard libraries
from decimal import Decimal
from typing import Final

# 3pps
from rich.console import Console
from rich.table import Table
from rich.text import Text

# Own modules
from degiro_renta.calculation.declaration import (
    DeclarationTotals,
    calculate_declaration_totals,
)
from degiro_renta.domain.operations import Sale
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.helpers import (
    bold_text,
    format_date,
    format_decimal,
    new_table,
    print_section,
    signed_amount,
)

# Style of the row that stands for the transmission of a sale: a
# bold background, so the text keeps its colors.
TRANSMISSION_STYLE: Final[str] = "bold on grey23"


def _percentage(value: Decimal | None, *, bold: bool = False) -> Text | str:
    """
    Format a gain or loss percentage, colored by its sign.

    Args:
        value: Percentage, or ``None`` when it cannot be measured.
        bold: Whether to add bold to the color.

    Returns:
        The colored percentage, or an empty cell when there is none.
    """

    if value is None:
        return ""

    return signed_amount(value, bold=bold, suffix=" %")


def _add_sale_rows(table: Table, sale: Sale) -> None:
    """
    Add a sale to the table, with one line per acquisition date.

    Columns follow the chronology: acquisition first, transmission
    after, then the result. A sale that consumed a single lot fits in
    one row. One that consumed lots bought on different days lists a
    row per acquisition date, which are the lines the return asks for,
    and closes with a row, on a background, for the transmission as a
    whole.

    Args:
        table: Table being filled.
        sale: Sale matched by FIFO.

    Returns:
        None.
    """

    transmission: list[str | Text] = [
        format_date(sale.date),
        sale.isin,
        sale.product,
        str(sale.quantity),
        format_decimal(sale.acquisition_cost),
        format_decimal(sale.transfer_value),
        signed_amount(sale.gain_loss, bold=True),
        _percentage(sale.gain_loss_pct, bold=True),
    ]

    if len(sale.matches) <= 1:
        acquired = format_date(sale.matches[0].acquisition_date) if sale.matches else ""
        table.add_row(acquired, *transmission, style=TRANSMISSION_STYLE)
        return

    for match in sale.matches:
        table.add_row(
            format_date(match.acquisition_date),
            "",
            sale.isin,
            sale.product,
            str(match.quantity),
            format_decimal(match.acquisition_cost),
            format_decimal(match.transfer_value),
            signed_amount(match.gain_loss),
            "",
        )

    table.add_row("", *transmission, style=TRANSMISSION_STYLE)


def _print_sales_table(console: Console, sales: list[Sale], result_header: str) -> None:
    """
    Print the sales with their acquisition lines and the totals.

    The totals add up the lines, which is what the return holds; a
    rounding difference against the total per sale is disclosed below.

    Args:
        console: Rich Console instance for output.
        sales: Sales matched by FIFO.
        result_header: Header of the last column, which holds the result.

    Returns:
        None.
    """

    table = new_table()
    table.add_column("Adquis.", no_wrap=True)
    table.add_column("Transm.", no_wrap=True)
    table.add_column("ISIN", no_wrap=True)
    # The issuer name is what the return asks for, so it is never cut:
    # a truncated name is a name you have to go and look up elsewhere.
    table.add_column("Producto", overflow="fold")
    table.add_column("Cant.", justify="right")
    table.add_column("Valor adq.", justify="right")
    table.add_column("Valor transm.", justify="right")
    table.add_column(result_header, justify="right")
    table.add_column("%", justify="right")

    for index, sale in enumerate(sales):
        if index:
            table.add_section()
        _add_sale_rows(table, sale)

    totals = calculate_declaration_totals(sales)

    table.add_section()
    table.add_row(
        bold_text("TOTAL"),
        "",
        "",
        "",
        "",
        bold_text(format_decimal(totals.acquisition_cost)),
        bold_text(format_decimal(totals.transfer_value)),
        signed_amount(totals.gain_loss, bold=True),
        _percentage(totals.gain_loss_pct, bold=True),
    )

    console.print(table)
    _warn_on_rounding_drift(console, totals)


def render_sales(console: Console, data: ReportData) -> None:
    """
    Render the sales of the exercise, ready to type into the return.

    The return declares every transferred element with its acquisition
    date and value, so a sale that consumed lots bought on different
    days is broken down into one line per date even though it was a
    single order. Values are the broker's real euros with the fees
    already inside both of them (art. 35 LIRPF): they must not be
    deducted again.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    print_section(console, "Ventas del ejercicio (FIFO por ISIN)")

    if not data.sales:
        console.print("[dim]Sin ventas en el ejercicio.[/dim]")
        return

    _print_sales_table(console, data.sales, "G/P")


def _warn_on_rounding_drift(console: Console, totals: DeclarationTotals) -> None:
    """
    Warn when the declared lines drift from the real sale total.

    Rounding each line to the cent can differ by a few cents from the
    gain computed once per sale. The sale total is the accurate figure,
    so the difference is disclosed instead of hidden.

    Args:
        console: Rich Console instance for output.
        totals: Aggregates of the declared lines.

    Returns:
        None.
    """

    if totals.rounding_drift == 0:
        return

    drift = format_decimal(totals.rounding_drift)
    real = format_decimal(totals.real_gain_loss)

    console.print(
        f"[dim]El total de las líneas difiere en {drift} EUR del total real "
        f"({real} EUR) por redondear cada línea al céntimo.[/dim]"
    )


def render_debt_sales(console: Console, data: ReportData) -> None:
    """
    Render the transmissions of financial assets of art. 25.2 LIRPF.

    Their result is capital income, not a capital gain, so the return
    declares them in a different section and they integrate into the
    capital-income block of the savings base.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    if not data.debt_sales:
        return

    print_section(
        console,
        "Transmisión de activos financieros (art. 25.2.b LIRPF)",
        "Rendimiento del capital mobiliario: va con dividendos e intereses, "
        "no con las ganancias y pérdidas patrimoniales",
    )
    _print_sales_table(console, data.debt_sales, "Rendimiento")
