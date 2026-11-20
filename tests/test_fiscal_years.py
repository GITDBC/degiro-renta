# Standard libraries
from datetime import date
from decimal import Decimal

# 3pps
import pytest

# Own modules
from degiro_renta import calculate_fifo
from degiro_renta.calculation.currency import calculate_currency_gains
from degiro_renta.calculation.report_data import activity_years, build_report_data
from degiro_renta.domain.currency import CurrencyConversion
from degiro_renta.domain.income import DividendIncome
from degiro_renta.domain.operations import Operation, OperationType
from tests.conftest import make_sale, make_statement


def test_a_loss_offsets_the_gains_of_the_following_exercise() -> None:
    """
    A 2023 capital-gains loss reduces the 2024 gain (art. 49 LIRPF).
    """

    sales = [
        make_sale(
            2023,
            "-1000.00",
            month=3,
            day=1,
            isin="IE0000000001",
            product="A",
            quantity=10,
            acquisition_cost="1000.00",
        ),
        make_sale(
            2024,
            "1500.00",
            month=3,
            day=1,
            isin="IE0000000002",
            product="B",
            quantity=10,
            acquisition_cost="500.00",
        ),
    ]

    report = build_report_data(sales, make_statement(), year=2024)

    assert report.savings_base.prior_gains_losses_applied == Decimal("1000")
    assert report.savings_base.total == Decimal("500")
    assert report.loss_carryforward == ()


def test_a_loss_expires_after_the_four_exercises_that_follow() -> None:
    """
    A loss from 2020 cannot be offset in 2025: the window is four years.
    """

    sales = [
        make_sale(
            2020,
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

    report = build_report_data(sales, make_statement(), year=2025)

    assert report.savings_base.prior_gains_losses_applied == Decimal("0")
    assert report.savings_base.total == Decimal("1500")


def test_an_unused_loss_is_listed_with_its_expiry() -> None:
    """
    A loss left after its exercise is reported with the last year to use it.
    """

    sales = [
        make_sale(
            2023,
            "-1000.00",
            month=3,
            day=1,
            isin="IE0000000001",
            product="A",
            quantity=10,
            acquisition_cost="1000.00",
        ),
    ]

    report = build_report_data(sales, make_statement(), year=2023)

    assert len(report.loss_carryforward) == 1
    assert report.loss_carryforward[0].origin_year == 2023
    assert report.loss_carryforward[0].amount_eur == Decimal("1000")
    assert report.loss_carryforward[0].expires_after == 2027


def test_a_purchase_in_2026_sold_in_2028_keeps_its_cost() -> None:
    """
    FIFO runs over the whole history, so the 2028 sale carries the 2026 cost.
    """

    operations = [
        Operation(
            date=date(2026, 3, 1),
            time="10:00",
            isin="IE0000000001",
            product="A",
            operation_type=OperationType.BUY,
            quantity=10,
            amount_eur=Decimal("-1000"),
            fee_eur=Decimal("0"),
        ),
        Operation(
            date=date(2028, 5, 1),
            time="10:00",
            isin="IE0000000001",
            product="A",
            operation_type=OperationType.SELL,
            quantity=10,
            amount_eur=Decimal("1500"),
            fee_eur=Decimal("0"),
        ),
    ]
    sales, _ = calculate_fifo(operations)
    statement = make_statement(operations=operations)

    report_2028 = build_report_data(sales, statement, year=2028)

    assert report_2028.savings_base.capital_gains == Decimal("500")
    assert report_2028.sales[0].acquisition_cost == Decimal("1000.00")


def test_the_last_exercise_with_activity_is_the_default() -> None:
    """
    Without an explicit year the report is for the last exercise with movements.
    """

    sales = [
        make_sale(
            2024,
            "100.00",
            month=3,
            day=1,
            isin="IE0000000001",
            product="A",
            quantity=10,
            acquisition_cost="100.00",
        ),
        make_sale(
            2026,
            "200.00",
            month=3,
            day=1,
            isin="IE0000000002",
            product="B",
            quantity=10,
            acquisition_cost="100.00",
        ),
    ]

    report = build_report_data(sales, make_statement())

    assert report.year == 2026
    assert activity_years(sales, make_statement()) == [2024, 2026]


def test_an_exercise_without_activity_is_refused() -> None:
    """
    Asking for an exercise with no movements gives a clear error.
    """

    sales = [
        make_sale(
            2026,
            "100.00",
            month=3,
            day=1,
            isin="IE0000000001",
            product="A",
            quantity=10,
            acquisition_cost="100.00",
        ),
    ]

    with pytest.raises(ValueError, match="No hay actividad en el ejercicio 2025"):
        build_report_data(sales, make_statement(), year=2025)


def test_a_us_dividend_is_deducted_up_to_the_treaty_cap() -> None:
    """
    The US withholding above 15% is not deductible and is reclaimable.

    Base 1100 EUR at 19% gives a quota of 209 EUR. The 100 EUR dividend is
    a share of 100/1100 of it, which is 19 EUR: the lower of that limit and
    the 15 EUR creditable within the cap is deducted.
    """

    sales = [
        make_sale(
            2026,
            "1000.00",
            month=3,
            day=1,
            isin="IE0000000001",
            product="A",
            quantity=10,
            acquisition_cost="1000.00",
        ),
    ]
    dividend = DividendIncome(
        date=date(2026, 6, 1),
        isin="US0378331005",
        product="APPLE",
        gross_eur=Decimal("100"),
        withholding_eur=Decimal("30"),
        domestic=False,
    )
    statement = make_statement(dividends=[dividend])

    report = build_report_data(sales, statement)

    assert report.savings_base.total == Decimal("1100")
    assert report.foreign_deduction == Decimal("15.00")
    assert report.foreign_excess == Decimal("15.00")
    assert report.foreign_unused_limit == Decimal("0.00")


def test_a_currency_round_trip_yields_its_gain() -> None:
    """
    Buying 1200 USD for 1000 EUR and selling them for 1100 EUR gains 100 EUR.
    """

    conversions = (
        CurrencyConversion(
            date=date(2026, 1, 10),
            time="10:00",
            eur_amount=Decimal("-1000"),
            foreign_amount=Decimal("1200"),
            foreign_currency="USD",
        ),
        CurrencyConversion(
            date=date(2026, 3, 10),
            time="10:00",
            eur_amount=Decimal("1100"),
            foreign_amount=Decimal("-1200"),
            foreign_currency="USD",
        ),
    )

    gains = calculate_currency_gains(conversions)

    assert len(gains) == 1
    assert gains[0].gain_eur == Decimal("100.00")
    assert gains[0].cost_eur == Decimal("1000.00")


def test_a_disposal_without_a_known_cost_is_skipped() -> None:
    """
    Units never bought in the statement have no cost, so no gain is invented.
    """

    conversions = (
        CurrencyConversion(
            date=date(2026, 1, 10),
            time="10:00",
            eur_amount=Decimal("1100"),
            foreign_amount=Decimal("-1200"),
            foreign_currency="USD",
        ),
    )

    assert calculate_currency_gains(conversions) == ()
