# Standard libraries
from decimal import Decimal

# Own modules
from degiro_renta.domain.income import DividendIncome
from degiro_renta.domain.money import ZERO


def total_dividend_income(dividends: list[DividendIncome]) -> Decimal:
    """
    Gross dividend income of the period.

    Args:
        dividends: Dividends collected during the period.

    Returns:
        Sum of the gross amounts in EUR.
    """

    return sum((dividend.gross_eur for dividend in dividends), ZERO)


def domestic_withholdings(dividends: list[DividendIncome]) -> Decimal:
    """
    Spanish withholdings, which are a payment on account.

    Only these subtract from the resulting quota: they are withheld on
    account of the same tax being settled (art. 99 LIRPF) and art. 79
    subtracts them to reach the cuota diferencial.

    Args:
        dividends: Dividends collected during the period.

    Returns:
        Sum of the Spanish withholdings in EUR, as a positive amount.
    """

    return sum(
        (dividend.withholding_eur for dividend in dividends if dividend.domestic),
        ZERO,
    )


def foreign_withholdings(dividends: list[DividendIncome]) -> Decimal:
    """
    Withholdings practised abroad, which are not a payment on account.

    A foreign tax is not an advance of the Spanish one: it gives the
    right to the double-taxation deduction of art. 80 LIRPF, capped by
    the treaty rate and by the average effective rate of the return
    (``calculation.double_taxation``).

    Args:
        dividends: Dividends collected during the period.

    Returns:
        Sum of the foreign withholdings in EUR, as a positive amount.
    """

    return sum(
        (dividend.withholding_eur for dividend in dividends if not dividend.domestic),
        ZERO,
    )
