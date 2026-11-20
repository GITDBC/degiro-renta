# Standard libraries
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

# Own modules
from degiro_renta.domain.money import percentage_of


class OperationType(StrEnum):
    """
    Stock operation type recognized by the parser.

    Its values are the words that open a buy/sell row of the Degiro
    statement, so the parser builds it straight from the match.
    """

    BUY = "Compra"
    SELL = "Venta"


@dataclass(frozen=True)
class Operation:
    """
    Normalized buy or sell operation in the broker's real EUR.

    Attributes:
        date: Operation date.
        time: Time in ``HH:MM`` format.
        isin: ISIN identifier of the instrument.
        product: Descriptive product name.
        operation_type: ``OperationType.BUY`` or ``OperationType.SELL``.
        quantity: Number of units.
        amount_eur: Consideration in EUR (sign included).
        fee_eur: Fees attributable to the operation (sign included).
    """

    date: date
    time: str
    isin: str
    product: str
    operation_type: OperationType
    quantity: int
    amount_eur: Decimal
    fee_eur: Decimal


@dataclass(frozen=True)
class AcquisitionMatch:
    """
    Portion of a sale imputed to a single acquisition date.

    The Spanish return asks for the acquisition date and value of every
    transferred element, so a sale that consumes lots bought on
    different days needs one declared line per acquisition date even
    though the broker executed a single order.

    Attributes:
        acquisition_date: Date of the purchase that supplied the units.
        quantity: Units taken from that acquisition date.
        acquisition_cost: Acquisition value of those units in EUR,
            fees included (art. 35.1.b LIRPF).
        transfer_value: Share of the transfer value attributed to those
            units, net of the sale fee (art. 35.2 LIRPF).
    """

    acquisition_date: date
    quantity: int
    acquisition_cost: Decimal
    transfer_value: Decimal

    @property
    def gain_loss(self) -> Decimal:
        """
        Gain or loss attributable to this acquisition date.

        Returns:
            Transfer value minus acquisition cost, in EUR.
        """

        return self.transfer_value - self.acquisition_cost


@dataclass(frozen=True)
class Sale:
    """
    Sale matched against FIFO lots with its acquisition cost.

    Attributes:
        date: Sale date.
        isin: ISIN identifier of the instrument.
        product: Descriptive product name.
        quantity: Units sold.
        acquisition_cost: FIFO acquisition cost imputed in EUR.
        transfer_value: Transfer value net of fees in EUR.
        gain_loss: Capital gain or loss
            (``transfer_value - acquisition_cost``).
        matches: Breakdown per acquisition date, in FIFO order, which
            the declaration lines are built from. FIFO always fills it;
            only a sale built by hand may leave it empty.
    """

    date: date
    isin: str
    product: str
    quantity: int
    acquisition_cost: Decimal
    transfer_value: Decimal
    gain_loss: Decimal
    matches: tuple[AcquisitionMatch, ...] = ()

    @property
    def gain_loss_pct(self) -> Decimal | None:
        """
        Gain or loss as a percentage of the acquisition cost.

        Returns:
            The percentage to two decimals, or ``None`` when the
            acquisition cost is zero.
        """

        return percentage_of(self.gain_loss, self.acquisition_cost)


@dataclass(frozen=True)
class UnvaluedOperation:
    """
    Trade the statement gives no way to express in euros.

    Happens on a Manual FX account: the order is settled against a
    balance already held in the foreign currency, so no
    ``Cambio de Divisa`` row accompanies it and the statement never
    states what the trade cost in euros. Guessing a rate would put an
    invented number in a tax report, so the whole ISIN is left out and
    listed here.

    Attributes:
        date: Operation date.
        isin: ISIN identifier of the instrument.
        description: Statement description, verbatim.
        amount: Signed amount in the currency of the trade.
        currency: Currency code of that amount.
    """

    date: date
    isin: str
    description: str
    amount: Decimal
    currency: str


@dataclass
class Lot:
    """
    Purchase lot pending consumption by FIFO.

    Mutable: the quantity is decremented as sales consume it.

    Attributes:
        quantity: Units remaining in the lot.
        unit_cost: Unit cost in EUR (includes the purchase fee).
        date: Date of the original purchase.
    """

    quantity: int
    unit_cost: Decimal
    date: date
