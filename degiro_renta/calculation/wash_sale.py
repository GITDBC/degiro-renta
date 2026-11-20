# Standard libraries
import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Final

# Own modules
from degiro_renta.domain.money import ZERO, to_cents
from degiro_renta.domain.operations import Operation, OperationType, Sale
from degiro_renta.domain.wash_sale import (
    UncoveredWindow,
    WashSaleDeferral,
    WashSalePending,
    WashSaleRelease,
    WashSaleResult,
)

# Months before and after a transmission in which acquiring homogeneous
# listed securities defers the loss (art. 33.5.f LIRPF), and the same
# window for financial assets (art. 25.2.b LIRPF). Everything a Degiro
# statement holds is admitted to trading.
WINDOW_MONTHS: Final[int] = 2


@dataclass
class _IsinLedger:
    """
    Purchases and sales of one ISIN, by date.

    Attributes:
        buys: Units bought per date.
        sells: Units sold per date.
        consumed: Units of each purchase date already transmitted by the
            sales processed so far, as FIFO identified them.
        used: Units of each purchase date already counted as a
            repurchase by a sale processed so far. A purchase cannot
            count for more than one transmission (DGT V0913-08, V3282-18).
    """

    buys: dict[date, int] = field(default_factory=lambda: defaultdict(int))
    sells: dict[date, int] = field(default_factory=lambda: defaultdict(int))
    consumed: dict[date, int] = field(default_factory=lambda: defaultdict(int))
    used: dict[date, int] = field(default_factory=lambda: defaultdict(int))

    def units_held_at(self, day: date) -> int:
        """
        Units held once every operation dated up to ``day`` is applied.

        Args:
            day: Last date included.

        Returns:
            Units held at the end of ``day``.
        """

        bought = sum(units for when, units in self.buys.items() if when <= day)
        sold = sum(units for when, units in self.sells.items() if when <= day)

        return bought - sold


@dataclass
class _PendingLine:
    """
    Units of a deferred loss that were acquired on the same terms.

    Attributes:
        units: Units still pending.
        unit_loss: Loss of each one, negative.
    """

    units: int
    unit_loss: Decimal


@dataclass
class _OpenDeferral:
    """
    Deferred loss waiting for definitive transmissions to impute it.

    Attributes:
        deferral: The deferral as reported.
        lines: Units still pending with the loss of each, in acquisition
            order, oldest first.
        amount: Deferred loss still pending, negative.
        units: Units still pending.
    """

    deferral: WashSaleDeferral
    lines: list[_PendingLine]
    amount: Decimal
    units: int


def add_months(day: date, months: int) -> date:
    """
    Move a date by whole months, clamping the day to the month end.

    Args:
        day: Date to move.
        months: Months to add; negative moves backwards.

    Returns:
        The shifted date, with the day clamped when the target month is
        shorter (31 March back two months is 31 January, but 31 December
        forward two months is the last day of February).
    """

    total = day.month - 1 + months
    year = day.year + total // 12
    month = total % 12 + 1
    last_day = calendar.monthrange(year, month)[1]

    return date(year, month, min(day.day, last_day))


def build_isin_ledgers(operations: list[Operation]) -> dict[str, _IsinLedger]:
    """
    Group the purchases and sales of the statement by ISIN and date.

    Args:
        operations: Normalized operations of the statement.

    Returns:
        Mapping of ISIN to its ledger.
    """

    ledgers: dict[str, _IsinLedger] = defaultdict(_IsinLedger)

    for operation in operations:
        ledger = ledgers[operation.isin]

        if operation.operation_type == OperationType.BUY:
            ledger.buys[operation.date] += operation.quantity
        else:
            ledger.sells[operation.date] += operation.quantity

    return ledgers


def _repurchased_units(sale: Sale, ledger: _IsinLedger) -> dict[date, int]:
    """
    Units counted as repurchased for a transmission, per purchase date.

    Art. 33.5.f LIRPF, as the DGT applies it (V0913-08, V1117-21,
    V3282-18) and the Manual práctico de Renta 2025 explains it (chapter
    11, section A):

    - Purchases of the two months before count only while they remain
      held after the transmission, so they are capped by the units held
      afterwards. A window holding a single purchase before the
      transmission, with nothing held when it opened, is not a
      repurchase.
    - Purchases of the two months after count whatever happens to them
      later: selling them is what makes a later transmission definitive.
    - A purchase already counted for an earlier transmission is left
      out, and the units counted never exceed the units sold.

    Purchases are taken oldest first.

    Args:
        sale: Transmission being checked. Its own units must already be
            recorded in ``ledger.consumed``.
        ledger: Purchases and sales of its ISIN.

    Returns:
        Repurchased units per purchase date, oldest first. Empty when the
        transmission is definitive.
    """

    start = add_months(sale.date, -WINDOW_MONTHS)
    end = add_months(sale.date, WINDOW_MONTHS)

    before = sorted(day for day in ledger.buys if start <= day <= sale.date)
    after = sorted(day for day in ledger.buys if sale.date < day <= end)

    if len(before) == 1 and ledger.units_held_at(start - timedelta(days=1)) == 0:
        before = []

    held_after = ledger.units_held_at(sale.date)
    budget = sale.quantity
    counted: dict[date, int] = {}

    for day in before:
        take = min(
            max(0, ledger.buys[day] - ledger.consumed[day] - ledger.used[day]),
            held_after,
            budget,
        )

        if take > 0:
            counted[day] = take
            held_after -= take
            budget -= take

    for day in after:
        take = min(max(0, ledger.buys[day] - ledger.used[day]), budget)

        if take > 0:
            counted[day] = take
            budget -= take

    return counted


def _open_deferral(sale: Sale, repurchased: dict[date, int]) -> _OpenDeferral | None:
    """
    Defer the loss of as many sold units in loss as were repurchased.

    The sale transmits the units acquired first (art. 37.2 LIRPF), and
    the loss that can be imputed is the one of those units, so the
    repurchased units take the loss of the units acquired last (DGT
    V0913-08: «la pérdida patrimonial que puede imputarse es la
    atribuible a las acciones adquiridas en primer lugar»; V1117-21). A
    line in gain of the same sale is never deferred.

    Args:
        sale: Transmission with repurchases.
        repurchased: Repurchased units per purchase date.

    Returns:
        The open deferral, or ``None`` when the sale has no loss.
    """

    budget = sum(repurchased.values())
    deferred_units = 0
    deferred = ZERO
    lines: list[_PendingLine] = []

    for match in reversed(sale.matches):
        if match.gain_loss >= 0 or budget == 0:
            continue

        take = min(match.quantity, budget)
        unit_loss = match.gain_loss / match.quantity
        deferred += unit_loss * take
        deferred_units += take
        budget -= take
        lines.insert(0, _PendingLine(take, unit_loss))

    if deferred_units == 0:
        return None

    amount = to_cents(deferred)

    return _OpenDeferral(
        deferral=WashSaleDeferral(
            transfer_date=sale.date,
            isin=sale.isin,
            sold_units=sale.quantity,
            repurchased_units=deferred_units,
            deferred_eur=amount,
            repurchase_dates=tuple(sorted(repurchased)),
        ),
        lines=lines,
        amount=amount,
        units=deferred_units,
    )


def _release_units(item: _OpenDeferral, units: int) -> Decimal:
    """
    Take units out of a deferral, oldest first, and price their loss.

    Args:
        item: Open deferral to take from.
        units: Units to take, not above the ones pending.

    Returns:
        The loss of those units, negative. The last units of a deferral
        take whatever amount is left, so rounding never leaves a cent
        pending.
    """

    if units == item.units:
        released = item.amount
        item.lines.clear()
    else:
        loss = ZERO
        remaining = units

        while remaining > 0:
            line = item.lines[0]
            take = min(line.units, remaining)
            loss += line.unit_loss * take
            remaining -= take
            line.units -= take

            if line.units == 0:
                item.lines.pop(0)

        released = to_cents(loss)

    item.amount -= released
    item.units -= units

    return released


def _release_deferred_losses(
    sale: Sale, opened: list[_OpenDeferral], definitive_units: int
) -> list[WashSaleRelease]:
    """
    Impute the deferred losses that a definitive transmission frees.

    Each unit transmitted for good frees the loss of one pending unit,
    the oldest pending one first, whichever units they are (DGT V0913-08,
    V1294-22, V0754-26, V1760-23, V0571-21, V0279-25). The sale only
    frees what is definitive in it: the units it counts as repurchased
    free nothing.

    Args:
        sale: Transmission being processed.
        opened: Open deferrals of the same ISIN, oldest first.
        definitive_units: Units of the sale that are transmitted for good.

    Returns:
        The releases the transmission produces.
    """

    releases: list[WashSaleRelease] = []
    remaining = definitive_units

    for item in opened:
        if remaining == 0:
            break

        if item.units == 0:
            continue

        taken = min(item.units, remaining)
        releases.append(
            WashSaleRelease(
                release_date=sale.date,
                transfer_date=item.deferral.transfer_date,
                isin=sale.isin,
                units=taken,
                released_eur=_release_units(item, taken),
            )
        )
        remaining -= taken

    return releases


def detect_wash_sales(sales: list[Sale], operations: list[Operation]) -> WashSaleResult:
    """
    Apply the two-month rule to the whole statement.

    Every transmission, in order, counts its repurchases. The units it
    does not repurchase are transmitted for good and impute, one for one,
    the oldest losses still deferred; its own loss is deferred in as many
    units as it repurchased (arts. 33.5.f and 25.2.b LIRPF, DGT
    V0913-08 and the consultations that follow it). The loss imputed
    falls in the exercise of the definitive transmission.

    Args:
        sales: Sales matched by FIFO, in chronological order.
        operations: Normalized operations of the statement.

    Returns:
        Deferrals, releases and the losses still pending at the end.
    """

    ledgers = build_isin_ledgers(operations)
    opened: dict[str, list[_OpenDeferral]] = defaultdict(list)
    deferrals: list[WashSaleDeferral] = []
    releases: list[WashSaleRelease] = []

    for sale in sales:
        ledger = ledgers[sale.isin]

        for match in sale.matches:
            ledger.consumed[match.acquisition_date] += match.quantity

        repurchased = _repurchased_units(sale, ledger)

        for day, units in repurchased.items():
            ledger.used[day] += units

        releases.extend(
            _release_deferred_losses(
                sale, opened[sale.isin], sale.quantity - sum(repurchased.values())
            )
        )

        item = _open_deferral(sale, repurchased) if repurchased else None

        if item is not None:
            deferrals.append(item.deferral)
            opened[sale.isin].append(item)

    return WashSaleResult(
        deferrals=tuple(deferrals),
        releases=tuple(releases),
        pending=_pending_by_isin(opened),
    )


def _pending_by_isin(
    opened: dict[str, list[_OpenDeferral]],
) -> tuple[WashSalePending, ...]:
    """
    Group the deferred losses still pending by ISIN.

    Args:
        opened: Open deferrals per ISIN.

    Returns:
        One pending entry per ISIN with a loss still deferred.
    """

    pending: list[WashSalePending] = []

    for isin in sorted(opened):
        amount = sum((item.amount for item in opened[isin]), ZERO)
        units = sum(item.units for item in opened[isin])

        if amount != 0:
            pending.append(WashSalePending(isin=isin, units=units, deferred_eur=amount))

    return tuple(pending)


def pending_deferrals_at(
    sales: list[Sale], operations: list[Operation], year: int
) -> tuple[WashSalePending, ...]:
    """
    Deferred losses still pending at the end of an exercise.

    The rule is run over the sales up to the end of that exercise. The
    purchases of the following two months still count, because the
    ledger holds every operation of the statement.

    Args:
        sales: Sales matched by FIFO, in chronological order.
        operations: Normalized operations of the statement.
        year: Exercise whose closing position is wanted.

    Returns:
        One pending entry per ISIN with a loss still deferred.
    """

    up_to = [sale for sale in sales if sale.date.year <= year]

    return detect_wash_sales(up_to, operations).pending


def uncovered_windows(
    sales: list[Sale],
    deferrals: tuple[WashSaleDeferral, ...],
    last_date: date | None,
) -> tuple[UncoveredWindow, ...]:
    """
    Transmissions in loss whose window ends after the statement does.

    Only the window after the transmission can outlast the statement:
    the one before it is always inside, since FIFO needs every earlier
    purchase anyway. Only the part of the loss still imputed counts: a
    part already deferred cannot be deferred again.

    Args:
        sales: Sales to check, in chronological order.
        deferrals: Losses the rule already deferred.
        last_date: Date of the most recent row of the statement.

    Returns:
        One entry per sale with a loss still imputed whose window ends
        after ``last_date``. Empty when the statement has no date.
    """

    if last_date is None:
        return ()

    deferred: dict[tuple[date, str], Decimal] = defaultdict(Decimal)

    for deferral in deferrals:
        deferred[(deferral.transfer_date, deferral.isin)] += deferral.deferred_eur

    uncovered: list[UncoveredWindow] = []

    for sale in sales:
        lines_in_loss = (m.gain_loss for m in sale.matches if m.gain_loss < 0)
        loss = sum(lines_in_loss, ZERO) - deferred[(sale.date, sale.isin)]
        window_end = add_months(sale.date, WINDOW_MONTHS)

        if loss < 0 and window_end > last_date:
            uncovered.append(
                UncoveredWindow(
                    transfer_date=sale.date,
                    isin=sale.isin,
                    loss_eur=loss,
                    window_end=window_end,
                )
            )

    return tuple(uncovered)


def wash_sale_adjustments(
    result: WashSaleResult,
) -> tuple[tuple[date, str, Decimal], ...]:
    """
    Turn the rule's outcome into dated corrections of the result.

    A deferral removes its loss from the year of the transmission, so it
    adds the amount back. A release imputes the loss in the year of the
    definitive transmission. The ISIN tells which block of the savings
    base the correction belongs to.

    Args:
        result: Outcome of ``detect_wash_sales``.

    Returns:
        Triples of date, ISIN and signed correction in EUR.
    """

    corrections: list[tuple[date, str, Decimal]] = [
        (deferral.transfer_date, deferral.isin, -deferral.deferred_eur)
        for deferral in result.deferrals
    ]
    corrections.extend(
        (release.release_date, release.isin, release.released_eur)
        for release in result.releases
    )

    return tuple(corrections)
