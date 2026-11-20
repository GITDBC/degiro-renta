# Standard libraries
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class WashSaleDeferral:
    """
    Loss deferred by the two-month rule (arts. 33.5.f and 25.2.b LIRPF).

    The deferred part is the loss of as many sold units in loss as were
    repurchased, taking the units acquired last: the loss of the first
    ones is imputed (DGT V0913-08). The amount is not lost: it is imputed
    as units are transmitted for good later on.

    Attributes:
        transfer_date: Date of the transmission that closed in loss.
        isin: ISIN identifier of the instrument.
        sold_units: Units transmitted by the sale.
        repurchased_units: Units whose loss is deferred, capped by the
            units repurchased and by the units sold in loss.
        deferred_eur: Deferred part of the losses of the sale, as a
            negative amount.
        repurchase_dates: Dates of the purchases counted as repurchases.
    """

    transfer_date: date
    isin: str
    sold_units: int
    repurchased_units: int
    deferred_eur: Decimal
    repurchase_dates: tuple[date, ...]


@dataclass(frozen=True)
class WashSaleRelease:
    """
    Deferred loss imputed at a definitive transmission.

    Attributes:
        release_date: Date of the transmission that imputes the loss.
        transfer_date: Date of the transmission that deferred it.
        isin: ISIN identifier of the instrument.
        units: Units of the deferral that this transmission frees, which
            are the definitive ones of the sale.
        released_eur: Amount imputed, as a negative amount in EUR.
    """

    release_date: date
    transfer_date: date
    isin: str
    units: int
    released_eur: Decimal


@dataclass(frozen=True)
class WashSalePending:
    """
    Deferred loss still waiting for a definitive transmission.

    Attributes:
        isin: ISIN identifier of the instrument.
        units: Units of the deferred losses still pending, which later
            definitive transmissions free one for one.
        deferred_eur: Deferred amount still pending, as a negative
            amount in EUR.
    """

    isin: str
    units: int
    deferred_eur: Decimal


@dataclass(frozen=True)
class UncoveredWindow:
    """
    Transmission in loss whose two-month window outlasts the statement.

    A purchase made after the last row of the statement, but within the
    two months that follow the transmission, would still defer its loss.
    The statement cannot tell, so the loss is imputed and the report
    asks to check it.

    Attributes:
        transfer_date: Date of the transmission in loss.
        isin: ISIN identifier of the instrument.
        loss_eur: Loss still imputed in the exercise, net of any part
            already deferred, as a negative amount.
        window_end: Last day on which a purchase would still count.
    """

    transfer_date: date
    isin: str
    loss_eur: Decimal
    window_end: date


@dataclass(frozen=True)
class WashSaleResult:
    """
    Outcome of applying the two-month rule to the whole statement.

    Attributes:
        deferrals: Losses deferred, in transmission order.
        releases: Deferred losses imputed, in release order.
        pending: Deferred losses still pending at the end of the
            period, one per ISIN.
        uncovered: Transmissions in loss whose window the statement
            does not cover in full.
    """

    deferrals: tuple[WashSaleDeferral, ...] = ()
    releases: tuple[WashSaleRelease, ...] = ()
    pending: tuple[WashSalePending, ...] = ()
    uncovered: tuple[UncoveredWindow, ...] = ()
