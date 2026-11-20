# 3pps
from rich.console import Console
from rich.table import Table

# Own modules
from degiro_renta.calculation.tax import total_quota
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.helpers import (
    bold_text,
    format_decimal,
    new_table,
    print_bullet,
    print_section,
    signed_amount,
)


def _add_savings_base_rows(table: Table, data: ReportData) -> None:
    """
    Add the integration of the two blocks of art. 49 into the base.

    Every row adds up to the base: the negative balance that is carried
    forward is added back because it is not integrated this year, and
    the negative balances of earlier years are subtracted.

    Args:
        table: Summary table being filled.
        data: Report data of the exercise.

    Returns:
        None.
    """

    savings = data.savings_base

    table.add_row("Dividendos (bruto)", format_decimal(savings.dividend_income))

    if savings.interest_income:
        table.add_row("Intereses de la cuenta", format_decimal(savings.interest_income))

    if savings.debt_income:
        table.add_row(
            "Activos financieros (art. 25.2)", format_decimal(savings.debt_income)
        )

    table.add_row(
        "Ganancias y pérdidas patrimoniales del ejercicio",
        format_decimal(savings.capital_gains),
    )

    carried = savings.carryforward_losses + savings.capital_income_carryforward

    if carried > 0:
        table.add_row(
            "Saldo negativo no integrado (pasa a ejercicios siguientes)",
            format_decimal(carried),
        )

    if savings.prior_gains_losses_applied > 0:
        table.add_row(
            "Pérdidas patrimoniales de ejercicios anteriores (art. 49)",
            format_decimal(-savings.prior_gains_losses_applied),
        )

    if savings.prior_capital_income_applied > 0:
        table.add_row(
            "Rendimientos negativos de ejercicios anteriores (art. 49)",
            format_decimal(-savings.prior_capital_income_applied),
        )

    table.add_section()
    table.add_row(
        bold_text("BASE DEL AHORRO"), bold_text(format_decimal(savings.total))
    )


def _add_quota_rows(table: Table, data: ReportData) -> None:
    """
    Add the quota over the base and what is left to pay or to refund.

    Applies the savings scale (arts. 66 and 76 LIRPF) to the base alone,
    with no personal and family minimum. The deduction of art. 80 and
    the Spanish withholdings, which are a payment on account, come off
    the quota.

    Args:
        table: Summary table being filled.
        data: Report data of the exercise.

    Returns:
        None.
    """

    brackets = data.irpf_quota or []

    table.add_section()

    for bracket in brackets:
        table.add_row(
            f"Cuota {bracket.rate * 100:.0f} % sobre {format_decimal(bracket.base)}",
            format_decimal(bracket.quota),
        )

    table.add_row(
        bold_text("CUOTA ESTIMADA"),
        bold_text(format_decimal(total_quota(brackets)), "bold yellow"),
    )

    if data.foreign_deduction > 0:
        table.add_row(
            "Deducción por doble imposición (art. 80)",
            format_decimal(-data.foreign_deduction),
        )

    if data.domestic_withholdings > 0:
        table.add_row(
            "Retenciones españolas (pago a cuenta)",
            format_decimal(-data.domestic_withholdings),
        )

    if data.quota_to_pay is None or not (brackets or data.quota_to_pay):
        return

    to_pay = data.quota_to_pay >= 0
    color = "yellow" if to_pay else "green"

    table.add_row(
        bold_text("A INGRESAR" if to_pay else "A DEVOLVER"),
        bold_text(format_decimal(abs(data.quota_to_pay)), f"bold {color}"),
    )


def _add_net_return_rows(table: Table, data: ReportData) -> None:
    """
    Add what the exercise leaves once taxes and costs are paid.

    The costs that no operation carries (connectivity fees and debit
    interest) are neither added to the FIFO cost nor integrated into the
    base, so they only reduce this return. Art. 26.1 LIRPF is a closed
    list: only what pays for the deposit or administration of the
    securities is deductible, and only from their capital income (DGT
    V2117-19, V0152-26). A market access fee is not clearly one of
    them, and a debit interest is not on the list.

    Args:
        table: Summary table being filled.
        data: Report data of the exercise.

    Returns:
        None.
    """

    if data.net_return is None:
        return

    table.add_section()
    table.add_row(
        "Resultado antes de impuestos y gastos", format_decimal(data.realized_result)
    )
    table.add_row(
        "Cuota estimada tras deducciones", format_decimal(-data.quota_after_credit)
    )

    costs = (
        ("Retención extranjera soportada", data.foreign_withholdings),
        ("Comisiones de conectividad", data.connectivity_fees),
        ("Intereses deudores", data.interest_expense),
    )

    for label, amount in costs:
        if amount > 0:
            table.add_row(label, format_decimal(-amount))

    table.add_section()
    table.add_row(
        bold_text("RENTABILIDAD NETA REAL"), signed_amount(data.net_return, bold=True)
    )


def render_summary(console: Console, data: ReportData) -> None:
    """
    Render the savings base, the quota and the net return in one table.

    Args:
        console: Rich Console instance for output.
        data: Report data of the exercise.

    Returns:
        None.
    """

    print_section(
        console,
        "Resumen fiscal",
        "Estimación orientativa: escala del ahorro estatal y autonómica "
        "(arts. 66 y 76 LIRPF), sin mínimo personal y familiar ni rentas "
        "ajenas a este extracto",
    )

    table = new_table()
    table.add_column("Concepto")
    table.add_column("EUR", justify="right")

    _add_savings_base_rows(table, data)
    _add_quota_rows(table, data)
    _add_net_return_rows(table, data)

    console.print(table)

    savings = data.savings_base

    if data.wash_sale_adjustment or data.currency_gain_loss:
        print_bullet(
            console,
            f"Ganancias y pérdidas patrimoniales: ventas "
            f"{format_decimal(data.sales_gain_loss)} EUR; regla de los dos "
            f"meses {format_decimal(data.wash_sale_adjustment)} EUR; cambios de "
            f"divisa {format_decimal(data.currency_gain_loss)} EUR.",
            style="dim",
        )

    if savings.offset_applied > 0:
        offset = format_decimal(savings.offset_applied)
        print_bullet(
            console,
            f"Compensación de pérdidas del ejercicio con rendimientos (límite "
            f"del 25 %, art. 49 LIRPF): -{offset} EUR.",
            style="dim",
        )

    if savings.capital_income_offset > 0:
        offset = format_decimal(savings.capital_income_offset)
        print_bullet(
            console,
            f"Compensación de rendimientos negativos del ejercicio con "
            f"ganancias (límite del 25 %, art. 49 LIRPF): -{offset} EUR.",
            style="dim",
        )
