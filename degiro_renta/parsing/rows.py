# Standard libraries
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final, TypedDict

# 3pps
import polars as pl

# Own modules
from degiro_renta.domain.income import OtherIncome
from degiro_renta.domain.money import EUR
from degiro_renta.domain.statement import (
    StatementRowKind,
    UnclassifiedRow,
)
from degiro_renta.parsing.columns import (
    BALANCE_COL,
    BALANCE_CURRENCY_COL,
    CURRENCY_COL,
    DATE_COL,
    DESCRIPTION_COL,
    ISIN_COL,
    ORDER_ID_COL,
    PRODUCT_COL,
    TIME_COL,
    VARIATION_COL,
)
from degiro_renta.parsing.descriptions import classify_description, is_sweep_row
from degiro_renta.parsing.values import amount_to_decimal, parse_date

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Worksheet holding the Degiro account statement inside Account.xlsx.
ACCOUNT_SHEET_NAME: Final[str] = "Estado de cuenta"

# Largest column index accessed unconditionally while reading a data row.
# Rows shorter than this are truncated/malformed and are skipped.
MIN_ROW_LEN: Final[int] = VARIATION_COL + 1

# Key of the rows that belong together: the order ID, or ``(date, time,
# ISIN)`` for the rows Degiro gives no order ID, such as dividends.
type GroupKey = str | tuple[str, str, str]


class AccountRow(TypedDict):
    """
    Normalized account-statement row with an exact Decimal amount.

    Attributes:
        date: Operation date in ``dd-mm-yyyy`` format.
        time: Time in ``HH:MM`` format.
        isin: ISIN identifier of the instrument, empty when absent.
        product: Product name, empty when absent.
        description: Operation description.
        variation: Exact variation amount in its own currency (sign
            included).
        currency: Variation currency code, empty when absent.
    """

    date: str
    time: str
    isin: str
    product: str
    description: str
    variation: Decimal
    currency: str


@dataclass
class StatementRows:
    """
    Every row of the statement, sorted into what it means fiscally.

    Attributes:
        groups: Rows that belong to an operation or a payment, keyed by
            order ID or by ``(date, time, ISIN)``.
        other_income: Promotions, rebates and refunds credited.
        loose_exchanges: Currency exchange rows tied to no instrument.
        unclassified: Rows the parser could neither recognize nor
            attribute.
        connectivity_entries: Market connectivity fees, dated, as
            positive amounts.
        interest_entries: Interest on the cash balance, dated, signed.
        fee_refunds: Refunds of transaction costs credited, as the date,
            the amount and the description verbatim.
        cash_balances: Balance in EUR the account shows after each row
            that states one, dated and in the order of the statement,
            leaving out the rows of a cash sweep.
        last_date: Date of the most recent row of the statement, or
            ``None`` when it has none.
    """

    groups: dict[GroupKey, list[AccountRow]] = field(
        default_factory=lambda: defaultdict(list)
    )
    other_income: list[OtherIncome] = field(default_factory=list)
    loose_exchanges: list[AccountRow] = field(default_factory=list)
    unclassified: list[UnclassifiedRow] = field(default_factory=list)
    connectivity_entries: list[tuple[date, Decimal]] = field(default_factory=list)
    interest_entries: list[tuple[date, Decimal]] = field(default_factory=list)
    fee_refunds: list[tuple[date, Decimal, str]] = field(default_factory=list)
    cash_balances: list[tuple[date, Decimal]] = field(default_factory=list)
    last_date: date | None = None


def order_group_key(row: list[str]) -> GroupKey | None:
    """
    Return the grouping key of the row or ``None`` if it has none.

    Uses the Order ID when present; otherwise groups by
    ``(date, time, ISIN)``.

    Args:
        row: Raw account-statement row as a list of strings.

    Returns:
        Grouping key (Order ID or tuple) or ``None`` when the row is
        tied to no instrument.
    """

    order_id = row[ORDER_ID_COL] if len(row) > ORDER_ID_COL else ""
    if order_id:
        return order_id

    isin = row[ISIN_COL]
    if isin:
        return (row[DATE_COL], row[TIME_COL], isin)

    return None


def is_continuation_row(row: list[str]) -> bool:
    """
    Report whether a row is the tail of a wrapped description.

    Degiro splits long descriptions across two spreadsheet rows: the
    second one carries only the remaining text and leaves every other
    column empty. Such a row is not an operation by itself and its text
    must be appended to the preceding row.

    Args:
        row: Raw account-statement row as a list of strings.

    Returns:
        True if the row only carries description text.
    """

    if len(row) <= DESCRIPTION_COL or not row[DESCRIPTION_COL]:
        return False

    return not any(
        row[col] for col in (DATE_COL, TIME_COL, ISIN_COL) if col < len(row)
    ) and not (len(row) > VARIATION_COL and row[VARIATION_COL])


def merge_continuation_rows(rows: list[list[str]]) -> list[list[str]]:
    """
    Join descriptions that Degiro wrapped onto a following row.

    Without this step a wrapped description loses the ``@price``
    fragment, ``OPERATION_REGEX`` stops matching and the whole
    operation disappears from the fiscal report.

    Args:
        rows: Raw account-statement rows as lists of strings.

    Returns:
        New list of rows where every continuation row has been folded
        into the operation row above it.
    """

    merged: list[list[str]] = []

    for row in rows:
        if merged and is_continuation_row(row):
            previous = merged[-1]
            tail = row[DESCRIPTION_COL].strip()
            previous[DESCRIPTION_COL] = f"{previous[DESCRIPTION_COL].rstrip()} {tail}"
            continue

        merged.append(list(row))

    return merged


def read_account_rows(path: Path) -> list[list[str]]:
    """
    Read the account-statement sheet as rows of plain strings.

    Reads the sheet with ``infer_schema_length=0`` so every cell is
    returned as text, preserving the full decimal precision of the
    amount columns. Empty cells are normalized to empty strings, the
    header row is excluded and descriptions wrapped onto a second row
    are folded back into their operation row.

    Args:
        path: Path to the Account.xlsx file exported from Degiro.

    Returns:
        List of rows, each a list of cell strings.
    """

    frame = pl.read_excel(
        path,
        sheet_name=ACCOUNT_SHEET_NAME,
        infer_schema_length=0,
    )

    rows = [
        ["" if cell is None else str(cell) for cell in row] for row in frame.iter_rows()
    ]

    return merge_continuation_rows(rows)


def to_account_row(row: list[str], variation: Decimal) -> AccountRow:
    """
    Turn a raw cell list into a normalized row.

    Args:
        row: Raw account-statement row as a list of strings.
        variation: Amount already converted to Decimal.

    Returns:
        The normalized row.
    """

    return AccountRow(
        date=row[DATE_COL],
        time=row[TIME_COL],
        isin=row[ISIN_COL],
        product=row[PRODUCT_COL] if len(row) > PRODUCT_COL else "",
        description=row[DESCRIPTION_COL],
        variation=variation,
        currency=row[CURRENCY_COL],
    )


def collect_loose_row(
    entry: AccountRow, kind: StatementRowKind, into: StatementRows
) -> None:
    """
    File a row that belongs to no instrument by what it means.

    Args:
        entry: Normalized row tied to neither an order nor an ISIN.
        kind: Kind the description was classified as.
        into: Accumulator to add the row to.

    Returns:
        None.
    """

    if kind is StatementRowKind.CURRENCY_EXCHANGE:
        into.loose_exchanges.append(entry)
    elif kind is StatementRowKind.INTEREST:
        into.interest_entries.append((parse_date(entry["date"]), entry["variation"]))
    elif kind is StatementRowKind.FEE_REFUND:
        into.fee_refunds.append(
            (parse_date(entry["date"]), entry["variation"], entry["description"])
        )
    elif kind is StatementRowKind.OTHER_INCOME:
        into.other_income.append(
            OtherIncome(
                date=parse_date(entry["date"]),
                description=entry["description"],
                amount_eur=entry["variation"],
            )
        )
    elif kind is not StatementRowKind.CASH_MOVEMENT:
        # A fee or an unknown description with nothing to attach it to.
        # Reported rather than dropped: it is the only signal that the
        # statement carries something this parser does not model.
        into.unclassified.append(
            UnclassifiedRow(
                date=entry["date"],
                description=entry["description"],
                amount=entry["variation"],
                currency=entry["currency"],
            )
        )


def parse_account_row(row: list[str]) -> AccountRow | None:
    """
    Normalize a raw row, or skip it with a warning when it is malformed.

    Args:
        row: Raw account-statement row as a list of strings.

    Returns:
        The normalized row, or ``None`` when it is shorter than the
        columns read or its amount is not a number.
    """

    # Defensive guard: rows shorter than the columns we read are
    # malformed and would raise IndexError mid-parse.
    if len(row) < MIN_ROW_LEN:
        _LOGGER.warning(
            "Se omite una fila mal formada con %d columnas (se esperaban >= %d): %r.",
            len(row),
            MIN_ROW_LEN,
            row,
        )
        return None

    try:
        variation = amount_to_decimal(row[VARIATION_COL])

    except ValueError:
        _LOGGER.warning(
            "Se omite una fila con importe inválido %r: %r.",
            row[VARIATION_COL],
            row,
        )
        return None

    return to_account_row(row, variation)


def _latest_date(current: date | None, text: str) -> date | None:
    """
    Keep the most recent date seen so far.

    A row whose date cannot be read leaves it as it was: the rows that
    need their date raise on their own, and a cash movement does not.

    Args:
        current: Most recent date seen so far, if any.
        text: Date of the row being read, as written in the statement.

    Returns:
        The later of both dates.
    """

    try:
        day = parse_date(text)

    except ValueError:
        return current

    return day if current is None else max(day, current)


def euro_balance(row: list[str]) -> tuple[date, Decimal] | None:
    """
    Read the balance in EUR the account shows after a row.

    Args:
        row: Raw account-statement row as a list of strings.

    Returns:
        The date of the row and the balance, or ``None`` when the row
        states none, states it in another currency, or has a balance or
        a date that cannot be read. Such a row is not an error here: it
        only leaves the balance unknown on that day.
    """

    if len(row) <= BALANCE_COL or row[BALANCE_CURRENCY_COL] != EUR:
        return None

    try:
        return parse_date(row[DATE_COL]), Decimal(row[BALANCE_COL])

    except (ValueError, InvalidOperation):
        return None


def read_statement_rows(
    path: Path,
) -> StatementRows:
    """
    Read every row of the XLSX and sort it by what it means.

    Args:
        path: Path to the Account.xlsx file exported from Degiro.

    Returns:
        Rows grouped per operation plus every standalone concept found.
    """

    collected = StatementRows()

    for row in read_account_rows(path):
        entry = parse_account_row(row)
        if entry is None:
            continue

        kind = classify_description(entry["description"])

        collected.last_date = _latest_date(collected.last_date, entry["date"])

        balance = None if is_sweep_row(entry["description"]) else euro_balance(row)
        if balance is not None:
            collected.cash_balances.append(balance)

        if kind is StatementRowKind.CONNECTIVITY_FEE:
            collected.connectivity_entries.append(
                (parse_date(entry["date"]), abs(entry["variation"]))
            )
            continue

        key = order_group_key(row)
        if key is None:
            collect_loose_row(entry, kind, collected)
            continue

        if kind is StatementRowKind.UNKNOWN:
            # Being grouped is not being read: a group only yields
            # operations, fees, exchanges, dividends and withholdings.
            # An unknown description inside one is used by nothing, so
            # it is reported like any other.
            collected.unclassified.append(
                UnclassifiedRow(
                    date=entry["date"],
                    description=entry["description"],
                    amount=entry["variation"],
                    currency=entry["currency"],
                )
            )

        collected.groups[key].append(entry)

    return collected
