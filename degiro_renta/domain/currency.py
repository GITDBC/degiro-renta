# Standard libraries
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class CurrencyConversion:
    """
    Currency exchange with no trade of its own to be folded into.

    The exchange difference on foreign currency held is a capital gain
    or loss (art. 33.1 LIRPF) imputed when the currency is converted
    (art. 14.2.e LIRPF, DGT V0152-26). When Degiro converts as part of a
    purchase or a sale, the result is already inside the acquisition and
    transfer values, which are taken from the euro leg the broker
    actually moved. A conversion that pairs with no trade has nowhere to
    hide, so it travels on its own to be reported.

    Attributes:
        date: Date of the exchange.
        time: Time in ``HH:MM`` format.
        eur_amount: Signed euro leg of the exchange.
        foreign_amount: Signed leg in the other currency.
        foreign_currency: Currency code of the non-euro leg.
    """

    date: date
    time: str
    eur_amount: Decimal
    foreign_amount: Decimal
    foreign_currency: str


@dataclass(frozen=True)
class CurrencyGain:
    """
    Gain or loss on a currency exchange with no trade attached.

    Attributes:
        date: Date of the disposal of foreign currency.
        currency: Currency code disposed of.
        units: Units of foreign currency disposed of.
        proceeds_eur: Euros received for them.
        cost_eur: Euro cost of those units, FIFO over earlier exchanges.
        gain_eur: ``proceeds_eur - cost_eur``.
    """

    date: date
    currency: str
    units: Decimal
    proceeds_eur: Decimal
    cost_eur: Decimal
    gain_eur: Decimal
