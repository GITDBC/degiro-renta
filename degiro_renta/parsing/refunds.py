# Standard libraries
import logging
from datetime import date
from decimal import Decimal
from typing import Final

# Own modules
from degiro_renta.domain.income import OtherIncome
from degiro_renta.domain.money import EUR, ZERO
from degiro_renta.parsing.descriptions import is_transaction_cost_row
from degiro_renta.parsing.rows import AccountRow, GroupKey
from degiro_renta.parsing.values import parse_date

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def _repay(costs: list[AccountRow], day: date, amount: Decimal) -> tuple[Decimal, int]:
    """
    Repay one refund against the oldest costs charged up to its date.

    Args:
        costs: Transaction-cost rows, oldest first. They are corrected in
            place.
        day: Date the refund was credited.
        amount: Amount of the refund.

    Returns:
        What was left over and the number of rows that were repaid.
    """

    remaining = amount
    repaid = 0

    for row in costs:
        if remaining <= ZERO or parse_date(row["date"]) > day:
            break

        charged = -row["variation"]
        if charged <= ZERO:
            continue

        take = min(charged, remaining)
        row["variation"] += take
        remaining -= take
        repaid += 1

    return remaining, repaid


def apply_fee_refunds(
    groups: dict[GroupKey, list[AccountRow]],
    refunds: list[tuple[date, Decimal, str]],
) -> list[OtherIncome]:
    """
    Subtract the refunds of transaction costs from the costs they repay.

    A refund of what was paid is not an income: the expense was smaller
    (art. 35.1.b and 35.2 LIRPF, which count only what the buyer or the
    seller paid). Degiro's promotion repays the first transaction costs
    of the account, so each refund takes the oldest costs charged up to
    its date that it has not repaid yet, and the rows are corrected in
    place before the operations are built from them.

    Args:
        groups: Rows of the statement grouped per order.
        refunds: Refunds credited, as date, amount and description.

    Returns:
        What no cost was left to repay, as other income to be reviewed.
    """

    costs = sorted(
        (
            row
            for rows in groups.values()
            for row in rows
            if is_transaction_cost_row(row["description"]) and row["currency"] == EUR
        ),
        key=lambda row: (parse_date(row["date"]), row["time"]),
    )
    unrepaid: list[OtherIncome] = []

    for day, amount, description in sorted(refunds, key=lambda refund: refund[0]):
        remaining, repaid = _repay(costs, day, amount)

        _LOGGER.warning(
            "«%s» de %s EUR (%s): se ha restado de los costes de transacción "
            "de las %d órdenes más antiguas que repaga, porque devuelve gastos "
            "ya pagados (arts. 35.1.b y 35.2 LIRPF) y no es un ingreso. Si "
            "Degiro la califica de otro modo, deshaz el ajuste.",
            description,
            amount,
            day.strftime("%d-%m-%Y"),
            repaid,
        )

        if remaining > ZERO:
            unrepaid.append(OtherIncome(day, description, remaining))

    return unrepaid
