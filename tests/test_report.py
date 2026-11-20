# Standard libraries
from dataclasses import replace
from datetime import date
from decimal import Decimal

# 3pps
import pytest

# Own modules
from degiro_renta import build_report_data, print_report
from degiro_renta.domain.income import DividendIncome, OtherIncome
from degiro_renta.domain.operations import (
    AcquisitionMatch,
    Operation,
    OperationType,
    Sale,
    UnvaluedOperation,
)
from tests.conftest import make_buy, make_console, make_sale, make_statement


@pytest.fixture
def simple_sales() -> list[Sale]:
    """
    Return a synthetic sale with a positive gain/loss of 50 EUR.
    """

    return [
        make_sale(
            2026,
            "50.00",
            month=3,
            day=1,
            isin="IE0000000099",
            product="TEST",
            quantity=10,
        )
    ]


@pytest.fixture
def losing_sales() -> list[Sale]:
    """
    Return a synthetic sale closing at a 50 EUR loss.
    """

    return [
        make_sale(
            2026,
            "-50.00",
            month=3,
            day=1,
            isin="IE0000000099",
            product="TEST",
            quantity=10,
            acquisition_cost="200.00",
        )
    ]


def render(  # noqa: PLR0913 - test render helper
    sales: list[Sale],
    *,
    connectivity_fees: Decimal = Decimal(0),
    dividends: list[DividendIncome] | None = None,
    operations: list[Operation] | None = None,
) -> str:
    """
    Build the report aggregates and render them to a string.

    Args:
        sales: Sales matched by FIFO.
        connectivity_fees: Total connectivity fees for the period.
        dividends: Dividends collected during the period.
        operations: Operations behind the sales, needed by the
            two-month rule.

    Returns:
        The rendered report as plain text.
    """

    console, buf = make_console()
    print_report(
        build_report_data(
            sales,
            make_statement(
                operations=operations,
                dividends=dividends,
                connectivity_fees=connectivity_fees,
            ),
        ),
        console=console,
    )

    return buf.getvalue()


def test_print_report_includes_sections_with_tax(
    simple_sales: list[Sale],
) -> None:
    """
    Verify that with tax all the key sections are printed.
    """

    out = render(simple_sales, connectivity_fees=Decimal("5.00"))

    assert "Ventas del ejercicio" in out
    assert "Resumen fiscal" in out
    assert "Ganancias y pérdidas patrimoniales del ejercicio" in out
    assert "50.00" in out
    assert "CUOTA ESTIMADA" in out
    assert "9.50" in out
    assert "RENTABILIDAD NETA REAL" in out
    assert "IE0000000099" in out


def test_declaration_lines_show_the_acquisition_date(
    simple_sales: list[Sale],
) -> None:
    """
    The declaration block lists the acquisition date of each line.

    Without it the user cannot fill the return, which asks for the
    acquisition date of every transferred element.
    """

    sale = simple_sales[0]
    detailed = [
        replace(
            sale,
            matches=(
                AcquisitionMatch(
                    acquisition_date=date(2026, 1, 15),
                    quantity=10,
                    acquisition_cost=Decimal("100.00"),
                    transfer_value=Decimal("150.00"),
                ),
            ),
        )
    ]

    out = render(detailed)

    assert "Adquis." in out
    assert "15-01-2026" in out
    assert "Valor transm." in out


def test_a_loss_line_with_a_repurchase_raises_the_two_month_block(
    simple_sales: list[Sale],
) -> None:
    """
    A line in loss with a repurchase still held is deferred and shown.

    The ten units sold are all transmitted, and five are bought back on
    10 March and kept: art. 33.5.f LIRPF defers the loss of five units in
    loss, the -5.00 EUR of the first line.
    """

    sale = simple_sales[0]
    detailed = [
        replace(
            sale,
            matches=(
                AcquisitionMatch(
                    acquisition_date=date(2026, 1, 15),
                    quantity=5,
                    acquisition_cost=Decimal("80.00"),
                    transfer_value=Decimal("75.00"),
                ),
                AcquisitionMatch(
                    acquisition_date=date(2026, 2, 20),
                    quantity=5,
                    acquisition_cost=Decimal("20.00"),
                    transfer_value=Decimal("75.00"),
                ),
            ),
        )
    ]
    operations = [
        make_buy("IE0000000099", 5, "-80.00", "0.00", day=15),
        Operation(
            date=date(2026, 2, 20),
            time="10:00",
            isin="IE0000000099",
            product="TEST",
            operation_type=OperationType.BUY,
            quantity=5,
            amount_eur=Decimal("-20.00"),
            fee_eur=Decimal("0.00"),
        ),
        Operation(
            date=date(2026, 3, 1),
            time="10:00",
            isin="IE0000000099",
            product="TEST",
            operation_type=OperationType.SELL,
            quantity=10,
            amount_eur=Decimal("150.00"),
            fee_eur=Decimal("0.00"),
        ),
        Operation(
            date=date(2026, 3, 10),
            time="10:00",
            isin="IE0000000099",
            product="TEST",
            operation_type=OperationType.BUY,
            quantity=5,
            amount_eur=Decimal("-14.00"),
            fee_eur=Decimal("0.00"),
        ),
    ]

    out = render(detailed, operations=operations)

    assert "Regla de los dos meses" in out
    assert "10-03-2026" in out
    assert "-5.00" in out


def test_a_loss_line_without_repurchases_is_left_alone(
    simple_sales: list[Sale],
) -> None:
    """
    No two-month block appears when nothing was bought in the window.

    The acquisition the loss comes from is the element transmitted, not
    a repurchase of it, so on its own it raises nothing.
    """

    sale = simple_sales[0]
    detailed = [
        replace(
            sale,
            matches=(
                AcquisitionMatch(
                    acquisition_date=date(2026, 1, 15),
                    quantity=10,
                    acquisition_cost=Decimal("160.00"),
                    transfer_value=Decimal("150.00"),
                ),
            ),
        )
    ]
    operations = [make_buy("IE0000000099", 10, "-160.00", "0.00", day=15)]

    out = render(detailed, operations=operations)

    assert "regla de los dos meses" not in out


def test_a_foreign_withholding_is_not_subtracted_from_the_quota(
    simple_sales: list[Sale],
) -> None:
    """
    The report sends a foreign withholding to the deduction, not the quota.

    Treating it as a payment on account would refund a tax Spain never
    collected.
    """

    dividends = [
        DividendIncome(
            date=date(2026, 6, 18),
            isin="US0378331005",
            product="APPLE INC",
            gross_eur=Decimal("100.00"),
            withholding_eur=Decimal("15.00"),
            domestic=False,
        )
    ]

    out = render(simple_sales, dividends=dividends)

    assert "Extranjero" in out
    assert "doble imposición" in out
    assert "Retenciones españolas (pago a cuenta)" not in out


def test_interest_reaches_the_base_and_its_own_block() -> None:
    """
    Credit interest is shown and integrated into the savings base.
    """

    console, buf = make_console()
    print_report(
        build_report_data(
            [],
            make_statement(interest_income=Decimal("12.34")),
        ),
        console=console,
    )
    out = buf.getvalue()

    assert "Intereses de la cuenta" in out
    assert "12.34" in out


def test_debit_interest_only_reduces_the_net_return() -> None:
    """
    Interest charged on the balance reduces the real return only.

    It is neither a FIFO cost nor a deductible expense of the returns.
    """

    console, buf = make_console()
    print_report(
        build_report_data(
            [],
            make_statement(interest_expense=Decimal("3.00")),
        ),
        console=console,
    )

    out = buf.getvalue()

    assert "Intereses deudores" in out
    assert "-3.00" in out
    assert "RENTABILIDAD NETA REAL" in out


def test_excluded_trades_are_named_in_red() -> None:
    """
    A trade with no euro value is listed, not quietly missing.
    """

    unvalued = (
        UnvaluedOperation(
            date=date(2026, 1, 15),
            isin="US0000000099",
            description="Compra 10 Fake@10 USD (US0000000099)",
            amount=Decimal("-100.00"),
            currency="USD",
        ),
    )
    console, buf = make_console()
    print_report(
        build_report_data(
            [],
            make_statement(unvalued_operations=unvalued),
        ),
        console=console,
    )
    out = buf.getvalue()

    assert "Operaciones excluidas por no tener contravalor en EUR" in out
    assert "US0000000099" in out


def test_promotions_are_shown_outside_the_base() -> None:
    """
    A promotion is reported without being integrated into any base.
    """

    other = (
        OtherIncome(
            date=date(2026, 4, 3),
            description="Promoción DEGIRO reembolso",
            amount_eur=Decimal("27.00"),
        ),
    )
    console, buf = make_console()
    print_report(
        build_report_data(
            [],
            make_statement(other_income=other),
        ),
        console=console,
    )
    out = buf.getvalue()

    assert "Otros importes abonados" in out
    assert "27.00" in out
    # Nothing to tax: the amount stays out of the savings base.
    assert "BASE DEL AHORRO" in out
    assert "A INGRESAR" not in out


def test_print_report_without_sales() -> None:
    """
    Verify that without sales it prints total 0 and no net return.
    """

    out = render([])

    assert "Ganancias y pérdidas patrimoniales del ejercicio" in out
    assert "0.00" in out
    assert "Sin ventas en el ejercicio." in out
    assert "RENTABILIDAD NETA" not in out
    assert "A INGRESAR" not in out


def test_net_return_lists_only_the_costs_there_are(
    simple_sales: list[Sale],
) -> None:
    """
    Without connectivity fees or debit interest no cost row appears.
    """

    out = render(simple_sales)

    assert "RENTABILIDAD NETA REAL" in out
    assert "Comisiones de conectividad" not in out
    assert "Intereses deudores" not in out


def test_print_report_loss_shows_the_realized_loss_without_quota(
    losing_sales: list[Sale],
) -> None:
    """
    A net loss has no quota to pay, yet the return is still reported.

    The return is the realized result, so the loss must be visible, and
    the quota block says there is nothing to tax.
    """

    out = render(losing_sales)

    assert "RENTABILIDAD NETA" in out
    assert "A INGRESAR" not in out


def test_print_report_without_dividends_states_it() -> None:
    """
    The dividend section is always rendered, empty when there are none.

    Keeping the section visible tells the user the concept was
    considered rather than silently skipped.
    """

    out = render([])

    assert "Dividendos cobrados" in out
    assert "Sin dividendos en el ejercicio." in out


def test_print_report_shows_dividends_and_withholdings(
    simple_sales: list[Sale],
) -> None:
    """
    Dividends, their withholding and the resulting net are rendered.

    The withholding is a payment on account, so it must be visible
    apart from the gross amount and subtracted from the quota.
    """

    dividends = [
        DividendIncome(
            date=date(2026, 7, 10),
            isin="ES0118594417",
            product="INDRA SISTEMAS SA",
            gross_eur=Decimal("9.00"),
            withholding_eur=Decimal("1.71"),
        )
    ]

    out = render(simple_sales, dividends=dividends)

    assert "Dividendos cobrados" in out
    assert "INDRA SISTEMAS SA" in out
    assert "9.00" in out
    assert "-1.71" in out
    assert "7.29" in out

    # Savings base = 50.00 gains + 9.00 dividends; quota = 19% = 11.21.
    assert "BASE DEL AHORRO" in out
    assert "59.00" in out
    assert "11.21" in out
    assert "Retenciones españolas (pago a cuenta)" in out
    assert "A INGRESAR" in out


def test_withholdings_above_the_quota_yield_a_refund() -> None:
    """
    An excess withholding is reported as an amount to be refunded.

    The withholding is 19% of the gross dividend, which matches the
    first bracket, so any extra retained must come back.
    """

    dividends = [
        DividendIncome(
            date=date(2026, 7, 10),
            isin="ES0118594417",
            product="INDRA SISTEMAS SA",
            gross_eur=Decimal("100.00"),
            withholding_eur=Decimal("30.00"),
        )
    ]

    out = render([], dividends=dividends)

    assert "A DEVOLVER" in out
    assert "11.00" in out


def test_losses_offset_dividends_up_to_the_legal_limit(
    losing_sales: list[Sale],
) -> None:
    """
    A negative gains balance only offsets 25% of the dividend balance.

    The rest is not lost: it is reported as carried forward to the next
    four years (art. 49 LIRPF).
    """

    dividends = [
        DividendIncome(
            date=date(2026, 7, 10),
            isin="ES0118594417",
            product="INDRA SISTEMAS SA",
            gross_eur=Decimal("100.00"),
            withholding_eur=Decimal("19.00"),
        )
    ]

    out = render(losing_sales, dividends=dividends)

    # Losses of 50.00 may only offset 25.00 (25% of 100.00 dividends).
    assert "Compensación de pérdidas" in out
    assert "-25.00" in out
    assert "Saldos negativos pendientes de compensar" in out
