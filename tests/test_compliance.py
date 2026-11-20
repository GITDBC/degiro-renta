# Standard libraries
import io
from datetime import date
from decimal import Decimal

# 3pps
from rich.console import Console

# Own modules
from degiro_renta import build_report_data, calculate_fifo, print_report
from degiro_renta.calculation.double_taxation import calculate_foreign_credit
from degiro_renta.calculation.savings_base import integrate_savings_base
from degiro_renta.calculation.wash_sale import detect_wash_sales
from degiro_renta.domain.income import DividendIncome
from degiro_renta.domain.operations import Operation, OperationType, UnvaluedOperation
from degiro_renta.domain.report import ReportData
from degiro_renta.domain.savings import BalanceKind, LossCarryforward
from tests.conftest import make_sale, make_statement

ETP_ISIN = "XS2940466316"


def op(  # noqa: PLR0913 - test operation builder
    day: date, isin: str, kind: OperationType, quantity: int, amount: str
) -> Operation:
    """
    Build an operation with no fees for the compliance scenarios.
    """

    return Operation(
        date=day,
        time="10:00",
        isin=isin,
        product="TEST",
        operation_type=kind,
        quantity=quantity,
        amount_eur=Decimal(amount),
        fee_eur=Decimal(0),
    )


def rendered(report: ReportData) -> str:
    """
    Render a report to plain text.
    """

    console = Console(file=io.StringIO(), width=140)
    print_report(report, console=console)

    return console.file.getvalue()


def test_the_manual_worked_example_of_chapter_12() -> None:
    """
    Reproduce the savings-base case of the Manual práctico de Renta 2025.

    Capital income -800, gains 4000, pending gains losses of 700 (2021)
    and 2100 (2022), pending negative capital income of 500 (2021). The
    manual offsets the -800 against the gains within the 25% limit of
    1000, then the 2800 of pending losses, and then 200 of the pending
    capital income, the rest of the shared limit. The base is 200.
    """

    pending = (
        LossCarryforward(2021, Decimal("700"), 2025, BalanceKind.GAINS),
        LossCarryforward(2021, Decimal("500"), 2025, BalanceKind.CAPITAL_INCOME),
        LossCarryforward(2022, Decimal("2100"), 2026, BalanceKind.GAINS),
    )

    savings, left = integrate_savings_base(
        2025, Decimal("4000"), Decimal(0), debt_income=Decimal("-800"), pending=pending
    )

    assert savings.capital_income_offset == Decimal("800")
    assert savings.prior_gains_losses_applied == Decimal("2800")
    assert savings.prior_capital_income_applied == Decimal("200.00")
    assert savings.total == Decimal("200.00")
    assert left == (
        LossCarryforward(2021, Decimal("300.00"), 2025, BalanceKind.CAPITAL_INCOME),
    )


def test_earlier_losses_offset_capital_income_within_25_percent() -> None:
    """
    A pending capital-gains loss also offsets dividends, up to 25%.

    A 1000 EUR loss of 2024 meets 400 EUR of dividends and no gain in
    2025: 100 EUR is offset, so the base is 300 and 900 stay pending.
    """

    sales = [
        make_sale(
            2024,
            "-1000.00",
            month=3,
            day=1,
            isin="IE0000000001",
            product="A",
            quantity=10,
            acquisition_cost="1000.00",
        )
    ]
    dividend = DividendIncome(
        date(2025, 6, 1), "ES0000000009", "B", Decimal("400"), Decimal("76"), True
    )

    report = build_report_data(sales, make_statement(dividends=[dividend]), year=2025)

    assert report.savings_base.total == Decimal("300.00")
    assert report.loss_carryforward[0].amount_eur == Decimal("900.00")


def test_the_25_percent_limit_is_shared_with_the_year_loss() -> None:
    """
    The year's own loss and the pending ones share one 25% limit.

    A loss of 50 EUR in the year takes 25 of the 25 EUR that 100 EUR of
    dividends allow, so the pending 1000 EUR get nothing this year.
    """

    savings, left = integrate_savings_base(
        2025,
        Decimal("-50"),
        Decimal("100"),
        pending=(LossCarryforward(2024, Decimal("1000"), 2028),),
    )

    assert savings.total == Decimal("75.00")
    assert savings.prior_gains_losses_applied == Decimal(0)
    assert sorted(entry.amount_eur for entry in left) == [
        Decimal("25.00"),
        Decimal("1000"),
    ]


def test_the_savings_base_table_adds_up() -> None:
    """
    Every row of the savings-base table adds up to the base.

    Gains of 1500 in 2025 minus the 1000 pending from 2024 give 500: the
    table shows the 1500 of the year, not the balance after the offset.
    """

    sales = [
        make_sale(
            2024,
            "-1000.00",
            month=3,
            day=1,
            isin="IE0000000001",
            product="A",
            quantity=10,
            acquisition_cost="1000.00",
        ),
        make_sale(
            2025,
            "1500.00",
            month=3,
            day=1,
            isin="IE0000000002",
            product="B",
            quantity=10,
            acquisition_cost="500.00",
        ),
    ]

    out = rendered(build_report_data(sales, make_statement(), year=2025))

    rows = {
        line.split("│")[1].strip(): line.split("│")[2].strip()
        for line in out.splitlines()
        if line.count("│") >= 3
    }

    assert rows["Ganancias y pérdidas patrimoniales del ejercicio"] == "1500.00"
    assert rows["Pérdidas patrimoniales de ejercicios anteriores (art. 49)"] == (
        "-1000.00"
    )
    assert rows["BASE DEL AHORRO"] == "500.00"


def test_an_excluded_isin_is_reported_in_every_exercise() -> None:
    """
    An unvalued trade excludes the whole history of its ISIN.

    So the exclusion is shown in the report of every exercise, not only
    in the one of the unvalued trade.
    """

    sales = [
        make_sale(
            2026,
            "10.00",
            month=3,
            day=1,
            isin="IE0000000001",
            product="A",
            quantity=10,
            acquisition_cost="100.00",
        )
    ]
    unvalued = (
        UnvaluedOperation(
            date(2025, 3, 1),
            "US0000000001",
            "Compra 10",
            Decimal("-100"),
            "USD",
        ),
    )

    report = build_report_data(
        sales,
        make_statement(unvalued_operations=unvalued),
        year=2026,
    )

    assert report.unvalued_operations == unvalued


def test_an_unknown_country_is_capped_at_15_percent_and_flagged() -> None:
    """
    A German dividend with 26.375% withheld is credited only up to 15%.
    """

    dividend = DividendIncome(
        date(2026, 6, 1),
        "DE0007164600",
        "SAP",
        Decimal("100"),
        Decimal("26.375"),
        False,
    )

    credit = calculate_foreign_credit([dividend], Decimal("950"), Decimal("5000"))

    assert credit.creditable == Decimal("15.00")
    assert credit.deduction == Decimal("15.00")
    assert credit.excess == Decimal("11.38")
    assert credit.unverified_countries == ("DE",)


def test_the_average_rate_is_expressed_with_two_decimals() -> None:
    """
    The limit uses the average effective rate rounded to two decimals.

    A quota of 2000 over a base of 10500 is 19.047...%, taken as 19.05%,
    so 100 EUR taxed abroad allow 19.05 EUR.
    """

    dividend = DividendIncome(
        date(2026, 6, 1),
        "US0378331005",
        "APPLE",
        Decimal("100"),
        Decimal("30"),
        False,
    )

    credit = calculate_foreign_credit([dividend], Decimal("2000"), Decimal("10500"))

    assert credit.creditable == Decimal("15.00")
    assert credit.deduction == Decimal("15.00")
    assert credit.unverified_countries == ()

    small = calculate_foreign_credit([dividend], Decimal("10"), Decimal("1000"))

    assert small.deduction == Decimal("1.00")


def test_a_debt_security_goes_to_capital_income() -> None:
    """
    The result of selling the ETP is capital income of art. 25.2 LIRPF.

    A 500 EUR gain on it joins the dividends block, not the gains block,
    so it is absent from the capital-gains total.
    """

    operations = [
        op(date(2026, 1, 10), ETP_ISIN, OperationType.BUY, 10, "-1000"),
        op(date(2026, 6, 10), ETP_ISIN, OperationType.SELL, 10, "1500"),
    ]
    sales, _ = calculate_fifo(operations)

    report = build_report_data(sales, make_statement(operations=operations))

    assert report.savings_base.capital_gains == Decimal(0)
    assert report.savings_base.debt_income == Decimal("500")
    assert report.savings_base.total == Decimal("500")
    assert report.sales == []
    assert len(report.debt_sales) == 1

    out = " ".join(rendered(report).split())

    assert "Transmisión de activos financieros (art. 25.2.b LIRPF)" in out


def test_a_debt_security_loss_offsets_gains_up_to_25_percent() -> None:
    """
    A loss on the ETP is negative capital income: 25% of the gains at most.

    1000 EUR of losses on it against 2000 EUR of gains offset 500; the
    other 500 carry forward as negative capital income.
    """

    operations = [
        op(date(2026, 1, 10), ETP_ISIN, OperationType.BUY, 10, "-2000"),
        op(date(2026, 6, 10), ETP_ISIN, OperationType.SELL, 10, "1000"),
        op(date(2026, 1, 10), "IE0000000001", OperationType.BUY, 10, "-1000"),
        op(date(2026, 6, 10), "IE0000000001", OperationType.SELL, 10, "3000"),
    ]
    operations.sort(key=lambda item: item.date)
    sales, _ = calculate_fifo(operations)

    report = build_report_data(sales, make_statement(operations=operations))

    assert report.savings_base.total == Decimal("1500.00")
    assert report.loss_carryforward[0].kind is BalanceKind.CAPITAL_INCOME
    assert report.loss_carryforward[0].amount_eur == Decimal("500.00")


def test_a_deferred_loss_is_released_by_the_units_of_a_definitive_sale() -> None:
    """
    A definitive sale frees the deferred loss whichever units it sells.

    100 units held since 2025 and 50 bought in March 2026; 50 sold at a
    loss in April with a repurchase on 20 April. The sale of 50 units in
    September has no purchase near it, so it is definitive: it frees the
    loss of the 50 units deferred, though FIFO sold the oldest units and
    not the repurchased ones (DGT V0913-08, V0754-26).
    """

    isin = "ES0000000001"
    operations = [
        op(date(2025, 1, 10), isin, OperationType.BUY, 100, "-1000"),
        op(date(2026, 3, 1), isin, OperationType.BUY, 50, "-600"),
        op(date(2026, 4, 1), isin, OperationType.SELL, 50, "400"),
        op(date(2026, 4, 20), isin, OperationType.BUY, 50, "-400"),
        op(date(2026, 9, 1), isin, OperationType.SELL, 50, "500"),
        op(date(2026, 12, 1), isin, OperationType.SELL, 100, "1000"),
    ]
    sales, _ = calculate_fifo(operations)

    result = detect_wash_sales(sales, operations)

    assert len(result.deferrals) == 1
    assert result.deferrals[0].deferred_eur == Decimal("-100.00")
    assert [release.release_date for release in result.releases] == [date(2026, 9, 1)]
    assert result.releases[0].released_eur == Decimal("-100.00")
    assert result.pending == ()


def test_a_sale_with_a_repurchase_frees_only_its_definitive_units() -> None:
    """
    Only the units the sale does not repurchase free the pending loss.

    The loss of 10 units is deferred in January. The sale of 25 units in
    June has 5 bought back on 1 July, so 20 are definitive: the 10 pending
    units are freed.
    """

    isin = "ES0000000001"
    operations = [
        op(date(2026, 1, 1), isin, OperationType.BUY, 10, "-100"),
        op(date(2026, 1, 15), isin, OperationType.BUY, 10, "-100"),
        op(date(2026, 1, 20), isin, OperationType.SELL, 10, "50"),
        op(date(2026, 2, 1), isin, OperationType.BUY, 10, "-60"),
        op(date(2026, 6, 1), isin, OperationType.BUY, 5, "-50"),
        op(date(2026, 6, 10), isin, OperationType.SELL, 25, "250"),
        op(date(2026, 7, 1), isin, OperationType.BUY, 5, "-50"),
    ]
    sales, _ = calculate_fifo(operations)

    result = detect_wash_sales(sales, operations)

    assert result.deferrals[0].deferred_eur == Decimal("-50.00")
    assert [(r.release_date, r.units) for r in result.releases] == [
        (date(2026, 6, 10), 10)
    ]
    assert result.releases[0].released_eur == Decimal("-50.00")
