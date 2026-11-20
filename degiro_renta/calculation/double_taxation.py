# Standard libraries
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

# Own modules
from degiro_renta.domain.income import DividendIncome
from degiro_renta.domain.money import ZERO, to_cents

# Maximum withholding on ordinary portfolio dividends that the treaty
# allows the source country to keep, keyed by the ISIN country prefix.
# The US rate is the general 15% of the Spain-US treaty as amended in
# force since 27 November 2019, per the AEAT treaty table. Its
# exceptions (dividends between companies, exempt cases) are not
# modelled, and the cap applies to dividends only, not to any other US
# income.
VERIFIED_TREATY_CAPS: Final[dict[str, Decimal]] = {"US": Decimal("0.15")}

# Cap applied to a country missing from the table above: the usual rate
# on portfolio dividends of the Spanish treaties, not verified for the
# country in question, so the report names every country it was used
# for.
DEFAULT_TREATY_CAP: Final[Decimal] = Decimal("0.15")

# Percentage places the average effective rate is expressed with (manual
# 2025, chapter 18: "se expresará con dos decimales").
RATE_QUANTIZE: Final[Decimal] = Decimal("0.01")


@dataclass(frozen=True)
class ForeignCredit:
    """
    Double-taxation deduction for withholdings taken abroad (art. 80).

    Attributes:
        withheld: Foreign withholdings practised, in EUR.
        creditable: Part of them within the treaty cap, in EUR.
        deduction: Deduction applied to the quota, the lower of the
            creditable amount and the limit of art. 80.1.b, in EUR.
        excess: Withholding above the treaty cap, reclaimable at the
            source country, in EUR.
        unused_limit: Creditable amount that the limit of art. 80.1.b
            prevented from being deducted, in EUR.
        unverified_countries: Countries capped with the default rate.
    """

    withheld: Decimal
    creditable: Decimal
    deduction: Decimal
    excess: Decimal
    unused_limit: Decimal
    unverified_countries: tuple[str, ...]


def calculate_foreign_credit(
    dividends: list[DividendIncome], quota: Decimal, savings_total: Decimal
) -> ForeignCredit:
    """
    Compute the deduction for withholdings taken abroad.

    The limit of art. 80.1.b is the average effective rate of the
    savings base, expressed with two decimals, applied to the foreign
    dividends integrated in it (manual 2025, chapter 18). The part of the
    savings base taxed abroad cannot exceed the base itself. Each
    dividend contributes at most the treaty share of its gross amount.

    Args:
        dividends: Dividends collected in the exercise.
        quota: Quota of the savings base before the deduction, in EUR.
        savings_total: Savings base of the exercise, in EUR.

    Returns:
        The deduction and the amounts that did not reach it.
    """

    foreign = [dividend for dividend in dividends if not dividend.domestic]

    withheld = sum((d.withholding_eur for d in foreign), ZERO)
    creditable = ZERO
    unverified: set[str] = set()

    for dividend in foreign:
        country = dividend.isin[:2]
        cap = VERIFIED_TREATY_CAPS.get(country)

        if cap is None:
            cap = DEFAULT_TREATY_CAP
            unverified.add(country)

        creditable += min(dividend.withholding_eur, cap * dividend.gross_eur)

    creditable = to_cents(creditable)
    taxed_abroad = min(sum((d.gross_eur for d in foreign), ZERO), savings_total)

    if savings_total <= 0 or taxed_abroad <= 0:
        limit = ZERO
    else:
        rate = (quota / savings_total * 100).quantize(
            RATE_QUANTIZE, rounding=ROUND_HALF_UP
        )
        limit = to_cents(taxed_abroad * rate / 100)

    deduction = min(creditable, limit)

    return ForeignCredit(
        withheld=withheld,
        creditable=creditable,
        deduction=deduction,
        excess=to_cents(withheld - creditable),
        unused_limit=creditable - deduction,
        unverified_countries=tuple(sorted(unverified)),
    )
