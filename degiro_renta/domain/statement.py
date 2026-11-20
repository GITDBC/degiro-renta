# Standard libraries
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

# Own modules
from degiro_renta.domain.currency import CurrencyConversion
from degiro_renta.domain.income import DividendIncome, OtherIncome
from degiro_renta.domain.operations import Operation, UnvaluedOperation


class StatementRowKind(StrEnum):
    """
    What a row of the Degiro account statement represents.

    Every row is classified into one of these, so a description the
    parser does not recognize lands in ``UNKNOWN`` and is reported
    instead of dropped in silence. A statement exported in another
    language, or a movement type Degiro adds later, then shows up as a
    warning rather than as a report that quietly declares less.
    """

    OPERATION = "operation"
    FEE = "fee"
    CONNECTIVITY_FEE = "connectivity_fee"
    CURRENCY_EXCHANGE = "currency_exchange"
    DIVIDEND = "dividend"
    DIVIDEND_WITHHOLDING = "dividend_withholding"
    INTEREST = "interest"
    OTHER_INCOME = "other_income"
    FEE_REFUND = "fee_refund"
    CASH_MOVEMENT = "cash_movement"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class UnclassifiedRow:
    """
    Statement row whose description the parser does not recognize.

    Attributes:
        date: Row date as written in the statement.
        description: Statement description, verbatim.
        amount: Signed amount as read.
        currency: Currency code of that amount, empty when absent.
    """

    date: str
    description: str
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class AccountStatement:
    """
    Everything the fiscal report needs from a Degiro account export.

    Attributes:
        operations: Normalized buy/sell operations, chronologically
            sorted. Excludes every ISIN that could not be valued in
            euros, so a FIFO chain is never built on a partial history.
        dividends: Dividends collected, with their withholdings.
        other_income: Promotions, rebates and refunds credited.
        currency_conversions: Currency exchanges that pair with no
            trade.
        unvalued_operations: Trades with no euro consideration in the
            statement, whose ISIN was left out of ``operations``.
        unclassified_rows: Rows whose description the parser does not
            recognize.
        connectivity_entries: Market connectivity fees, as pairs of date
            and positive amount in EUR.
        interest_entries: Interest on the cash balance, as pairs of date
            and signed amount in EUR (credit positive, debit negative).
        cash_balances: Balance in EUR the account shows after each row
            that states one, as pairs of date and amount, in the order
            of the statement, which lists the newest row first. The rows
            of a cash sweep are left out.
        last_date: Date of the most recent row of the statement, which
            is as far as it can tell whether a purchase happened.
            ``None`` when the statement has no rows.
    """

    operations: list[Operation]
    dividends: list[DividendIncome]
    other_income: tuple[OtherIncome, ...] = ()
    currency_conversions: tuple[CurrencyConversion, ...] = ()
    unvalued_operations: tuple[UnvaluedOperation, ...] = ()
    unclassified_rows: tuple[UnclassifiedRow, ...] = ()
    connectivity_entries: tuple[tuple[date, Decimal], ...] = ()
    interest_entries: tuple[tuple[date, Decimal], ...] = ()
    cash_balances: tuple[tuple[date, Decimal], ...] = ()
    last_date: date | None = None
