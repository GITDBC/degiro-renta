# 3pps
from rich.console import Console

# Own modules
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.helpers import (
    format_decimal,
    new_table,
    print_section,
)


def render_loss_carryforward(console: Console, data: ReportData) -> None:
    """
    Render the negative balances still waiting to be offset.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    if not data.loss_carryforward:
        return

    print_section(
        console,
        "Saldos negativos pendientes de compensar (art. 49 LIRPF)",
        "Primero con su propio bloque y después con el otro, hasta el 25 %, "
        "en los ejercicios siguientes hasta el plazo "
        "indicado",
    )

    table = new_table()
    table.add_column("Generado en")
    table.add_column("Tipo")
    table.add_column("Pendiente", justify="right")
    table.add_column("Compensable hasta")

    for entry in data.loss_carryforward:
        table.add_row(
            str(entry.origin_year),
            entry.kind.value,
            format_decimal(entry.amount_eur),
            str(entry.expires_after),
        )

    console.print(table)


def render_foreign_credit(console: Console, data: ReportData) -> None:
    """
    Render the double-taxation deduction for withholdings taken abroad.

    The deduction reduces the quota (art. 80 LIRPF). The part of the
    foreign withholding above the treaty cap is reclaimable at the source
    country, and the part the limit of art. 80.1.b blocks is not
    recovered in this return.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    if not (
        data.foreign_deduction
        or data.foreign_excess
        or data.foreign_unused_limit
        or data.unverified_treaty_countries
    ):
        return

    print_section(
        console,
        "Deducción por doble imposición internacional (art. 80 LIRPF)",
        "Menor entre la retención extranjera admisible y el límite de la "
        "cuota por la proporción de rentas extranjeras",
    )
    console.print(f"Deducción aplicada: -{format_decimal(data.foreign_deduction)} EUR")

    if data.foreign_excess > 0:
        console.print(
            f"[yellow]Retención por encima del tope del convenio: "
            f"{format_decimal(data.foreign_excess)} EUR. Reclámala al país de "
            f"origen.[/yellow]"
        )

    if data.foreign_unused_limit > 0:
        console.print(
            f"[yellow]Retención admisible no deducible por el límite de la "
            f"cuota: {format_decimal(data.foreign_unused_limit)} EUR.[/yellow]"
        )

    if data.unverified_treaty_countries:
        countries = ", ".join(data.unverified_treaty_countries)
        console.print(
            f"[yellow]Tope del 15 % no verificado para {countries}: es el tipo "
            f"habitual de los convenios españoles sobre dividendos. Compruébalo "
            f"en la tabla de convenios de la AEAT.[/yellow]"
        )
