# Standard libraries
import re
from typing import Final

# Own modules
from degiro_renta.domain.statement import (
    StatementRowKind,
)
from degiro_renta.parsing.values import QUANTITY_PATTERN

# Buy/sell row: type, quantity in Spanish notation, product name and the
# unit price after the "@" marker, this one with a decimal comma.
OPERATION_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"^(Compra|Venta)\s+({QUANTITY_PATTERN})\s+.*@([\d.,]+)\s+\w+"
)

# Prefix shared by every buy/sell row. Used to detect operation rows that
# OPERATION_REGEX failed to parse so they are reported instead of silently
# dropped from the fiscal report.
OPERATION_PREFIX_REGEX: Final[re.Pattern[str]] = re.compile(r"^(Compra|Venta)\s")

FEE_DESCRIPTIONS: Final[tuple[str, ...]] = (
    "Costes de transacción",
    "Comisión",
    "Tasa",
    "Impuesto",
    "Transaction Tax",
)

# Description of the market data subscription, charged to the account and
# not to any single trade.
CONNECTIVITY_DESCRIPTION: Final[str] = "Comisión de conectividad con el mercado"

# Fragment identifying both legs of a currency exchange.
EXCHANGE_DESCRIPTION: Final[str] = "Cambio de Divisa"

# Descriptions of the tax withheld at source on a dividend. Checked
# before the dividend itself, since their text also mentions one.
WITHHOLDING_DESCRIPTIONS: Final[tuple[str, ...]] = (
    "Retención del dividendo",
    "Impuesto sobre dividendo",
)

# Openings of a gross dividend row. Matched as a prefix rather than by
# equality: Degiro writes variants such as "Dividendo (ajuste)" or
# "Reparto de dividendo", and requiring the exact word "Dividendo" left
# them out of the report without a word.
DIVIDEND_PREFIXES: Final[tuple[str, ...]] = (
    "Dividendo",
    "Reparto de dividendo",
    "Pago de dividendo",
)

# Fragments of the credit/debit interest rows on the cash balance.
INTEREST_DESCRIPTIONS: Final[tuple[str, ...]] = (
    "Interest",
    "Interés",
    "Intereses",
)

# Description of the promotion that pays back the first transaction costs
# of a new account (up to 100 EUR, never the currency exchange costs), so
# it is a refund of expenses and not a promotional gain.
FEE_REFUND_DESCRIPTIONS: Final[tuple[str, ...]] = ("Promoción DEGIRO reembolso",)

# Start of the row that charges the transaction costs of an order, the
# only expense that promotion pays back. Taxes charged beside it, such as
# the Spanish Transaction Tax, are not part of it.
TRANSACTION_COST_PREFIX: Final[str] = "Costes de transacción"

# Fragments of amounts credited that are neither a return on an
# instrument nor the transmission of one.
OTHER_INCOME_DESCRIPTIONS: Final[tuple[str, ...]] = (
    "Promoción",
    "Bonificación",
    "Reembolso",
)

# Text of the rows that move cash between the trading account and the
# flatexDEGIRO cash account. They come in pairs, a sweep transfer and
# its mirror in the cash account, posted at the same minute.
SWEEP_DESCRIPTION: Final[str] = "Cash Sweep"
SWEEP_MIRROR_DESCRIPTION: Final[str] = "Cuenta de Efectivo en flatexDEGIRO"

# Fragments of the rows that only move cash in or out of the account,
# which alter no patrimony and belong in no fiscal block.
CASH_DESCRIPTIONS: Final[tuple[str, ...]] = (
    SWEEP_DESCRIPTION,
    "Deposit",
    "Depósito",
    "Withdrawal",
    "Transferir",
    "Ingreso",
    "Retirada",
    "flatex",
)

# Description fragments mapped to what they mean, in the order they must
# be tried. A withholding names a dividend, a dividend processing fee
# names dividends, an exchange leg is worded like a deposit and the
# connectivity fee is worded like a fee: the first match wins, so the
# narrower concept has to come first.
DESCRIPTION_KINDS: Final[tuple[tuple[tuple[str, ...], StatementRowKind], ...]] = (
    ((CONNECTIVITY_DESCRIPTION,), StatementRowKind.CONNECTIVITY_FEE),
    ((EXCHANGE_DESCRIPTION,), StatementRowKind.CURRENCY_EXCHANGE),
    (WITHHOLDING_DESCRIPTIONS, StatementRowKind.DIVIDEND_WITHHOLDING),
    (INTEREST_DESCRIPTIONS, StatementRowKind.INTEREST),
    (FEE_REFUND_DESCRIPTIONS, StatementRowKind.FEE_REFUND),
    (OTHER_INCOME_DESCRIPTIONS, StatementRowKind.OTHER_INCOME),
    (FEE_DESCRIPTIONS, StatementRowKind.FEE),
    (CASH_DESCRIPTIONS, StatementRowKind.CASH_MOVEMENT),
)


def is_withholding_row(description: str) -> bool:
    """
    Report whether a description is the tax withheld on a dividend.

    Args:
        description: Statement description to test.

    Returns:
        True when the row is a withholding, or a refund of one.
    """

    return any(key in description for key in WITHHOLDING_DESCRIPTIONS)


def is_transaction_cost_row(description: str) -> bool:
    """
    Report whether a description is the transaction cost of an order.

    Args:
        description: Statement description to test.

    Returns:
        True when the row charges the broker's own cost of the order and
        not a tax or another fee.
    """

    return description.startswith(TRANSACTION_COST_PREFIX)


def is_sweep_row(description: str) -> bool:
    """
    Report whether a description is one of the two rows of a cash sweep.

    The sweep moves cash between two accounts of the client, so the cash
    he holds does not change. One row of the pair states a passing
    balance that the other one undoes, and which of the two it is varies
    from pair to pair, so neither tells the cash at that moment.

    Args:
        description: Statement description to test.

    Returns:
        True when the row moves cash between the two accounts.
    """

    return SWEEP_DESCRIPTION in description or SWEEP_MIRROR_DESCRIPTION in description


def is_dividend_row(description: str) -> bool:
    """
    Report whether a description opens a gross dividend row.

    Args:
        description: Statement description to test.

    Returns:
        True when the row is a gross dividend and not its withholding.
    """

    if is_withholding_row(description):
        return False

    return description.startswith(DIVIDEND_PREFIXES)


def classify_description(description: str) -> StatementRowKind:
    """
    Decide what a statement row means from its description.

    Every row gets a kind, so a description this parser does not know
    ends up as ``UNKNOWN`` and can be reported. The order of the checks
    matters: a withholding mentions a dividend, a dividend processing
    fee mentions dividends, and both legs of a currency exchange are
    worded like a deposit and a withdrawal.

    Args:
        description: Statement description to classify.

    Returns:
        The kind the row belongs to.
    """

    if OPERATION_PREFIX_REGEX.match(description):
        return StatementRowKind.OPERATION

    # Checked before the keyword table because a gross dividend row is
    # recognized by how it opens, not by a fragment: that is what keeps
    # a dividend processing fee from being read as a dividend.
    if is_dividend_row(description):
        return StatementRowKind.DIVIDEND

    for keywords, kind in DESCRIPTION_KINDS:
        if any(keyword in description for keyword in keywords):
            return kind

    return StatementRowKind.UNKNOWN
