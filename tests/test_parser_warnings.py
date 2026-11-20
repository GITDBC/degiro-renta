# Standard libraries
import logging
from decimal import Decimal
from pathlib import Path

# 3pps
import pytest

# Own modules
from degiro_renta import parse_account_xlsx
from degiro_renta.domain.statement import AccountStatement
from tests.conftest import account_row, write_account_xlsx

ISIN = "ES0000000001"


def dividend_row(amount: str, *, day: str = "10-06-2026") -> list[object]:
    """
    Build the gross dividend row of a payment.
    """

    return account_row(
        "Dividendo",
        currency="EUR",
        amount=amount,
        isin=ISIN,
        date_str=day,
        time="08:00",
    )


def withholding_row(amount: str, *, day: str = "10-06-2026") -> list[object]:
    """
    Build a withholding row, or the refund of one when positive.
    """

    return account_row(
        "Retención del dividendo",
        currency="EUR",
        amount=amount,
        isin=ISIN,
        date_str=day,
        time="08:00",
    )


def parse(tmp_path: Path, rows: list[list[object]]) -> AccountStatement:
    """
    Write the rows to a statement and parse it.
    """

    return parse_account_xlsx(write_account_xlsx(tmp_path / "Account.xlsx", rows))


def test_a_refund_in_the_same_payment_reduces_the_withholding(
    tmp_path: Path,
) -> None:
    """
    A positive withholding row gives back part of what was withheld.

    Adding it by absolute value would withhold 24 where 14 was kept.
    """

    statement = parse(
        tmp_path, [dividend_row("100"), withholding_row("-19"), withholding_row("5")]
    )

    assert statement.dividends[0].gross_eur == Decimal("100")
    assert statement.dividends[0].withholding_eur == Decimal("14")


def test_a_refund_on_another_day_is_warned_about(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """
    A refund posted apart from its dividend is named, not dropped.
    """

    rows = [
        dividend_row("100"),
        withholding_row("-19"),
        withholding_row("5", day="20-06-2026"),
    ]

    with caplog.at_level(logging.WARNING):
        statement = parse(tmp_path, rows)

    assert statement.dividends[0].withholding_eur == Decimal("19")
    assert "sin dividendo que la acompañe" in caplog.text
    assert "20-06-2026" in caplog.text


def test_a_withholding_with_no_dividend_is_warned_about(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """
    A withholding that no payment takes in is never silently lost.
    """

    with caplog.at_level(logging.WARNING):
        statement = parse(tmp_path, [withholding_row("-19")])

    assert statement.dividends == []
    assert "sin dividendo que la acompañe" in caplog.text


def test_a_withholding_in_another_currency_is_warned_about(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """
    A withholding in a currency other than the dividend's is not used.
    """

    rows = [
        dividend_row("100"),
        account_row(
            "Retención del dividendo",
            currency="USD",
            amount="-19",
            isin=ISIN,
            date_str="10-06-2026",
            time="08:00",
        ),
    ]

    with caplog.at_level(logging.WARNING):
        statement = parse(tmp_path, rows)

    assert statement.dividends[0].withholding_eur == Decimal("0")
    assert "sin dividendo que la acompañe" in caplog.text


def test_a_dividend_with_its_withholding_raises_no_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """
    The usual payment, withholding included, is not noise.
    """

    with caplog.at_level(logging.WARNING):
        parse(tmp_path, [dividend_row("100"), withholding_row("-19")])

    assert "sin dividendo que la acompañe" not in caplog.text


def test_operations_with_no_order_number_are_warned_about(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """
    An ISIN change booked as a sale and a purchase is flagged.

    Degiro gives those rows no order number and they are usually not a
    transmission, so taking them for one must not go unnoticed.
    """

    rows = [
        account_row(
            "Compra 10 Old Co@10 EUR (IE0000000001)",
            currency="EUR",
            amount="-100",
            isin="IE0000000001",
            order_id="ORD-1",
            date_str="05-01-2026",
        ),
        account_row(
            "Venta 10 Old Co@12 EUR (IE0000000001)",
            currency="EUR",
            amount="120",
            isin="IE0000000001",
            date_str="01-03-2026",
        ),
        account_row(
            "Compra 10 New Co@12 EUR (IE0000000002)",
            currency="EUR",
            amount="-120",
            isin="IE0000000002",
            date_str="01-03-2026",
        ),
    ]

    with caplog.at_level(logging.WARNING):
        parse(tmp_path, rows)

    assert "2 operación(es) sin número de orden" in caplog.text
    assert "IE0000000001" in caplog.text
    assert "IE0000000002" in caplog.text
    assert "01-03-2026" in caplog.text


def test_operations_with_an_order_number_raise_no_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """
    A normal trade carries its order number and is left alone.
    """

    rows = [
        account_row(
            "Compra 10 Foo@10 EUR (ES0000000001)",
            currency="EUR",
            amount="-100",
            isin=ISIN,
            order_id="ORD-1",
        )
    ]

    with caplog.at_level(logging.WARNING):
        statement = parse(tmp_path, rows)

    assert len(statement.operations) == 1
    assert "sin número de orden" not in caplog.text
