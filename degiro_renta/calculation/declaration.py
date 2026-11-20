# Standard libraries
from dataclasses import dataclass
from decimal import Decimal

# Own modules
from degiro_renta.domain.money import ZERO, percentage_of
from degiro_renta.domain.operations import AcquisitionMatch, Sale


@dataclass(frozen=True)
class DeclarationTotals:
    """
    Aggregates of the lines typed into the tax return.

    Attributes:
        transfer_value: Transfer value added up across every line, in
            EUR.
        acquisition_cost: Acquisition value added up across every line,
            in EUR.
        gain_loss: Gain or loss implied by the lines
            (``transfer_value - acquisition_cost``).
        real_gain_loss: Gain or loss computed once per sale, which is
            the accurate figure.
        rounding_drift: Line total minus the real total, in EUR. Non
            zero when splitting a sale by acquisition date and rounding
            each line to the cent does not add back up.
    """

    transfer_value: Decimal
    acquisition_cost: Decimal
    gain_loss: Decimal
    real_gain_loss: Decimal
    rounding_drift: Decimal

    @property
    def gain_loss_pct(self) -> Decimal | None:
        """
        Gain or loss of the lines as a percentage of their cost.

        Returns:
            The percentage to two decimals, or ``None`` when the
            acquisition cost is zero.
        """

        return percentage_of(self.gain_loss, self.acquisition_cost)


def build_declaration_lines(sales: list[Sale]) -> list[tuple[Sale, AcquisitionMatch]]:
    """
    Flatten the sales into one line per acquisition date.

    The Spanish return declares every transferred element with its own
    acquisition date and value (art. 35 LIRPF), so a sale that consumed
    lots bought on different days yields several lines even though the
    broker executed a single order.

    Args:
        sales: Sales matched by FIFO.

    Returns:
        Pairs of sale and the acquisition it was imputed to, in FIFO
        order.
    """

    return [(sale, match) for sale in sales for match in sale.matches]


def calculate_declaration_totals(sales: list[Sale]) -> DeclarationTotals:
    """
    Add up the declared lines and measure how far they drift.

    Args:
        sales: Sales matched by FIFO.

    Returns:
        ``DeclarationTotals`` with the line totals, the accurate total
        computed per sale and the drift between them.
    """

    lines = build_declaration_lines(sales)

    transfer_value = sum((match.transfer_value for _, match in lines), ZERO)
    acquisition_cost = sum((match.acquisition_cost for _, match in lines), ZERO)
    gain_loss = transfer_value - acquisition_cost
    real_gain_loss = sum((sale.gain_loss for sale in sales), ZERO)

    return DeclarationTotals(
        transfer_value=transfer_value,
        acquisition_cost=acquisition_cost,
        gain_loss=gain_loss,
        real_gain_loss=real_gain_loss,
        rounding_drift=gain_loss - real_gain_loss,
    )
