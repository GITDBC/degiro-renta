# Standard libraries
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

# Own modules
from degiro_renta.domain.currency import CurrencyConversion, CurrencyGain
from degiro_renta.domain.money import ZERO, to_cents

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


@dataclass
class _ForeignLot:
    """
    Foreign currency bought with euros, pending to be disposed of.

    Attributes:
        units: Units still held.
        cost_eur: Euro cost of those units.
    """

    units: Decimal
    cost_eur: Decimal


def calculate_currency_gains(
    conversions: tuple[CurrencyConversion, ...],
) -> tuple[CurrencyGain, ...]:
    """
    Compute the gain or loss of each disposal of foreign currency.

    Only exchanges with no trade attached are passed here. Converting
    euros into a currency acquires units at the euros paid; converting
    them back disposes of units FIFO, and the exchange difference is
    imputed at that conversion (art. 14.2.e LIRPF, DGT V0152-26). A disposal
    with no earlier acquisition in the statement has no determinable
    cost and is skipped with a warning rather than given an invented one.

    Args:
        conversions: Exchanges with no trade attached, oldest first.

    Returns:
        One gain per disposal whose cost could be determined.
    """

    lots: dict[str, deque[_ForeignLot]] = defaultdict(deque)
    gains: list[CurrencyGain] = []

    for conversion in conversions:
        currency = conversion.foreign_currency

        if conversion.eur_amount < 0 and conversion.foreign_amount > 0:
            lots[currency].append(
                _ForeignLot(conversion.foreign_amount, -conversion.eur_amount)
            )
            continue

        if not (conversion.eur_amount > 0 and conversion.foreign_amount < 0):
            continue

        disposed = -conversion.foreign_amount
        remaining = disposed
        cost = ZERO
        queue = lots[currency]

        while remaining > 0 and queue:
            lot = queue[0]
            used = min(remaining, lot.units)
            cost += lot.cost_eur * used / lot.units
            lot.cost_eur -= lot.cost_eur * used / lot.units
            lot.units -= used
            remaining -= used

            if lot.units == 0:
                queue.popleft()

        if remaining > 0:
            _LOGGER.warning(
                "Cambio de %s el %s: %s unidades sin coste de compra en el "
                "extracto; su ganancia no se calcula.",
                currency,
                conversion.date,
                remaining,
            )
            continue

        gains.append(
            CurrencyGain(
                date=conversion.date,
                currency=currency,
                units=disposed,
                proceeds_eur=conversion.eur_amount,
                cost_eur=to_cents(cost),
                gain_eur=to_cents(conversion.eur_amount - cost),
            )
        )

    return tuple(gains)
