# 3pps
from rich.console import Console

# Own modules
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.helpers import (
    format_date,
    format_decimal,
    new_table,
    print_section,
    signed_amount,
)


def render_currency_gains(console: Console, data: ReportData) -> None:
    """
    Render the gains and losses of currency exchanges with no trade.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    if not data.currency_gains:
        return

    print_section(
        console,
        "Ganancias y pérdidas por cambio de divisa",
        "FIFO por divisa sobre los cambios sin operación asociada, "
        "imputados al convertir (arts. 33.1 y 14.2.e LIRPF)",
    )

    table = new_table()
    table.add_column("Fecha")
    table.add_column("Divisa")
    table.add_column("Unidades", justify="right")
    table.add_column("Transmitido EUR", justify="right")
    table.add_column("Coste EUR", justify="right")
    table.add_column("G/P", justify="right")

    for gain in data.currency_gains:
        table.add_row(
            format_date(gain.date),
            gain.currency,
            format_decimal(gain.units),
            format_decimal(gain.proceeds_eur),
            format_decimal(gain.cost_eur),
            signed_amount(gain.gain_eur),
        )

    console.print(table)


def render_unvalued_operations(console: Console, data: ReportData) -> None:
    """
    Render the trades left out for having no euro consideration.

    How to compute them apart is said in the notice under the title.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    if not data.unvalued_operations:
        return

    print_section(
        console,
        "Operaciones excluidas por no tener contravalor en EUR",
        "El extracto no trae el cambio de divisa de estas órdenes",
    )

    table = new_table()
    table.add_column("Fecha")
    table.add_column("ISIN")
    table.add_column("Concepto", max_width=44, overflow="ellipsis")
    table.add_column("Importe", justify="right")
    table.add_column("Divisa")

    for operation in data.unvalued_operations:
        table.add_row(
            format_date(operation.date),
            operation.isin,
            operation.description,
            format_decimal(operation.amount),
            operation.currency,
        )

    console.print(table)
