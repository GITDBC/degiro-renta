# Standard libraries
import io
import logging
from dataclasses import replace
from datetime import date
from decimal import Decimal

# 3pps
import pytest
from rich.console import Console

# Own modules
from degiro_renta import build_report_data, calculate_fifo, print_report
from degiro_renta.calculation.wash_sale import uncovered_windows
from degiro_renta.cli import PACKAGE_LOGGER, collect_notices
from degiro_renta.domain.income import OtherIncome
from degiro_renta.domain.money import percentage_of
from degiro_renta.domain.operations import (
    AcquisitionMatch,
    Operation,
    OperationType,
    Sale,
)
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.helpers import Notice
from degiro_renta.reporting.income import OTHER_INCOME_CATEGORY, other_income_notices
from degiro_renta.reporting.tax_report import print_notices
from degiro_renta.reporting.wash_sale import WASH_SALE_CATEGORY, wash_sale_notices
from tests.conftest import make_console, make_dividend, make_sale, make_statement

ISIN = "IE0000000001"


def op(day: date, kind: OperationType, quantity: int, amount: str) -> Operation:
    """
    Build an operation with no fees on a fixed ISIN.
    """

    return Operation(
        date=day,
        time="10:00",
        isin=ISIN,
        product="TEST",
        operation_type=kind,
        quantity=quantity,
        amount_eur=Decimal(amount),
        fee_eur=Decimal(0),
    )


def report_for(operations: list[Operation], last_date: date | None) -> ReportData:
    """
    Build the 2026 report of some operations over a statement ending then.
    """

    sales, _ = calculate_fifo(operations)
    statement = replace(make_statement(operations=operations), last_date=last_date)

    return build_report_data(sales, statement, year=2026)


# Bought for 1000 in January and sold for 800 on 10 March: a 200 loss
# whose two-month window runs until 10 May.
BUY = op(date(2026, 1, 5), OperationType.BUY, 10, "-1000")
SELL_AT_LOSS = op(date(2026, 3, 10), OperationType.SELL, 10, "800")


def test_a_loss_with_its_window_still_open_is_noted() -> None:
    """
    A loss whose window outlasts the statement says so.
    """

    report = report_for([BUY, SELL_AT_LOSS], date(2026, 4, 1))

    assert [item.loss_eur for item in report.wash_sale.uncovered] == [Decimal("-200")]
    assert report.wash_sale.uncovered[0].window_end == date(2026, 5, 10)


def test_a_window_the_statement_covers_is_not_noted() -> None:
    """
    A statement that reaches the end of the window leaves nothing open.
    """

    report = report_for([BUY, SELL_AT_LOSS], date(2026, 5, 10))

    assert report.wash_sale.uncovered == ()


def test_a_gain_is_never_noted() -> None:
    """
    Only a loss can be deferred, so a gain has no window to warn about.
    """

    report = report_for(
        [BUY, op(date(2026, 3, 10), OperationType.SELL, 10, "1500")],
        date(2026, 4, 1),
    )

    assert report.wash_sale.uncovered == ()


def test_a_statement_with_no_date_notes_nothing() -> None:
    """
    Without a last date there is nothing to compare the window with.
    """

    sales, _ = calculate_fifo([BUY, SELL_AT_LOSS])

    assert uncovered_windows(sales, (), None) == ()


def test_a_loss_already_deferred_is_not_noted() -> None:
    """
    A loss the rule already deferred in full cannot be deferred again.
    """

    repurchase = op(date(2026, 3, 20), OperationType.BUY, 10, "-800")

    report = report_for([BUY, SELL_AT_LOSS, repurchase], date(2026, 4, 1))

    assert report.wash_sale.deferrals[0].deferred_eur == Decimal("-200.00")
    assert report.wash_sale.uncovered == ()


def test_only_the_part_still_imputed_is_noted() -> None:
    """
    With 4 of 10 units repurchased, 80 is deferred and 120 stays open.
    """

    repurchase = op(date(2026, 3, 20), OperationType.BUY, 4, "-320")

    report = report_for([BUY, SELL_AT_LOSS, repurchase], date(2026, 4, 1))

    assert report.wash_sale.deferrals[0].deferred_eur == Decimal("-80.00")
    assert [item.loss_eur for item in report.wash_sale.uncovered] == [
        Decimal("-120.00")
    ]


def test_the_wash_sale_notice_names_the_loss_and_the_rule() -> None:
    """
    The note carries the loss, the ISIN and the date the window ends.
    """

    report = report_for([BUY, SELL_AT_LOSS], date(2026, 4, 1))

    notices = wash_sale_notices(report)

    assert len(notices) == 1
    assert notices[0].category == WASH_SALE_CATEGORY
    assert "-200.00 EUR" in notices[0].message
    assert ISIN in notices[0].message
    assert "10-05-2026" in notices[0].message
    assert wash_sale_notices(report_for([BUY], date(2026, 4, 1))) == []


def test_the_other_income_notice_appears_only_with_such_income() -> None:
    """
    The promotions note is raised when there is a promotion, not before.
    """

    promotion = OtherIncome(date(2026, 4, 3), "Promoción", Decimal("27"))

    with_income = build_report_data(
        [], make_statement(other_income=(promotion,)), year=2026
    )
    without = build_report_data([make_sale(2026, "10")], make_statement(), year=2026)

    assert [n.category for n in other_income_notices(with_income)] == [
        OTHER_INCOME_CATEGORY
    ]
    assert other_income_notices(without) == []


def test_notices_are_grouped_by_category_in_order_of_appearance() -> None:
    """
    Each category is printed once, with its own notes under it.
    """

    console, buf = make_console()

    print_notices(
        console,
        [
            Notice("primero", "Extracto"),
            Notice("segundo", "Regla"),
            Notice("tercero", "Extracto"),
        ],
    )
    out = buf.getvalue()

    assert out.count("Extracto") == 1
    assert out.count("Regla") == 1
    assert out.index("Extracto") < out.index("primero") < out.index("tercero")
    assert out.index("tercero") < out.index("Regla") < out.index("segundo")


def test_a_severe_notice_is_red_and_the_rest_yellow() -> None:
    """
    An error is told apart from a warning by its color.
    """

    console = Console(file=io.StringIO(), force_terminal=True, color_system="standard")

    print_notices(
        console,
        [Notice("grave", "Extracto", severe=True), Notice("leve", "Extracto")],
    )
    out = console.file.getvalue()  # type: ignore[attr-defined]

    assert "\x1b[31m" in out
    assert "\x1b[33m" in out


def test_notices_sit_between_the_title_and_the_first_section() -> None:
    """
    The report opens with its title, then the notes, then the sections.
    """

    console, buf = make_console()
    report = build_report_data([make_sale(2026, "10")], make_statement(), year=2026)

    print_report(report, console=console, notices=[Notice("aviso único", "Extracto")])
    out = buf.getvalue()

    assert out.index("INFORME FISCAL") < out.index("aviso único")
    assert out.index("aviso único") < out.index("Ventas del ejercicio")


def test_the_collector_turns_warnings_into_notices(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Warnings and errors of the package travel with the report.

    They are kept off the log meanwhile, and what is below a warning is
    passed on untouched.
    """

    log = logging.getLogger(f"{PACKAGE_LOGGER}.parsing")

    with caplog.at_level(logging.INFO), collect_notices() as notices:
        log.info("solo informativo")
        log.warning("un aviso")
        log.error("un error")

    assert [(item.message, item.severe) for item in notices] == [
        ("un aviso", False),
        ("un error", True),
    ]
    assert all(item.category == "Extracto" for item in notices)
    assert "solo informativo" in caplog.text
    assert "un aviso" not in caplog.text


def test_the_collector_leaves_the_logger_as_it_found_it() -> None:
    """
    The handler is removed and propagation is restored, whatever it was.
    """

    package = logging.getLogger(PACKAGE_LOGGER)

    for propagate in (True, False):
        package.propagate = propagate
        handlers = list(package.handlers)

        with collect_notices():
            pass

        assert package.propagate is propagate
        assert package.handlers == handlers

    package.propagate = True


def test_a_failed_run_still_logs_its_warnings(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    If the run fails midway the warnings reach the log, not the void.
    """

    log = logging.getLogger(f"{PACKAGE_LOGGER}.parsing")

    with caplog.at_level(logging.WARNING), pytest.raises(RuntimeError):
        with collect_notices() as notices:
            log.warning("aviso antes del fallo")
            raise RuntimeError("fallo")

    assert notices == []
    assert "aviso antes del fallo" in caplog.text
    assert logging.getLogger(PACKAGE_LOGGER).propagate is True


def table_rows(out: str) -> dict[str, str]:
    """
    Read the two-column summary table into label and amount.
    """

    return {
        line.split("│")[1].strip(): line.split("│")[2].strip()
        for line in out.splitlines()
        if line.count("│") == 3 and "Concepto" not in line
    }


def test_the_summary_adds_up_from_the_base_to_the_net_return() -> None:
    """
    Base, quota, amount to pay and net return follow from one another.

    A gain of 1000 and a dividend of 100 with 19 withheld make a base of
    1100 and a quota of 209, so 190 is left to pay. The net return takes
    the quota and the costs off the realized 1100.
    """

    statement = make_statement(
        dividends=[make_dividend(2026, "100", "19")],
        connectivity_fees=Decimal("5"),
        interest_expense=Decimal("3"),
    )
    report = build_report_data([make_sale(2026, "1000")], statement, year=2026)
    console, buf = make_console()

    print_report(report, console=console)
    rows = table_rows(buf.getvalue())

    assert rows["BASE DEL AHORRO"] == "1100.00"
    assert rows["CUOTA ESTIMADA"] == "209.00"
    assert rows["Retenciones españolas (pago a cuenta)"] == "-19.00"
    assert rows["A INGRESAR"] == "190.00"
    assert rows["Resultado antes de impuestos y gastos"] == "1100.00"
    assert rows["Cuota estimada tras deducciones"] == "-209.00"
    assert rows["Comisiones de conectividad"] == "-5.00"
    assert rows["Intereses deudores"] == "-3.00"
    assert rows["RENTABILIDAD NETA REAL"] == "883.00"


def test_the_percentage_is_on_the_transmission_and_the_total_only() -> None:
    """
    The acquisition lines carry no percentage and the transmission does.

    The transmission row closes its block, after the lines it adds up.
    """

    sale = Sale(
        date=date(2026, 6, 15),
        isin=ISIN,
        product="TEST",
        quantity=10,
        acquisition_cost=Decimal("200.00"),
        transfer_value=Decimal("250.00"),
        gain_loss=Decimal("50.00"),
        matches=(
            AcquisitionMatch(date(2026, 1, 10), 4, Decimal("80"), Decimal("90")),
            AcquisitionMatch(date(2026, 2, 10), 6, Decimal("120"), Decimal("160")),
        ),
    )
    console, buf = make_console()

    print_report(
        build_report_data([sale], make_statement(), year=2026), console=console
    )
    lines = buf.getvalue().splitlines()
    first = next(line for line in lines if "10-01-2026" in line)
    second = next(line for line in lines if "10-02-2026" in line)
    transmission = next(line for line in lines if "15-06-2026" in line)
    total = next(line for line in lines if "TOTAL" in line and "│" in line)

    assert "%" not in first
    assert "%" not in second
    assert "25.00 %" in transmission
    assert "25.00 %" in total
    assert lines.index(first) < lines.index(second) < lines.index(transmission)


@pytest.mark.parametrize(
    ("part", "whole", "expected"),
    [
        ("19.32", "360.26", "5.36"),
        ("-5.79", "43.75", "-13.23"),
        ("2402.48", "65427.62", "3.67"),
        ("10", "0", None),
    ],
)
def test_percentage_of_rounds_half_up_and_guards_zero(
    part: str, whole: str, expected: str | None
) -> None:
    """
    A percentage has two decimals and nothing to measure against is None.
    """

    result = percentage_of(Decimal(part), Decimal(whole))

    assert result == (Decimal(expected) if expected is not None else None)
