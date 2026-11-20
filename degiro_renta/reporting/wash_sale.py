# Standard libraries
from typing import Final

# 3pps
from rich.console import Console

# Own modules
from degiro_renta.domain.money import ZERO
from degiro_renta.domain.report import ReportData
from degiro_renta.domain.wash_sale import WashSalePending
from degiro_renta.reporting.helpers import (
    Notice,
    format_date,
    format_decimal,
    new_table,
    print_bullet,
    print_section,
    signed_amount,
)

# Heading of the rule, for its section and for the notes about it.
WASH_SALE_CATEGORY: Final[str] = "Regla de los dos meses (arts. 33.5.f y 25.2.b LIRPF)"


def render_wash_sales(console: Console, data: ReportData) -> None:
    """
    Render the two-month rule: deferred, imputed and pending losses.

    Deferred losses are the part of a loss the rule keeps out of the year
    of the transmission. Imputed losses are the ones released at a later
    definitive transmission, and the year to declare them is the release
    date. Pending losses are still waiting at the end of the exercise.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    result = data.wash_sale

    if not (result.deferrals or result.releases or result.pending):
        return

    print_section(console, WASH_SALE_CATEGORY)

    if result.deferrals:
        table = new_table()
        table.add_column("Transm.")
        table.add_column("ISIN")
        table.add_column("Cant.", justify="right")
        table.add_column("Recompradas", justify="right")
        table.add_column("Diferido", justify="right")
        table.add_column("Compras en la ventana")

        for deferral in result.deferrals:
            table.add_row(
                format_date(deferral.transfer_date),
                deferral.isin,
                str(deferral.sold_units),
                str(deferral.repurchased_units),
                signed_amount(deferral.deferred_eur),
                ", ".join(format_date(day) for day in deferral.repurchase_dates),
            )

        console.print(table)
        deferred_total = sum((d.deferred_eur for d in result.deferrals), ZERO)
        print_bullet(
            console,
            f"Diferido en el ejercicio: {format_decimal(deferred_total)} EUR, "
            f"ya excluido de la base.",
            style="yellow",
        )

    if result.releases:
        table = new_table()
        table.add_column("Imputación")
        table.add_column("Origen")
        table.add_column("ISIN")
        table.add_column("Uds.", justify="right")
        table.add_column("Pérdida imputada", justify="right")

        for release in result.releases:
            table.add_row(
                format_date(release.release_date),
                format_date(release.transfer_date),
                release.isin,
                str(release.units),
                signed_amount(release.released_eur),
            )

        console.print(table)

    for pending in result.pending:
        _render_pending_deferral(console, pending)


def wash_sale_notices(data: ReportData) -> list[Notice]:
    """
    Note the losses whose two-month window the statement does not cover.

    A purchase made after the last row of the statement, within the two
    months that follow a transmission in loss, would defer that loss, and
    the statement cannot tell. These notes go under the title of the
    report instead of a section of their own.

    Args:
        data: Report data of the exercise.

    Returns:
        One notice per transmission whose window outlasts the statement.
    """

    return [
        Notice(
            f"La pérdida de {format_decimal(item.loss_eur)} EUR en {item.isin} "
            f"({format_date(item.transfer_date)}) se imputa en el ejercicio, "
            f"pero su ventana llega al {format_date(item.window_end)} y el "
            f"extracto termina antes. Si compras o compraste ese valor hasta "
            f"esa fecha, la pérdida se difiere.",
            WASH_SALE_CATEGORY,
        )
        for item in data.wash_sale.uncovered
    ]


def _render_pending_deferral(console: Console, pending: WashSalePending) -> None:
    """
    Print a deferred loss still pending at the end of the exercise.

    Args:
        console: Rich Console instance for output.
        pending: Deferred loss of one ISIN.

    Returns:
        None.
    """

    print_bullet(
        console,
        f"Pendiente de imputar en {pending.isin}: "
        f"{format_decimal(pending.deferred_eur)} EUR ({pending.units} uds.). "
        f"Se imputará, la más antigua primero, a medida que transmitas de "
        f"forma definitiva esas unidades u otras del mismo valor.",
        style="yellow",
    )
