# Standard libraries
from datetime import date
from decimal import Decimal

# 3pps
import pytest

# Own modules
from degiro_renta import calculate_fifo
from degiro_renta.calculation.wash_sale import (
    add_months,
    detect_wash_sales,
    wash_sale_adjustments,
)
from degiro_renta.domain.operations import Operation, OperationType
from tests.conftest import make_buy, make_sell


@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (date(2026, 3, 15), -2, date(2026, 1, 15)),
        (date(2026, 3, 15), 2, date(2026, 5, 15)),
        (date(2026, 1, 15), -2, date(2025, 11, 15)),
        (date(2026, 11, 15), 2, date(2027, 1, 15)),
        # The day is clamped when the target month is shorter, so the
        # window never lands on a date that does not exist.
        (date(2026, 4, 30), -2, date(2026, 2, 28)),
        (date(2026, 12, 31), 2, date(2027, 2, 28)),
    ],
)
def test_the_window_moves_by_whole_months(
    start: date, months: int, expected: date
) -> None:
    """
    Two months means the same day two months over, clamped to the month.
    """

    assert add_months(start, months) == expected


def test_a_repurchase_defers_the_loss_while_the_units_are_held() -> None:
    """
    Buying back within two months keeps the loss out of the year.

    The 100 units bought back are still held after the sale, so the whole
    loss is deferred and kept as pending until they are transmitted.
    """

    operations = [
        make_buy("ES0000000001", 100, "-5000", "0", day=1),
        make_sell("ES0000000001", 100, "4000", "0", day=15),
        make_buy("ES0000000001", 100, "-4200", "0", day=20),
    ]
    sales, _ = calculate_fifo(operations)

    result = detect_wash_sales(sales, operations)

    assert len(result.deferrals) == 1
    deferral = result.deferrals[0]
    assert deferral.transfer_date == date(2026, 1, 15)
    assert deferral.repurchased_units == 100
    assert deferral.deferred_eur == Decimal("-1000.00")
    assert deferral.repurchase_dates == (date(2026, 1, 20),)
    assert result.releases == ()
    assert result.pending[0].isin == "ES0000000001"
    assert result.pending[0].units == 100
    assert wash_sale_adjustments(result) == (
        (date(2026, 1, 15), "ES0000000001", Decimal("1000.00")),
    )


def test_a_repurchase_outside_the_window_is_not_deferred() -> None:
    """
    A loss with no purchase inside the window is simply deductible.

    The single purchase before the sale is also excluded: it was the only
    one in its window and no security was held when that window opened.
    """

    operations = [
        make_buy("ES0000000001", 100, "-5000", "0", day=1),
        make_sell("ES0000000001", 100, "4000", "0", day=15),
    ]
    sales, _ = calculate_fifo(operations)

    result = detect_wash_sales(sales, operations)

    assert result.deferrals == ()
    assert result.pending == ()


def test_a_gain_is_never_deferred() -> None:
    """
    The rule defers losses only; a profitable sale raises nothing.
    """

    operations = [
        make_buy("ES0000000001", 100, "-4000", "0", day=1),
        make_sell("ES0000000001", 100, "5000", "0", day=15),
        make_buy("ES0000000001", 100, "-5200", "0", day=20),
    ]
    sales, _ = calculate_fifo(operations)

    assert detect_wash_sales(sales, operations).deferrals == ()


def test_a_closed_position_imputes_the_loss_in_full() -> None:
    """
    Nothing repurchased is still held, so there is nothing to defer.

    Manual chapter 11: when no homogeneous security remains after the
    transmission, the loss is imputed in full in the year it was made.
    """

    operations = [
        make_buy("ES0000000001", 10, "-500", "0", day=1),
        make_buy("ES0000000001", 10, "-100", "0", day=10),
        make_sell("ES0000000001", 20, "800", "0", day=20),
    ]
    sales, _ = calculate_fifo(operations)

    result = detect_wash_sales(sales, operations)

    assert result.deferrals == ()
    assert result.pending == ()


def test_only_the_repurchased_share_is_deferred() -> None:
    """
    When fewer units are bought back than sold, only they are deferred.

    Thirty of the one hundred units sold are repurchased and held, so
    thirty percent of the loss is deferred.
    """

    operations = [
        make_buy("ES0000000001", 100, "-5000", "0", day=1),
        make_sell("ES0000000001", 100, "4000", "0", day=15),
        make_buy("ES0000000001", 30, "-1260", "0", day=20),
    ]
    sales, _ = calculate_fifo(operations)

    deferral = detect_wash_sales(sales, operations).deferrals[0]

    assert deferral.repurchased_units == 30
    assert deferral.deferred_eur == Decimal("-300.00")


def test_repurchases_count_once_per_transmission_not_per_line() -> None:
    """
    Two loss lines of one sale share the same repurchased units.

    Forty and sixty units were bought on two days and sold together; the
    thirty units bought back are counted once, so 30% of the 1000 EUR
    loss is deferred, not 30% of each line.
    """

    operations = [
        make_buy("ES0000000001", 40, "-2000", "0", day=1),
        make_buy("ES0000000001", 60, "-3000", "0", day=2),
        make_sell("ES0000000001", 100, "4000", "0", day=15),
        make_buy("ES0000000001", 30, "-1260", "0", day=20),
    ]
    sales, _ = calculate_fifo(operations)

    result = detect_wash_sales(sales, operations)

    assert sales[0].gain_loss == Decimal("-1000")
    assert result.deferrals[0].deferred_eur == Decimal("-300.00")


def test_repurchases_are_matched_to_the_units_sold_in_loss() -> None:
    """
    A winning sale can still carry a loss line that the rule defers.

    The first lot lost 100 EUR on 10 units; five units were repurchased,
    so the loss of five units in loss is deferred: half of it. The gain
    of the other lot is never deferred, and FIFO identifies which units
    were transmitted (manual chapter 11, section C).
    """

    operations = [
        make_buy("ES0000000001", 10, "-500", "0", day=1),
        make_buy("ES0000000001", 10, "-100", "0", day=10),
        make_sell("ES0000000001", 20, "800", "0", day=20),
        make_buy("ES0000000001", 5, "-200", "0", day=25),
    ]
    sales, _ = calculate_fifo(operations)

    deferral = detect_wash_sales(sales, operations).deferrals[0]

    assert sales[0].gain_loss == Decimal("200")
    assert deferral.repurchased_units == 5
    assert deferral.deferred_eur == Decimal("-50.00")


def test_another_isin_bought_in_the_window_does_not_count() -> None:
    """
    Only homogeneous securities defer a loss, not any purchase.
    """

    operations = [
        make_buy("ES0000000001", 100, "-5000", "0", day=1),
        make_sell("ES0000000001", 100, "4000", "0", day=15),
        make_buy("ES0000000002", 100, "-4200", "0", day=20),
    ]
    sales, _ = calculate_fifo(operations)

    assert detect_wash_sales(sales, operations).deferrals == ()


def test_the_pending_loss_is_released_at_a_definitive_transmission() -> None:
    """
    A later sale with no purchase in its window imputes the deferred loss.

    The sale in June has no purchase within two months of it, so it is
    definitive: the 1000 EUR deferred in January is imputed on that day.
    """

    operations = [
        make_buy("ES0000000001", 100, "-5000", "0", day=1),
        make_sell("ES0000000001", 100, "4000", "0", day=15),
        make_buy("ES0000000001", 100, "-4200", "0", day=20),
        Operation(
            date=date(2026, 6, 1),
            time="10:00",
            isin="ES0000000001",
            product="TEST",
            operation_type=OperationType.SELL,
            quantity=100,
            amount_eur=Decimal("4300"),
            fee_eur=Decimal("0"),
        ),
    ]
    sales, _ = calculate_fifo(operations)

    result = detect_wash_sales(sales, operations)

    assert len(result.releases) == 1
    assert result.releases[0].release_date == date(2026, 6, 1)
    assert result.releases[0].transfer_date == date(2026, 1, 15)
    assert result.releases[0].released_eur == Decimal("-1000.00")
    assert result.pending == ()
