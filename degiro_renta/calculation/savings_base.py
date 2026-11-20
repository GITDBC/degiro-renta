# Standard libraries
from dataclasses import replace
from decimal import Decimal
from typing import Final

# Own modules
from degiro_renta.domain.money import ZERO, to_cents
from degiro_renta.domain.savings import BalanceKind, LossCarryforward, SavingsBase

# Share of the positive balance of one block of the savings base that
# the negative balance of the other block may offset (art. 49 LIRPF).
OFFSET_LIMIT_RATE: Final[Decimal] = Decimal("0.25")

# Exercises that follow the one in which a negative balance arose and in
# which it may still be offset (art. 49 LIRPF).
CARRYFORWARD_YEARS: Final[int] = 4


def _quarter(balance: Decimal) -> Decimal:
    """
    The 25% of a positive balance that the other block may offset.

    Args:
        balance: Balance of one block of the savings base.

    Returns:
        A quarter of the balance rounded to the cent, zero when the
        balance is not positive.
    """

    return to_cents(max(balance, ZERO) * OFFSET_LIMIT_RATE)


def _consume(
    pending: list[LossCarryforward], available: Decimal
) -> tuple[Decimal, list[LossCarryforward]]:
    """
    Offset pending negative balances, oldest first, up to an amount.

    Args:
        pending: Negative balances of earlier years, oldest first.
        available: Most that may be offset.

    Returns:
        The amount offset and the balances still pending afterwards.
    """

    used = ZERO
    left: list[LossCarryforward] = []

    for entry in pending:
        take = min(entry.amount_eur, max(available - used, ZERO))
        used += take

        if entry.amount_eur > take:
            left.append(replace(entry, amount_eur=entry.amount_eur - take))

    return used, left


def integrate_savings_base(  # noqa: PLR0913 - the inputs art. 49 integrates
    year: int,
    capital_gains: Decimal,
    dividend_income: Decimal,
    *,
    interest_income: Decimal = ZERO,
    debt_income: Decimal = ZERO,
    pending: tuple[LossCarryforward, ...] = (),
) -> tuple[SavingsBase, tuple[LossCarryforward, ...]]:
    """
    Integrate one exercise into the savings base (art. 49 LIRPF).

    Follows the two phases of the Manual práctico de Renta 2025
    (chapter 12). First the balances of the year: capital gains and
    losses on one side and capital income on the other, the negative
    one offsetting the positive one up to 25% of it. Then the negative
    balances of the four previous years: each one offsets the positive
    balance left in its own block, and what remains offsets the other
    block within the same 25%, shared with the year's own offset and
    measured over that block's balance before any offset.

    Args:
        year: Exercise being integrated.
        capital_gains: Balance of capital gains and losses of the year.
        dividend_income: Gross dividends of the year.
        interest_income: Credit interest of the year.
        debt_income: Signed result of the financial assets of art. 25.2
            transmitted in the year.
        pending: Negative balances of earlier years still pending.

    Returns:
        The savings base of the year and the negative balances pending
        after it, the year's own remainder included.
    """

    capital_income = dividend_income + interest_income + debt_income
    limit_on_income = _quarter(capital_income)
    limit_on_gains = _quarter(capital_gains)

    gains_left = capital_gains
    income_left = capital_income
    gains_offset = ZERO
    income_offset = ZERO

    if capital_gains < 0 < capital_income:
        gains_offset = min(-capital_gains, limit_on_income)
        income_left -= gains_offset
        gains_left += gains_offset
    elif capital_income < 0 < capital_gains:
        income_offset = min(-capital_income, limit_on_gains)
        gains_left -= income_offset
        income_left += income_offset

    alive = [entry for entry in pending if year <= entry.expires_after]
    prior_gains = [e for e in alive if e.kind is BalanceKind.GAINS]
    prior_income = [e for e in alive if e.kind is BalanceKind.CAPITAL_INCOME]

    gains_own, prior_gains = _consume(prior_gains, max(gains_left, ZERO))
    gains_left -= gains_own
    income_own, prior_income = _consume(prior_income, max(income_left, ZERO))
    income_left -= income_own

    income_cross, prior_income = _consume(
        prior_income,
        min(max(gains_left, ZERO), limit_on_gains - income_offset),
    )
    gains_left -= income_cross
    gains_cross, prior_gains = _consume(
        prior_gains,
        min(max(income_left, ZERO), limit_on_income - gains_offset),
    )
    income_left -= gains_cross

    new: list[LossCarryforward] = []
    expires_after = year + CARRYFORWARD_YEARS

    if gains_left < 0:
        new.append(
            LossCarryforward(year, -gains_left, expires_after, BalanceKind.GAINS)
        )
    if income_left < 0:
        new.append(
            LossCarryforward(
                year, -income_left, expires_after, BalanceKind.CAPITAL_INCOME
            )
        )

    savings = SavingsBase(
        capital_gains=capital_gains,
        dividend_income=dividend_income,
        offset_applied=gains_offset,
        carryforward_losses=max(-gains_left, ZERO),
        total=max(gains_left, ZERO) + max(income_left, ZERO),
        interest_income=interest_income,
        debt_income=debt_income,
        capital_income_offset=income_offset,
        capital_income_carryforward=max(-income_left, ZERO),
        prior_gains_losses_applied=gains_own + gains_cross,
        prior_capital_income_applied=income_own + income_cross,
    )

    remaining = tuple(
        sorted((*prior_gains, *prior_income, *new), key=lambda e: e.origin_year)
    )

    return savings, remaining
