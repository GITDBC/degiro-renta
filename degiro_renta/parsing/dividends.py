# Standard libraries
import logging
from decimal import Decimal
from typing import Final

# Own modules
from degiro_renta.domain.income import DividendIncome
from degiro_renta.domain.money import EUR, ZERO
from degiro_renta.parsing.descriptions import is_dividend_row, is_withholding_row
from degiro_renta.parsing.exchanges import implied_exchange_rate
from degiro_renta.parsing.rows import AccountRow
from degiro_renta.parsing.values import parse_date

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Country prefix of the ISINs whose withholding is Spanish, and
# therefore a payment on account instead of a foreign tax.
SPANISH_ISIN_PREFIX: Final[str] = "ES"


def sum_dividend_withholding(rows: list[AccountRow], currency: str) -> Decimal:
    """
    Net tax withheld at source inside a dividend group.

    A withholding is a negative row and a refund of it a positive one, so
    adding the rows with their sign leaves what was finally withheld.

    Args:
        rows: Rows of the group.
        currency: Currency the gross dividend is denominated in.

    Returns:
        Withholding as a positive amount, in that same currency.
    """

    return -sum(
        (
            row["variation"]
            for row in rows
            if is_withholding_row(row["description"]) and row["currency"] == currency
        ),
        ZERO,
    )


def warn_on_stray_withholdings(rows: list[AccountRow], currency: str | None) -> None:
    """
    Warn about the withholding rows no dividend of the group takes in.

    A refund posted on another day than the dividend, or a withholding in
    another currency than its payment, falls here. Leaving it out of the
    figures without saying so would misstate what was withheld.

    Args:
        rows: Rows of the group.
        currency: Currency of the gross dividend of the group, or ``None``
            when the group holds no dividend.

    Returns:
        None.
    """

    for row in rows:
        if is_withholding_row(row["description"]) and row["currency"] != currency:
            _LOGGER.warning(
                "Retención del dividendo de %s (%s) de %s %s sin dividendo "
                "que la acompañe en el mismo cobro: no se ha tenido en "
                "cuenta. Si es la devolución o la corrección de otro cobro, "
                "ajústala a mano.",
                row["isin"],
                row["date"],
                row["variation"],
                row["currency"],
            )


def build_group_dividend(rows: list[AccountRow]) -> DividendIncome | None:
    """
    Build a ``DividendIncome`` from grouped rows, if any.

    A dividend payment appears as a gross row optionally followed by a
    withholding row for the tax taken at source. Both are matched by the
    ``(date, time, ISIN)`` fallback key because Degiro assigns them no
    Order ID. Every gross row of the group is added up, so a payment
    split across two lines is not read as one.

    A dividend paid in a foreign currency is converted with the rate
    implied by the ``Cambio de Divisa`` pair Degiro settled it with. Only
    when the statement carries no such pair is the payment excluded, with
    a warning, since there is then no rate to convert it by.

    Args:
        rows: XLSX rows belonging to a single group.

    Returns:
        The dividend collected, or ``None`` when the group holds none.

    Raises:
        ValueError: If the payment date is not valid.
    """

    gross_rows = [row for row in rows if is_dividend_row(row["description"])]

    warn_on_stray_withholdings(rows, gross_rows[0]["currency"] if gross_rows else None)

    if not gross_rows:
        return None

    header = gross_rows[0]
    currency = header["currency"]
    gross = sum((row["variation"] for row in gross_rows), ZERO)
    withholding = sum_dividend_withholding(rows, currency)
    rate = Decimal(1)

    if currency != EUR:
        implied = implied_exchange_rate(rows)

        if implied is None:
            _LOGGER.warning(
                "El dividendo de %s (%s) está en %s y el extracto no trae su "
                "cambio de divisa; se excluye del informe fiscal. Añádelo a "
                "mano con el tipo del BCE del día de cobro.",
                header["isin"],
                header["date"],
                currency,
            )
            return None

        rate = implied

    return DividendIncome(
        date=parse_date(header["date"]),
        isin=header["isin"],
        product=header["product"],
        gross_eur=gross * rate,
        withholding_eur=withholding * rate,
        domestic=header["isin"].startswith(SPANISH_ISIN_PREFIX),
    )
