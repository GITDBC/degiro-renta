# Standard libraries
from collections import defaultdict
from decimal import Decimal

# Own modules
from degiro_renta.domain.currency import CurrencyConversion
from degiro_renta.domain.money import EUR, ZERO
from degiro_renta.parsing.descriptions import EXCHANGE_DESCRIPTION
from degiro_renta.parsing.rows import AccountRow
from degiro_renta.parsing.values import parse_date


def sum_exchange_eur_legs(rows: list[AccountRow]) -> Decimal | None:
    """
    Total EUR leg of the currency exchanges of an operation group.

    Every ``Cambio de Divisa`` row denominated in EUR is added up.
    Degiro emits one exchange pair per execution, so an order filled in
    several tranches carries several EUR legs and taking only the first
    would understate the consideration.

    Args:
        rows: Rows of the operation group.

    Returns:
        Sum of the EUR exchange legs, or ``None`` when the group has
        none.
    """

    legs = [
        row["variation"]
        for row in rows
        if EXCHANGE_DESCRIPTION in row["description"] and row["currency"] == EUR
    ]

    if not legs:
        return None

    return sum(legs, ZERO)


def implied_exchange_rate(rows: list[AccountRow]) -> Decimal | None:
    """
    EUR per unit of foreign currency implied by an exchange pair.

    Taking the rate from the two legs the broker actually moved needs no
    external source and stays consistent with the euro figures of the
    rest of the report.

    Args:
        rows: Rows of the group.

    Returns:
        Euros per unit of the foreign currency, or ``None`` when the
        group holds no usable exchange pair.
    """

    eur_leg = ZERO
    foreign_leg = ZERO

    for row in rows:
        if EXCHANGE_DESCRIPTION not in row["description"]:
            continue

        if row["currency"] == EUR:
            eur_leg += abs(row["variation"])
        else:
            foreign_leg += abs(row["variation"])

    if not eur_leg or not foreign_leg:
        return None

    return eur_leg / foreign_leg


def pair_currency_conversions(rows: list[AccountRow]) -> list[CurrencyConversion]:
    """
    Pair the legs of the currency exchanges of a set of rows.

    Args:
        rows: Rows holding exchange legs, from one group or from the
            statement at large.

    Returns:
        One conversion per ``(date, time)`` that has both legs, in the
        order the dates appear.
    """

    legs: dict[tuple[str, str], list[AccountRow]] = defaultdict(list)

    for row in rows:
        if EXCHANGE_DESCRIPTION in row["description"]:
            legs[(row["date"], row["time"])].append(row)

    conversions: list[CurrencyConversion] = []

    for (day, time), pair in legs.items():
        eur = next((row for row in pair if row["currency"] == EUR), None)
        foreign = next((row for row in pair if row["currency"] != EUR), None)

        if eur is None or foreign is None:
            continue

        conversions.append(
            CurrencyConversion(
                date=parse_date(day),
                time=time,
                eur_amount=eur["variation"],
                foreign_amount=foreign["variation"],
                foreign_currency=foreign["currency"],
            )
        )

    return conversions
