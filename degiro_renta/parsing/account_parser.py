# Standard libraries
import logging
from pathlib import Path
from typing import Final

# Own modules
from degiro_renta.domain.income import DividendIncome
from degiro_renta.domain.operations import Operation, UnvaluedOperation
from degiro_renta.domain.statement import (
    AccountStatement,
    UnclassifiedRow,
)
from degiro_renta.parsing.dividends import build_group_dividend
from degiro_renta.parsing.exchanges import pair_currency_conversions
from degiro_renta.parsing.operations import (
    build_group_operations,
    drop_unvalued_isins,
)
from degiro_renta.parsing.refunds import apply_fee_refunds
from degiro_renta.parsing.rows import read_statement_rows

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def warn_on_unclassified_rows(rows: tuple[UnclassifiedRow, ...]) -> None:
    """
    Warn about the rows that reached no fiscal concept.

    An export in another language, or a movement type Degiro adds later,
    shows up here. Saying so beats printing a report that quietly leaves
    money out.

    Args:
        rows: Rows the parser could neither recognize nor attribute.

    Returns:
        None.
    """

    if not rows:
        return

    sample = ", ".join(sorted({row.description for row in rows})[:5])

    _LOGGER.warning(
        "%d fila(s) del extracto no se han podido clasificar y quedan fuera "
        "del informe: %s. Revisa si el extracto está en otro idioma o si "
        "contiene movimientos no contemplados.",
        len(rows),
        sample,
    )


def warn_on_orderless_operations(operations: list[Operation]) -> None:
    """
    Warn about the buys and sells that carry no order number.

    Every trade of a real order has one. Degiro books ISIN changes,
    splits and exchanges of shares as a sale of the old security and a
    purchase of the new one with none, and they are usually not a
    transmission at all, so they must not be taken for one in silence.

    Args:
        operations: Operations built from rows with no order number.

    Returns:
        None.
    """

    if not operations:
        return

    ordered = sorted(operations, key=lambda operation: (operation.date, operation.time))
    sample = ", ".join(
        f"{operation.operation_type.value} {operation.quantity} {operation.isin} "
        f"({operation.date:%d-%m-%Y})"
        for operation in ordered[:5]
    )

    _LOGGER.warning(
        "%d operación(es) sin número de orden: %s. Degiro anota así los "
        "cambios de ISIN, los splits y los canjes, que normalmente no son "
        "ventas ni compras: aquí se tratan como tales y pueden dar una "
        "ganancia o pérdida que no existe. Revísalas antes de declarar.",
        len(operations),
        sample,
    )


def warn_on_empty_statement(statement: AccountStatement) -> None:
    """
    Warn when nothing fiscally relevant came out of the statement.

    An empty report is indistinguishable from a year with no activity,
    which is exactly how an unparseable export would look.

    Args:
        statement: Parsed statement about to be returned.

    Returns:
        None.
    """

    if statement.operations or statement.dividends:
        return

    _LOGGER.warning(
        "No se ha reconocido ninguna compra, venta ni dividendo en el "
        "extracto. Comprueba que es el XLSX de Estado de cuenta de Degiro "
        "exportado en castellano y que cubre el periodo esperado."
    )


def parse_account_xlsx(path: Path) -> AccountStatement:
    """
    Parse a Degiro Account.xlsx statement.

    Reads the ``Estado de cuenta`` sheet and groups rows by Order ID
    (or by ``(Date, Time, ISIN)`` when there is no ID) to obtain the
    broker's real EUR consideration (the ``Cambio de Divisa`` rows in
    EUR), the associated fees and the dividends collected with their
    withholdings. Amounts are read as exact Decimals so no monetary
    precision is lost.

    Every row is accounted for: interest, promotions and currency
    exchanges that pair with no trade travel with the statement instead
    of being dropped, and anything left unrecognized is reported.

    Args:
        path: Path to the Account.xlsx file exported from Degiro
            (account statement).

    Returns:
        ``AccountStatement`` with the operations sorted by date and
        time, the dividends sorted by date, and every other concept the
        statement carries.

    Raises:
        ValueError: If a date or an amount in the sheet is not valid.
    """

    collected = read_statement_rows(path)
    unrepaid_refunds = apply_fee_refunds(collected.groups, collected.fee_refunds)

    operations: list[Operation] = []
    dividends: list[DividendIncome] = []
    unvalued: list[UnvaluedOperation] = []
    conversions = pair_currency_conversions(collected.loose_exchanges)

    orderless: list[Operation] = []

    for key, rows in collected.groups.items():
        group_operations, group_unvalued = build_group_operations(rows)
        operations.extend(group_operations)

        if isinstance(key, tuple):
            orderless.extend(group_operations)
        unvalued.extend(group_unvalued)

        dividend = build_group_dividend(rows)
        if dividend is not None:
            dividends.append(dividend)

        # An exchange inside a group of trades or of dividends is the
        # conversion of that very payment, already inside its euro
        # figures. One that pairs with neither is a swap of currency on
        # its own, which alters the patrimony by itself.
        if not group_operations and not group_unvalued and dividend is None:
            conversions.extend(pair_currency_conversions(rows))

    operations = drop_unvalued_isins(operations, unvalued)
    operations.sort(key=lambda operation: (operation.date, operation.time))
    dividends.sort(key=lambda dividend: dividend.date)

    statement = AccountStatement(
        operations=operations,
        dividends=dividends,
        other_income=tuple(collected.other_income) + tuple(unrepaid_refunds),
        currency_conversions=tuple(
            sorted(conversions, key=lambda item: (item.date, item.time))
        ),
        unvalued_operations=tuple(unvalued),
        unclassified_rows=tuple(collected.unclassified),
        connectivity_entries=tuple(collected.connectivity_entries),
        interest_entries=tuple(collected.interest_entries),
        cash_balances=tuple(collected.cash_balances),
        last_date=collected.last_date,
    )

    warn_on_unclassified_rows(statement.unclassified_rows)
    warn_on_orderless_operations(orderless)
    warn_on_empty_statement(statement)

    return statement
