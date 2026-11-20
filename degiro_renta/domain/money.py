# Standard libraries
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

# Currency every fiscal figure of the report is expressed in.
EUR: Final[str] = "EUR"

ZERO: Final[Decimal] = Decimal(0)

CENT: Final[Decimal] = Decimal("0.01")


def to_cents(value: Decimal) -> Decimal:
    """
    Round an amount to the cent, half up.

    Args:
        value: Amount to round.

    Returns:
        The amount with two decimals.
    """

    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def percentage_of(part: Decimal, whole: Decimal) -> Decimal | None:
    """
    Express an amount as a percentage of another, to two decimals.

    Args:
        part: Amount to express.
        whole: Amount it is measured against.

    Returns:
        The percentage rounded half up, or ``None`` when ``whole`` is
        zero and there is nothing to measure against.
    """

    if whole == 0:
        return None

    return to_cents(part / whole * 100)
