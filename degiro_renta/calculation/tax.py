# Standard libraries
from decimal import Decimal
from typing import Final

# Own modules
from degiro_renta.domain.money import ZERO, to_cents
from degiro_renta.domain.savings import TaxBracket

# Upper bound of each bracket, ``None`` for the last one, and its rate.
type SavingsScale = tuple[tuple[Decimal | None, Decimal], ...]

# Savings scale in force since 2025 (Ley 7/2024): the state scale plus
# the autonomic one, both fixed by state law (arts. 66 and 76 LIRPF) for
# every region of the common regime. The personal and family minimum
# (art. 56) is not applied, so the quota is an estimate.
SAVINGS_SCALE: Final[SavingsScale] = (
    (Decimal("6000"), Decimal("0.19")),
    (Decimal("50000"), Decimal("0.21")),
    (Decimal("200000"), Decimal("0.23")),
    (Decimal("300000"), Decimal("0.27")),
    (None, Decimal("0.30")),
)


def calculate_irpf_quota(savings_base: Decimal) -> list[TaxBracket]:
    """
    Break down the IRPF quota by savings-base brackets.

    The base must already integrate every savings-base item (dividends
    and other ``rendimientos del capital mobiliario`` plus capital
    gains), since arts. 66 and 76 LIRPF apply the progressive scale to their
    total rather than to each item separately.

    Args:
        savings_base: Total positive savings base in EUR.

    Returns:
        List of applied brackets with base and quota. Empty if
        ``savings_base <= 0``.
    """

    if savings_base <= 0:
        return []

    breakdown: list[TaxBracket] = []
    lower = ZERO
    remaining = savings_base

    for upper, rate in SAVINGS_SCALE:
        width = (upper - lower) if upper is not None else remaining
        bracket_base = min(remaining, width)

        if bracket_base <= 0:
            break

        breakdown.append(
            TaxBracket(
                lower=to_cents(lower),
                upper=to_cents(upper) if upper is not None else None,
                rate=rate,
                base=to_cents(bracket_base),
                quota=to_cents(bracket_base * rate),
            )
        )
        remaining -= bracket_base
        lower = upper if upper is not None else lower

        if remaining <= 0:
            break

    return breakdown


def total_quota(brackets: list[TaxBracket]) -> Decimal:
    """
    Add up the quota of every applied bracket.

    Args:
        brackets: Bracket breakdown over the savings base.

    Returns:
        Total estimated quota in EUR, zero when no bracket applies.
    """

    return sum((bracket.quota for bracket in brackets), ZERO)
