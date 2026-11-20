# Standard libraries
from datetime import date
from decimal import Decimal

# Own modules
from degiro_renta import calculate_fifo
from degiro_renta.calculation.wash_sale import detect_wash_sales
from degiro_renta.domain.operations import Operation, OperationType
from degiro_renta.domain.wash_sale import WashSaleResult

ISIN = "ES0000000001"

# The scenarios below are the worked cases of the binding consultations of
# the DGT on art. 33.5.f LIRPF, with their dates, units and results. The
# documentation summarises each criterion with its reference.


def buy(day: date, units: int, price: str) -> Operation:
    """
    Build a purchase of ``units`` at ``price`` each, with no fees.
    """

    return Operation(
        date=day,
        time="10:00",
        isin=ISIN,
        product="TEST",
        operation_type=OperationType.BUY,
        quantity=units,
        amount_eur=-Decimal(price) * units,
        fee_eur=Decimal(0),
    )


def sell(day: date, units: int, price: str) -> Operation:
    """
    Build a sale of ``units`` at ``price`` each, with no fees.
    """

    return Operation(
        date=day,
        time="10:00",
        isin=ISIN,
        product="TEST",
        operation_type=OperationType.SELL,
        quantity=units,
        amount_eur=Decimal(price) * units,
        fee_eur=Decimal(0),
    )


def run(operations: list[Operation]) -> WashSaleResult:
    """
    Apply the two-month rule to operations given in chronological order.
    """

    sales, _ = calculate_fifo(operations)

    return detect_wash_sales(sales, operations)


def test_v0913_08_the_loss_that_is_deferred_is_the_one_of_the_last_units() -> None:
    """
    The units acquired first are the ones whose loss is imputed (V0913-08).

    1005 units sold on 15 February, 995 of them repurchased: the loss left
    out is the one of 95 units of January and 900 of February, 144,500
    EUR, and the 10 units of January are imputed.
    """

    result = run(
        [
            buy(date(2026, 1, 1), 105, "950"),
            buy(date(2026, 2, 10), 900, "1000"),
            sell(date(2026, 2, 15), 1005, "850"),
            buy(date(2026, 3, 1), 950, "990"),
            buy(date(2026, 3, 10), 15, "980"),
            buy(date(2026, 4, 5), 30, "900"),
        ]
    )

    deferral = result.deferrals[0]

    assert deferral.repurchased_units == 995
    assert deferral.deferred_eur == Decimal("-144500.00")


def test_v0913_08_a_definitive_sale_frees_the_oldest_pending_units() -> None:
    """
    The sale of 1 April is definitive for 955 of its 965 units (V0913-08).

    The 995 units counted on 15 February are not counted again, so only the
    10 bought on 16 April are a repurchase. The 955 definitive units free
    the loss of 95 units of January and 860 of February, 138,500 EUR; the
    sale defers the loss of the 10 units it repurchased, 300 EUR.
    """

    result = run(
        [
            buy(date(2026, 1, 1), 105, "950"),
            buy(date(2026, 2, 10), 900, "1000"),
            sell(date(2026, 2, 15), 1005, "850"),
            buy(date(2026, 3, 1), 950, "990"),
            buy(date(2026, 3, 10), 15, "980"),
            sell(date(2026, 4, 1), 965, "950"),
            buy(date(2026, 4, 5), 30, "900"),
            buy(date(2026, 4, 16), 10, "820"),
        ]
    )

    first, second = result.deferrals

    assert first.repurchased_units == 995
    assert second.repurchased_units == 10
    assert second.deferred_eur == Decimal("-300.00")
    assert [(r.units, r.released_eur) for r in result.releases] == [
        (955, Decimal("-138500.00"))
    ]
    assert [(p.units, p.deferred_eur) for p in result.pending] == [
        (50, Decimal("-6300.00"))
    ]


def test_v0913_08_the_prior_purchases_are_capped_by_the_units_still_held() -> None:
    """
    120 units sold with 25 bought in the two months before (V0913-08).

    Only 5 remain held after the sale and one more is bought the day
    after, so 10 units are repurchased in all.
    """

    result = run(
        [
            buy(date(2026, 1, 1), 100, "100"),
            buy(date(2026, 3, 1), 10, "100"),
            buy(date(2026, 4, 1), 15, "85"),
            sell(date(2026, 4, 15), 120, "80"),
            buy(date(2026, 4, 16), 5, "81"),
        ]
    )

    assert result.deferrals[0].repurchased_units == 10


def test_v1117_21_the_first_units_sold_keep_their_loss() -> None:
    """
    The loss that can be imputed is the one of the first units (V1117-21).

    1008 units bought first lose 2 EUR each and the 2000 bought later lose
    4 EUR each. With 2000 units repurchased, the 1008 first ones are
    imputed and the 8000 EUR loss of the other 2000 is deferred.
    """

    result = run(
        [
            buy(date(2025, 1, 10), 1008, "10"),
            buy(date(2025, 6, 10), 2000, "12"),
            sell(date(2026, 3, 1), 3008, "8"),
            buy(date(2026, 3, 20), 2000, "8"),
        ]
    )

    assert result.deferrals[0].deferred_eur == Decimal("-8000.00")


def test_v3282_18_a_purchase_counts_for_one_transmission_only() -> None:
    """
    Four sales in the same weeks, each with its own purchase (V3282-18).

    The loss of 20 February takes the purchase of 15 March, the one of 26
    March takes the 20 March one, and the sales of 31 March and 5 April
    take the 24 and 28 March ones, so none of them is definitive.
    """

    result = run(
        [
            buy(date(2026, 2, 5), 4000, "10"),
            sell(date(2026, 2, 8), 4000, "10.10"),
            buy(date(2026, 2, 15), 4000, "10"),
            sell(date(2026, 2, 20), 2000, "9.75"),
            buy(date(2026, 3, 15), 2000, "10"),
            buy(date(2026, 3, 20), 2000, "10"),
            buy(date(2026, 3, 24), 2000, "10"),
            sell(date(2026, 3, 26), 2000, "9.70"),
            buy(date(2026, 3, 28), 2000, "10"),
            sell(date(2026, 3, 31), 2000, "10.20"),
            buy(date(2026, 4, 1), 2000, "10"),
            sell(date(2026, 4, 5), 2000, "10.05"),
        ]
    )

    assert [d.repurchase_dates for d in result.deferrals] == [
        (date(2026, 3, 15),),
        (date(2026, 3, 20),),
    ]
    assert [d.deferred_eur for d in result.deferrals] == [
        Decimal("-500.00"),
        Decimal("-600.00"),
    ]
    assert result.releases == ()


def test_v1760_23_each_definitive_sale_frees_the_oldest_pending_loss() -> None:
    """
    Three sales in July free the losses of four in May and June (V1760-23).

    The sale of 2000 frees the 800 EUR of 5 May, the one of 3000 frees the
    500 EUR of 9 May and the one of 990 frees 990 of the 3000 units of 10
    May. The 10 units left in hand keep the rest pending.
    """

    result = run(
        [
            buy(date(2022, 5, 4), 6000, "10"),
            sell(date(2022, 5, 5), 2000, "9.60"),
            buy(date(2022, 5, 6), 5000, "10"),
            sell(date(2022, 5, 9), 3000, "9.8333333333333333"),
            sell(date(2022, 5, 10), 3000, "9.7666666666666667"),
            buy(date(2022, 6, 10), 3000, "10"),
            sell(date(2022, 6, 17), 3000, "9.9333333333333333"),
            buy(date(2022, 6, 20), 3000, "10"),
            sell(date(2022, 7, 19), 2000, "9.875"),
            sell(date(2022, 7, 20), 3000, "9.9333333333333333"),
            sell(date(2022, 7, 21), 990, "9.9494949494949495"),
        ]
    )

    assert [d.deferred_eur for d in result.deferrals] == [
        Decimal("-800.00"),
        Decimal("-500.00"),
        Decimal("-700.00"),
        Decimal("-200.00"),
    ]
    assert [(r.release_date, r.units) for r in result.releases] == [
        (date(2022, 7, 19), 2000),
        (date(2022, 7, 20), 3000),
        (date(2022, 7, 21), 990),
    ]
    assert [r.released_eur for r in result.releases[:2]] == [
        Decimal("-800.00"),
        Decimal("-500.00"),
    ]
    assert result.releases[2].released_eur == Decimal("-231.00")


def test_v0571_21_a_sale_with_a_purchase_the_same_day_frees_nothing() -> None:
    """
    The sale of 11 August has 7000 units bought that day (V0571-21).

    It is not definitive, so it frees nothing; the sale of 25 December
    frees the 800 EUR of 5 July and 1000 of the 3000 units of 8 July.
    """

    result = run(
        [
            buy(date(2020, 7, 4), 6000, "10"),
            sell(date(2020, 7, 5), 2000, "9.60"),
            buy(date(2020, 7, 6), 5000, "10"),
            sell(date(2020, 7, 8), 3000, "9.8333333333333333"),
            sell(date(2020, 7, 9), 3000, "9.7666666666666667"),
            buy(date(2020, 8, 10), 3000, "10"),
            sell(date(2020, 8, 11), 2000, "10"),
            buy(date(2020, 8, 11), 7000, "10"),
            sell(date(2020, 12, 25), 3000, "9.9333333333333333"),
        ]
    )

    assert [r.release_date for r in result.releases] == [date(2020, 12, 25)] * 2
    assert [r.units for r in result.releases] == [2000, 1000]
    assert result.releases[0].released_eur == Decimal("-800.00")


def test_v1294_22_the_units_not_repurchased_are_the_definitive_ones() -> None:
    """
    18,000 units sold with 10,000 bought two months before (V1294-22).

    The other 8000 are definitive, which frees the loss deferred in 2020
    for 5000 units, in the exercise of this sale.
    """

    result = run(
        [
            buy(date(2008, 1, 10), 18000, "10"),
            buy(date(2020, 12, 18), 5000, "10"),
            sell(date(2020, 12, 31), 5000, "9.5"),
            buy(date(2021, 10, 28), 10000, "9"),
            sell(date(2021, 12, 21), 18000, "8"),
        ]
    )

    assert result.deferrals[0].transfer_date == date(2020, 12, 31)
    assert result.deferrals[0].repurchased_units == 5000
    assert [(r.release_date, r.units) for r in result.releases] == [
        (date(2021, 12, 21), 5000)
    ]
    assert result.deferrals[1].repurchased_units == 10000
