# Standard libraries
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

# 3pps
import pytest

# Own modules
from degiro_renta import parse_account_xlsx
from degiro_renta.domain.operations import Operation
from tests.conftest import account_row, write_account_xlsx

ISIN = "ES0000000001"
REFUND = "Promoción DEGIRO reembolso"


def trade(order: str, day: str, *, cost: float, tax: float = 0.0) -> list[list[object]]:
    """
    Build the rows of a purchase: the trade, its transaction cost and a tax.
    """

    rows = [
        account_row(
            "Compra 10 Foo@10 EUR (ES0000000001)",
            currency="EUR",
            amount=-100.0,
            isin=ISIN,
            order_id=order,
            date_str=day,
        ),
        account_row(
            "Costes de transacción y/o externos de DEGIRO",
            currency="EUR",
            amount=-cost,
            isin=ISIN,
            order_id=order,
            date_str=day,
        ),
    ]

    if tax:
        rows.append(
            account_row(
                "Spanish Transaction Tax",
                currency="EUR",
                amount=-tax,
                isin=ISIN,
                order_id=order,
                date_str=day,
            )
        )

    return rows


def refund(amount: float, day: str = "03-04-2026") -> list[object]:
    """
    Build the refund row, which carries no order and no instrument.
    """

    return account_row(REFUND, currency="EUR", amount=amount, date_str=day)


def fees_of(operations: list[Operation]) -> list[Decimal]:
    """
    Fees of the operations in order, as positive amounts.
    """

    return [abs(operation.fee_eur) for operation in operations]


def parse(tmp_path: Path, rows: list[list[object]]) -> tuple[list[Decimal], int]:
    """
    Parse the rows and return the fees charged and the other income found.
    """

    statement = parse_account_xlsx(write_account_xlsx(tmp_path / "Account.xlsx", rows))

    return fees_of(statement.operations), len(statement.other_income)


def test_the_refund_repays_the_oldest_costs_first(tmp_path: Path) -> None:
    """
    27 EUR repay the first costs, up to the order that exhausts them.

    The costs are 2, 2 and 2: the refund of 3 repays the first and half
    of the second, and the third is charged in full.
    """

    rows = [
        *trade("A", "10-01-2026", cost=2),
        *trade("B", "11-01-2026", cost=2),
        *trade("C", "12-01-2026", cost=2),
        refund(3),
    ]

    fees, other = parse(tmp_path, rows)

    assert fees == [Decimal(0), Decimal(1), Decimal(2)]
    assert other == 0


def test_a_tax_charged_beside_the_cost_is_not_repaid(tmp_path: Path) -> None:
    """
    The promotion repays the broker's costs, not the Spanish tax.
    """

    rows = [*trade("A", "10-01-2026", cost=2, tax=0.5), refund(5)]

    fees, other = parse(tmp_path, rows)

    assert fees == [Decimal("0.5")]
    assert other == 1


def test_what_the_costs_cannot_absorb_is_reported_as_income(
    tmp_path: Path,
) -> None:
    """
    A refund over the costs charged leaves the rest to be reviewed.
    """

    statement = parse_account_xlsx(
        write_account_xlsx(
            tmp_path / "Account.xlsx",
            [*trade("A", "10-01-2026", cost=2), refund(5)],
        )
    )

    assert fees_of(statement.operations) == [Decimal(0)]
    assert [item.amount_eur for item in statement.other_income] == [Decimal(3)]
    assert statement.other_income[0].date == date(2026, 4, 3)


def test_a_refund_does_not_repay_costs_charged_after_it(tmp_path: Path) -> None:
    """
    It repays what had been charged by its date, not what comes later.
    """

    rows = [
        *trade("A", "10-01-2026", cost=2),
        *trade("B", "20-04-2026", cost=2),
        refund(4),
    ]

    fees, other = parse(tmp_path, rows)

    assert fees == [Decimal(0), Decimal(2)]
    assert other == 1


def test_a_second_refund_continues_where_the_first_stopped(tmp_path: Path) -> None:
    """
    Two refunds repay the costs one after the other, never the same twice.
    """

    rows = [
        *trade("A", "10-01-2026", cost=2),
        *trade("B", "11-01-2026", cost=2),
        refund(2, "03-04-2026"),
        refund(2, "03-05-2026"),
    ]

    fees, other = parse(tmp_path, rows)

    assert fees == [Decimal(0), Decimal(0)]
    assert other == 0


def test_the_refund_is_noted_in_the_report(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """
    The adjustment is not silent: the statement says what was done.
    """

    rows = [*trade("A", "10-01-2026", cost=2), refund(2)]

    with caplog.at_level(logging.WARNING):
        parse(tmp_path, rows)

    assert "Promoción DEGIRO reembolso" in caplog.text
    assert "arts. 35.1.b y 35.2" in caplog.text
