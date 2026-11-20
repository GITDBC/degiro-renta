# Standard libraries
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

# 3pps
import pytest

# Own modules
from degiro_renta import (
    build_report_data,
    calculate_fifo,
    parse_account_xlsx,
    print_report,
)
from degiro_renta.calculation.foreign_assets import (
    average_balance,
    balance_on,
    build_foreign_assets,
)
from degiro_renta.domain.foreign_assets import ForeignAssets
from degiro_renta.domain.operations import Operation, OperationType
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.foreign_assets import (
    MODEL_720_CATEGORY,
    foreign_assets_notices,
)
from tests.conftest import account_row, make_console, make_statement, write_account_xlsx

ISIN = "IE0000000001"


def buy(day: date, amount: str, quantity: int = 10) -> Operation:
    """
    Build a purchase with no fees.
    """

    return Operation(
        date=day,
        time="10:00",
        isin=ISIN,
        product="TEST",
        operation_type=OperationType.BUY,
        quantity=quantity,
        amount_eur=Decimal(f"-{amount}"),
        fee_eur=Decimal(0),
    )


def sell(day: date, amount: str, quantity: int) -> Operation:
    """
    Build a sale with no fees.
    """

    return replace(
        buy(day, "0", quantity),
        operation_type=OperationType.SELL,
        amount_eur=Decimal(amount),
    )


def with_balances(
    operations: list[Operation],
    balances: tuple[tuple[date, Decimal], ...],
    last_date: date,
) -> ReportData:
    """
    Build the 2026 report of a statement with these operations and balances.
    """

    statement = replace(
        make_statement(operations=operations),
        cash_balances=balances,
        last_date=last_date,
    )
    sales, _ = calculate_fifo(statement.operations)

    return build_report_data(sales, statement, year=2026)


def assets(cost: str, cash: str, average: str | None = None) -> ForeignAssets:
    """
    Build the assets of a statement that ends on 31 December 2026.
    """

    return ForeignAssets(
        as_of=date(2026, 12, 31),
        securities_cost=Decimal(cost),
        cash_balance=Decimal(cash),
        cash_average=None if average is None else Decimal(average),
    )


def notices_for(held: ForeignAssets | None) -> list[str]:
    """
    Messages the report raises for the assets.
    """

    data = replace(
        build_report_data([], make_statement()), foreign_assets=held, year=2026
    )

    return [item.message for item in foreign_assets_notices(data)]


def test_balance_is_the_one_of_the_latest_day_with_a_row() -> None:
    """
    The balance of a day is that of the newest row on or before it.
    """

    entries = (
        (date(2026, 3, 2), Decimal(300)),
        (date(2026, 3, 2), Decimal(200)),
        (date(2026, 3, 1), Decimal(100)),
    )

    assert balance_on(entries, date(2026, 3, 2)) == Decimal(300)
    assert balance_on(entries, date(2026, 3, 15)) == Decimal(300)
    assert balance_on(entries, date(2026, 3, 1)) == Decimal(100)
    assert balance_on(entries, date(2026, 2, 28)) == Decimal(0)


def test_balance_does_not_depend_on_the_order_of_the_days() -> None:
    """
    A statement listed oldest first gives the same balance.
    """

    entries = ((date(2026, 3, 1), Decimal(100)), (date(2026, 3, 2), Decimal(300)))

    assert balance_on(entries, date(2026, 3, 5)) == Decimal(300)


def test_average_balance_weights_every_day() -> None:
    """
    Four days, two at 100 and two at 300, average 200.
    """

    entries = ((date(2026, 10, 3), Decimal(300)), (date(2026, 10, 1), Decimal(100)))

    assert average_balance(entries, date(2026, 10, 1), date(2026, 10, 4)) == Decimal(
        200
    )


def test_cost_counts_only_what_is_still_open_at_year_end() -> None:
    """
    A sale consumes the oldest lot, and a purchase of the next year is out.
    """

    operations = [
        buy(date(2026, 1, 5), "1000"),
        buy(date(2026, 2, 5), "3000"),
        sell(date(2026, 3, 5), "1200", 10),
        buy(date(2027, 1, 5), "9000"),
    ]
    statement = replace(
        make_statement(operations=operations), last_date=date(2027, 1, 5)
    )

    held = build_foreign_assets(statement, 2026)

    assert held.as_of == date(2026, 12, 31)
    assert held.securities_cost == Decimal(3000)


def test_a_statement_that_ends_earlier_is_measured_on_its_last_day() -> None:
    """
    The date of reference is the last row when it comes before 31 December.
    """

    statement = replace(
        make_statement(operations=[buy(date(2026, 1, 5), "1000")]),
        last_date=date(2026, 11, 13),
    )

    held = build_foreign_assets(statement, 2026)

    assert held.as_of == date(2026, 11, 13)


def test_no_average_when_the_statement_ends_before_the_last_quarter() -> None:
    """
    There is no quarter to average before 1 October.
    """

    statement = replace(
        make_statement(operations=[buy(date(2026, 1, 5), "1000")]),
        last_date=date(2026, 6, 30),
    )

    assert build_foreign_assets(statement, 2026).cash_average is None


def test_report_carries_cost_balance_and_average() -> None:
    """
    The report holds what the account has abroad.
    """

    report = with_balances(
        [buy(date(2026, 1, 5), "1000")],
        ((date(2026, 12, 20), Decimal(400)), (date(2026, 10, 1), Decimal(100))),
        date(2026, 12, 31),
    )

    held = report.foreign_assets
    assert held is not None
    assert held.securities_cost == Decimal(1000)
    assert held.cash_balance == Decimal(400)
    # 80 days at 100 and 12 at 400, out of 92.
    assert held.cash_average is not None
    assert round(held.cash_average, 2) == Decimal("139.13")


def test_nothing_is_said_far_below_the_limit() -> None:
    """
    Cost and cash under half the limit raise no note.
    """

    assert notices_for(assets("24999.99", "24999.99", "24999.99")) == []


def test_nothing_is_said_without_assets() -> None:
    """
    A report with no exercise has nothing to note.
    """

    assert notices_for(None) == []


def test_securities_near_the_limit_are_noted_in_yellow() -> None:
    """
    Half the limit reaches the note, which is not yet severe.
    """

    data = replace(
        build_report_data([], make_statement()),
        foreign_assets=assets("30000", "0"),
        year=2026,
    )

    (notice,) = foreign_assets_notices(data)

    assert notice.category == MODEL_720_CATEGORY
    assert not notice.severe
    assert "30000.00" in notice.message
    assert "1 de enero al 31 de marzo de 2027" in notice.message


@pytest.mark.parametrize(("cost", "severe"), [("50000", False), ("50000.01", True)])
def test_only_what_exceeds_the_limit_is_severe(cost: str, severe: bool) -> None:
    """
    The obligation is to exceed the limit, so reaching it stays yellow.
    """

    data = replace(
        build_report_data([], make_statement()),
        foreign_assets=assets(cost, "0"),
        year=2026,
    )

    (notice,) = foreign_assets_notices(data)

    assert notice.severe is severe


def test_cash_is_judged_by_the_higher_of_balance_and_average() -> None:
    """
    A low closing balance does not hide a high average of the quarter.
    """

    messages = notices_for(assets("0", "100", "60000"))

    assert len(messages) == 1
    assert messages[0].startswith("Cuenta:")
    assert "60000.00" in messages[0]


def test_each_block_is_noted_on_its_own() -> None:
    """
    Securities and cash are separate blocks, each with its own note.
    """

    messages = notices_for(assets("30000", "30000", "30000"))

    assert [message.split(":")[0] for message in messages] == [
        "Valores e IIC",
        "Cuenta",
    ]


def test_the_real_report_prints_the_heading(tmp_path: Path) -> None:
    """
    A statement over half the limit prints the note under its heading.
    """

    rows = [
        account_row(
            "Compra 1 TEST@40000 EUR (ES0000000001)",
            currency="EUR",
            amount="-40000",
            isin="ES0000000001",
            order_id="A1",
            date_str="05-01-2026",
        ),
    ]
    statement = parse_account_xlsx(write_account_xlsx(tmp_path / "Account.xlsx", rows))
    sales, _ = calculate_fifo(statement.operations)
    data = build_report_data(sales, statement, year=2026)

    console, buffer = make_console()
    print_report(data, console=console)

    assert "Modelo 720" in buffer.getvalue()


def balance_row(
    description: str, balance: str, day: str, *, currency: str = "EUR"
) -> list[object]:
    """
    Build a row with no instrument that states a balance.
    """

    row = account_row(description, currency=currency, amount="0", date_str=day)
    row[4] = None
    row[9] = currency
    row[10] = balance

    return row


def test_foreign_currency_balances_are_not_the_cash(tmp_path: Path) -> None:
    """
    Only the balances stated in EUR are read.
    """

    rows = [
        balance_row("flatex Deposit", "888", "02-02-2026", currency="USD"),
        balance_row("flatex Deposit", "500", "01-02-2026"),
    ]

    statement = parse_account_xlsx(write_account_xlsx(tmp_path / "Account.xlsx", rows))

    assert statement.cash_balances == ((date(2026, 2, 1), Decimal(500)),)


@pytest.mark.parametrize(
    ("sweep_balance", "mirror_balance"), [("1100", "500"), ("500", "-100")]
)
def test_neither_row_of_a_sweep_gives_the_cash(
    tmp_path: Path, sweep_balance: str, mirror_balance: str
) -> None:
    """
    Either row of the pair can carry the passing balance, so both are left out.

    The statement shows both layouts: the sweep row inflated and its
    mirror back to the cash, or the mirror below zero and the sweep back.
    """

    rows = [
        balance_row(
            "Transferir desde su Cuenta de Efectivo en flatexDEGIRO Bank: 600 EUR",
            mirror_balance,
            "03-02-2026",
        ),
        balance_row("Degiro Cash Sweep Transfer", sweep_balance, "03-02-2026"),
        balance_row("flatex Deposit", "500", "01-02-2026"),
    ]

    statement = parse_account_xlsx(write_account_xlsx(tmp_path / "Account.xlsx", rows))

    assert statement.cash_balances == ((date(2026, 2, 1), Decimal(500)),)
