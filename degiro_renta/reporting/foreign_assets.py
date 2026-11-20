# Standard libraries
from decimal import Decimal
from typing import Final

# Own modules
from degiro_renta.domain.foreign_assets import ForeignAssets
from degiro_renta.domain.report import ReportData
from degiro_renta.reporting.helpers import Notice, format_date, format_decimal

# Heading the notes about the assets held abroad are listed under.
MODEL_720_CATEGORY: Final[str] = "Modelo 720"

# Value a block of assets held abroad has to exceed for the modelo 720
# to be filed: the balances of the accounts, on 31 December and on
# average over the last quarter, art. 42 bis.4.e RGGI; the securities,
# collective investment schemes and insurances taken together, art. 42
# ter.4.c RGGI (RD 1065/2007). The Orden HAP/72/2013 refers to them
# without repeating the limit.
MODEL_720_THRESHOLD: Final[Decimal] = Decimal(50_000)

# Share of that limit from which the report mentions the modelo 720. The
# statement knows what the positions cost, not what they are worth on 31
# December, so it warns well before the cost reaches the limit.
MODEL_720_NOTICE_RATIO: Final[Decimal] = Decimal("0.5")


def _reaches_notice(amount: Decimal) -> bool:
    """
    Whether an amount is close enough to the limit to be mentioned.

    Args:
        amount: Cost of the positions or cash balance.

    Returns:
        True when it reaches the share of the limit the report warns at.
    """

    return amount >= MODEL_720_THRESHOLD * MODEL_720_NOTICE_RATIO


def _deadline(year: int) -> str:
    """
    Period in which the modelo 720 of an exercise is filed (art. 7 of the
    Orden HAP/72/2013).

    Args:
        year: Exercise the declaration refers to.

    Returns:
        The period, from 1 January to 31 March of the following year.
    """

    return f"del 1 de enero al 31 de marzo de {year + 1}"


def _securities_notice(assets: ForeignAssets, year: int) -> Notice | None:
    """
    Note about the block of securities and collective investment schemes.

    The modelo 720 takes the value on 31 December of the securities and
    the net asset value of the funds, ETFs included, valued as the
    Impuesto sobre el Patrimonio does (art. 42 ter.6 RGGI): shares at
    their average quotation of the last quarter or, on a foreign market
    like the Spanish ones, at their quotation on 31 December. The
    statement does not carry that, so the note gives the cost and says
    what decides. Securities deposited abroad count whatever their
    issuer is (art. 42 ter RGGI), unless the depositary is established in
    Spain, which Degiro is not.

    Args:
        assets: What the account holds when the exercise closes.
        year: Exercise reported.

    Returns:
        The note, or ``None`` when the cost is far below the limit.
    """

    if not _reaches_notice(assets.securities_cost):
        return None

    return Notice(
        f"Valores e IIC: a {format_date(assets.as_of)} las posiciones abiertas "
        f"cuestan {format_decimal(assets.securities_cost)} €. Degiro es una "
        f"entidad en el extranjero: si su valor a 31-12 supera "
        f"{format_decimal(MODEL_720_THRESHOLD)} €, se declaran {_deadline(year)}.",
        MODEL_720_CATEGORY,
        severe=assets.securities_cost > MODEL_720_THRESHOLD,
    )


def _cash_notice(assets: ForeignAssets, year: int) -> Notice | None:
    """
    Note about the block of accounts.

    The limit applies to the balance on 31 December and to the average
    of the last quarter, and exceeding either one is enough (art. 42
    bis.4.e RGGI). Only the balance in EUR is known: the one in other
    currencies is not added.

    Args:
        assets: What the account holds when the exercise closes.
        year: Exercise reported.

    Returns:
        The note, or ``None`` when both balances are far below the limit.
    """

    average = assets.cash_average
    highest = (
        assets.cash_balance if average is None else max(assets.cash_balance, average)
    )

    if not _reaches_notice(highest):
        return None

    quarter = (
        ""
        if average is None
        else f" y su media desde el 1 de octubre {format_decimal(average)} €"
    )

    return Notice(
        f"Cuenta: el saldo en euros a {format_date(assets.as_of)} es "
        f"{format_decimal(assets.cash_balance)} €{quarter}. Se declara "
        f"{_deadline(year)} si el saldo a 31-12 o la media del último "
        f"trimestre supera {format_decimal(MODEL_720_THRESHOLD)} €.",
        MODEL_720_CATEGORY,
        severe=highest > MODEL_720_THRESHOLD,
    )


def foreign_assets_notices(data: ReportData) -> list[Notice]:
    """
    Remind of the modelo 720 when the account is near its limit.

    Degiro is an entity abroad, so what it holds counts for the modelo
    720 (Orden HAP/72/2013), which is filed once a block exceeds 50,000
    EUR (arts. 42 bis and 42 ter RGGI). Securities and cash are separate
    blocks. The statement knows
    the cost of the positions, not their value on 31 December, so the
    note says what the statement shows and what decides the obligation.
    Whether the modelo was filed in an earlier year, which changes when
    it has to be filed again, is not known here.

    Args:
        data: Report data of the exercise.

    Returns:
        A note per block that is near or over the limit, none when
        both are far below it or when there is no exercise.
    """

    if data.foreign_assets is None or data.year is None:
        return []

    notices = (
        _securities_notice(data.foreign_assets, data.year),
        _cash_notice(data.foreign_assets, data.year),
    )

    return [notice for notice in notices if notice is not None]
