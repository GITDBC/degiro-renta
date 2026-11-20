# Standard libraries
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

# Own modules
from degiro_renta.domain.money import ZERO


class BalanceKind(StrEnum):
    """
    Balance of the savings base a negative amount belongs to.

    Art. 49 LIRPF integrates two balances separately and carries each
    one's negative remainder forward on its own.
    """

    GAINS = "ganancias y pérdidas patrimoniales"
    CAPITAL_INCOME = "rendimientos del capital mobiliario"


@dataclass(frozen=True)
class TaxBracket:
    """
    Savings-base bracket (arts. 66 and 76 LIRPF) with its base and quota.

    Attributes:
        lower: Lower bound of the bracket in EUR.
        upper: Upper bound of the bracket in EUR, or ``None`` if last.
        rate: Applied tax rate (e.g. ``0.19``).
        base: Taxable base covered by this bracket in EUR.
        quota: Resulting quota (``base * rate``) in EUR.
    """

    lower: Decimal
    upper: Decimal | None
    rate: Decimal
    base: Decimal
    quota: Decimal


@dataclass(frozen=True)
class SavingsBase:
    """
    Savings-base integration of capital income and capital gains.

    Art. 49 LIRPF integrates two balances separately: capital gains and
    losses, and ``rendimientos del capital mobiliario`` (dividends,
    interest and the results of financial assets of art. 25.2). The
    negative balance of each one offsets the positive balance of the
    other up to 25% of it, and the remainder carries forward four years.
    Pending negatives of earlier years offset first their own balance and
    then the other one, within the same 25% limit shared with the
    current year's offset.

    Attributes:
        capital_gains: Balance of capital gains and losses of the year.
        dividend_income: Gross dividend income in EUR.
        offset_applied: Capital-gains loss of the year offset against
            capital income.
        carryforward_losses: Capital-gains loss of the year left to
            carry to future years.
        total: Resulting taxable savings base in EUR.
        interest_income: Credit interest collected in EUR.
        debt_income: Result of transmitting financial assets of art.
            25.2 LIRPF, signed, in EUR.
        capital_income_offset: Negative capital income of the year
            offset against capital gains.
        capital_income_carryforward: Negative capital income of the year
            left to carry to future years.
        prior_gains_losses_applied: Capital-gains losses of earlier years
            offset this year.
        prior_capital_income_applied: Negative capital income of earlier
            years offset this year.
    """

    capital_gains: Decimal
    dividend_income: Decimal
    offset_applied: Decimal
    carryforward_losses: Decimal
    total: Decimal
    interest_income: Decimal = ZERO
    debt_income: Decimal = ZERO
    capital_income_offset: Decimal = ZERO
    capital_income_carryforward: Decimal = ZERO
    prior_gains_losses_applied: Decimal = ZERO
    prior_capital_income_applied: Decimal = ZERO

    @property
    def capital_income(self) -> Decimal:
        """
        Balance of ``rendimientos del capital mobiliario`` of the year.

        Returns:
            Gross dividends plus credit interest plus the result of the
            financial assets of art. 25.2, in EUR.
        """

        return self.dividend_income + self.interest_income + self.debt_income


@dataclass(frozen=True)
class LossCarryforward:
    """
    Negative balance still waiting to be offset in later exercises.

    Attributes:
        origin_year: Exercise in which the negative balance arose.
        amount_eur: Amount left to offset, positive, in EUR.
        expires_after: Last exercise in which it may still be offset
            (art. 49 LIRPF: the four years that follow).
        kind: Balance the amount belongs to.
    """

    origin_year: int
    amount_eur: Decimal
    expires_after: int
    kind: BalanceKind = BalanceKind.GAINS
