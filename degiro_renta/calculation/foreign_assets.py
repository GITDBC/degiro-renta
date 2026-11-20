# Standard libraries
from datetime import date, timedelta
from decimal import Decimal

# Own modules
from degiro_renta.calculation.fifo import calculate_fifo
from degiro_renta.domain.foreign_assets import ForeignAssets
from degiro_renta.domain.money import ZERO
from degiro_renta.domain.statement import AccountStatement


def balance_on(entries: tuple[tuple[date, Decimal], ...], day: date) -> Decimal:
    """
    Cash balance at the end of a day.

    Among the rows of the latest date on or before ``day``, the first one
    in the statement stands for the end of that day, since the export
    lists the newest row first.

    Args:
        entries: Balances after each row, dated, in statement order.
        day: Day to look the balance up.

    Returns:
        The balance at the end of the latest day with a row on or before
        ``day``, zero when the statement has none that early.
    """

    latest: date | None = None
    balance = ZERO

    for entry_date, amount in entries:
        if entry_date <= day and (latest is None or entry_date > latest):
            latest = entry_date
            balance = amount

    return balance


def average_balance(
    entries: tuple[tuple[date, Decimal], ...], since: date, until: date
) -> Decimal:
    """
    Average of the daily cash balance over a range of days.

    Args:
        entries: Balances after each row, dated, in statement order.
        since: First day of the range.
        until: Last day of the range, included.

    Returns:
        The mean of the end-of-day balances of every day of the range.
    """

    days = (until - since).days + 1
    total = sum(
        (balance_on(entries, since + timedelta(days=offset)) for offset in range(days)),
        ZERO,
    )

    return total / days


def build_foreign_assets(statement: AccountStatement, year: int) -> ForeignAssets:
    """
    Gather what the account holds abroad when an exercise closes.

    The cost leaves out the ISINs the statement could not value in euros,
    which are not in its operations either.

    Args:
        statement: Parsed Degiro account statement.
        year: Exercise to look at.

    Returns:
        The cost of the open positions, the cash balance and its
        average over the last quarter, all on 31 December or on the
        last day the statement covers when that comes first.
    """

    year_end = date(year, 12, 31)
    as_of = (
        year_end if statement.last_date is None else min(year_end, statement.last_date)
    )

    _, lots = calculate_fifo(
        [operation for operation in statement.operations if operation.date <= as_of]
    )
    cost = sum(
        (lot.quantity * lot.unit_cost for queue in lots.values() for lot in queue),
        ZERO,
    )

    quarter_start = date(year, 10, 1)
    average = (
        average_balance(statement.cash_balances, quarter_start, as_of)
        if as_of >= quarter_start
        else None
    )

    return ForeignAssets(
        as_of=as_of,
        securities_cost=cost,
        cash_balance=balance_on(statement.cash_balances, as_of),
        cash_average=average,
    )
