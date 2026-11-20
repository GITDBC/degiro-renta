# Standard libraries
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ForeignAssets:
    """
    What the Degiro account holds abroad on the date the exercise closes.

    It is the information the modelo 720 asks for as far as the
    statement can tell: the statement carries what the positions cost
    and the cash balance, not what the positions are worth on 31
    December.

    Attributes:
        as_of: 31 December of the exercise, or the date of the last row
            of the statement when it ends earlier.
        securities_cost: Cost of the positions still open on ``as_of``,
            matched by FIFO.
        cash_balance: Cash balance in EUR on ``as_of``.
        cash_average: Average daily cash balance in EUR from 1 October
            to ``as_of``, or ``None`` when ``as_of`` is before 1
            October.
    """

    as_of: date
    securities_cost: Decimal
    cash_balance: Decimal
    cash_average: Decimal | None
