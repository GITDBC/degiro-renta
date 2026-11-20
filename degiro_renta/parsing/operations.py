# Standard libraries
import logging
import re
from decimal import Decimal
from typing import Final

# Own modules
from degiro_renta.domain.money import EUR, ZERO
from degiro_renta.domain.operations import Operation, OperationType, UnvaluedOperation
from degiro_renta.parsing.descriptions import (
    FEE_DESCRIPTIONS,
    OPERATION_PREFIX_REGEX,
    OPERATION_REGEX,
)
from degiro_renta.parsing.exchanges import sum_exchange_eur_legs
from degiro_renta.parsing.rows import AccountRow
from degiro_renta.parsing.values import parse_date, quantity_to_int

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def build_unvalued_operation(header: AccountRow) -> UnvaluedOperation:
    """
    Describe a trade the statement gives no euro consideration for.

    Args:
        header: Buy/sell row that could not be valued.

    Returns:
        The trade, ready to be reported as excluded.
    """

    return UnvaluedOperation(
        date=parse_date(header["date"]),
        isin=header["isin"],
        description=header["description"],
        amount=header["variation"],
        currency=header["currency"],
    )


def build_operation(
    header: AccountRow, match: re.Match[str], amount_eur: Decimal, fee_eur: Decimal
) -> Operation:
    """
    Build a normalized operation from its buy/sell row.

    Args:
        header: Buy/sell row of the group.
        match: Match of ``OPERATION_REGEX`` over the row description,
            resolved by ``select_operation_headers``.
        amount_eur: Consideration in EUR, sign included.
        fee_eur: Fees attributable to this execution, sign included.

    Returns:
        The normalized operation.
    """

    return Operation(
        date=parse_date(header["date"]),
        time=header["time"],
        isin=header["isin"],
        product=header["description"].split("@")[0].split(" ", 2)[2].strip(),
        operation_type=OperationType(match.group(1)),
        quantity=quantity_to_int(match.group(2)),
        amount_eur=amount_eur,
        fee_eur=fee_eur,
    )


def select_operation_headers(
    rows: list[AccountRow],
) -> list[tuple[AccountRow, re.Match[str]]]:
    """
    Pick the buy/sell rows of a group and report unparseable ones.

    A row that starts like an operation but does not match
    ``OPERATION_REGEX`` would otherwise be dropped without trace,
    silently removing a real trade from the fiscal report. Those rows
    are logged as errors so the discrepancy is visible.

    Each selected row travels with the match that parsed it, so the
    callers read the operation type and the quantity off a match the
    type system guarantees instead of matching again behind an
    ``assert`` that ``python -O`` strips from the bytecode.

    A fractional quantity ("Compra 0,5 ...") is reported here too:
    ``Operation.quantity`` holds whole units, and rounding one in
    silence would put an invented figure in a tax return. Being named in
    an error the user can act on beats being declared wrong.

    Args:
        rows: Rows belonging to a single operation group.

    Returns:
        Pairs of row and its match, for the rows whose description is a
        fully parseable buy/sell.
    """

    headers: list[tuple[AccountRow, re.Match[str]]] = []

    for row in rows:
        match = OPERATION_REGEX.match(row["description"])

        if match is not None:
            headers.append((row, match))
        elif OPERATION_PREFIX_REGEX.match(row["description"]):
            _LOGGER.error(
                "Fila de operación ilegible omitida (%s %s %s): %r. NO se "
                "incluye en el informe fiscal.",
                row["date"],
                row["time"],
                row["isin"],
                row["description"],
            )

    return headers


def build_group_operations(
    rows: list[AccountRow],
) -> tuple[list[Operation], list[UnvaluedOperation]]:
    """
    Build the operations of a group, or report them as unvalued.

    When an order has partial executions (several buy/sell rows with the
    same Order ID) it yields one operation per execution, with the fees
    and the euro consideration distributed by share quantity.

    A trade in a foreign currency with no ``Cambio de Divisa`` row of
    its own cannot be expressed in euros from the statement alone, which
    is what a Manual FX account looks like. Those are returned apart
    instead of raised: aborting threw away a whole report over one
    unvaluable order, and inventing a rate would put a made-up number in
    a tax return.

    Args:
        rows: XLSX rows belonging to a single operation.

    Returns:
        Tuple with the operations built and the trades left unvalued.

    Raises:
        ValueError: If a date in the group is not valid.
    """

    headers = select_operation_headers(rows)
    if not headers:
        return [], []

    total_fee = sum(
        (
            row["variation"]
            for row in rows
            if any(key in row["description"] for key in FEE_DESCRIPTIONS)
        ),
        ZERO,
    )

    # Degiro emits one Cambio de Divisa pair per execution, so every
    # EUR exchange leg is added up rather than only the first, which
    # would understate multi-tranche foreign orders.
    total_fx_eur = sum_exchange_eur_legs(rows)
    total_quantity = sum(quantity_to_int(match.group(2)) for _, match in headers)

    operations: list[Operation] = []
    unvalued: list[UnvaluedOperation] = []

    for header, match in headers:
        ratio = Decimal(quantity_to_int(match.group(2))) / Decimal(total_quantity)

        if total_fx_eur is not None:
            amount = total_fx_eur * ratio
        elif header["currency"] == EUR:
            amount = header["variation"]
        else:
            unvalued.append(build_unvalued_operation(header))
            continue

        operations.append(build_operation(header, match, amount, total_fee * ratio))

    return operations, unvalued


def drop_unvalued_isins(
    operations: list[Operation],
    unvalued: list[UnvaluedOperation],
) -> list[Operation]:
    """
    Remove every ISIN whose history has an unvaluable trade.

    A FIFO chain is only as good as the operations feeding it: keeping
    the valuable half of an ISIN would match sales against lots that are
    not all there and publish a gain computed on a partial cost. The
    whole instrument steps aside instead, and is reported.

    Args:
        operations: Operations built from the statement.
        unvalued: Trades with no euro consideration.

    Returns:
        Operations of the ISINs that could be valued in full.
    """

    if not unvalued:
        return operations

    blocked = {item.isin for item in unvalued}

    _LOGGER.warning(
        "%d operación(es) sin contravalor en EUR en el extracto (cuenta "
        "Manual FX o divisa sin cambio asociado). Se excluye del informe "
        "fiscal todo el historial de %s: calcula esos valores aparte en la "
        "divisa y convierte la diferencia al tipo de la fecha de venta (DGT "
        "V0152-26).",
        len(unvalued),
        ", ".join(sorted(blocked)),
    )

    return [operation for operation in operations if operation.isin not in blocked]
