# Standard libraries
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Final

# Own modules
from degiro_renta.domain.money import ZERO

# Thousands separator Degiro writes quantities with, in the Spanish
# locale of the export: "1.081" is 1081 units, not a fractional amount.
THOUSANDS_SEPARATOR: Final[str] = "."

# Quantity of units of a buy/sell row. The separated form is matched
# explicitly, group by group, instead of accepting any run of digits and
# dots: a match then converts exactly by removing the separators, and a
# quantity that is not a whole number of units does not match at all.
# The plain alternative comes second so "1.081" is read as one grouped
# number rather than as the "1" in front of it.
QUANTITY_PATTERN: Final[str] = r"\d{1,3}(?:\.\d{3})+|\d+"


def amount_to_decimal(text: str) -> Decimal:
    """
    Convert a Degiro XLSX amount cell to an exact Decimal.

    The XLSX export stores amounts as native numbers that Polars
    renders as dot-decimal text (for example ``"-1734.6"``) when the
    sheet is read as strings. Converting straight from that text keeps
    full precision and avoids both the European thousand/decimal
    ambiguity and IEEE-754 float artifacts.

    Args:
        text: Raw amount cell, empty when the cell is blank.

    Returns:
        Equivalent Decimal value, or ``Decimal(0)`` if the string is
        empty.

    Raises:
        ValueError: If the string is not a valid amount.
    """

    if not text:
        return ZERO

    try:
        return Decimal(text)

    except InvalidOperation as err:
        error_message = (
            f"Importe no numérico en el extracto: {text!r}. Exporta de nuevo "
            f"el Estado de cuenta desde Degiro sin abrirlo ni editarlo."
        )
        raise ValueError(error_message) from err


def quantity_to_int(text: str) -> int:
    """
    Convert the quantity of a buy/sell description to units.

    Degiro writes the quantity in the Spanish locale, so the dot is a
    thousands separator: "1.081" is 1081 units. Removing the separators
    by hand, rather than leaning on ``locale``, keeps the conversion
    independent of the environment the report is produced in.

    Only text already matched by ``QUANTITY_PATTERN`` reaches here, so
    every dot present is a separator and the result is exact.

    Args:
        text: Quantity group of an ``OPERATION_REGEX`` match.

    Returns:
        Number of units the operation moved.
    """

    return int(text.replace(THOUSANDS_SEPARATOR, ""))


def parse_date(text: str) -> date:
    """
    Parse dates in ``dd-mm-yyyy`` or ``dd-mm-yy`` format.

    Args:
        text: String with the date to parse.

    Returns:
        Corresponding ``date`` object.

    Raises:
        ValueError: If the string matches none of the accepted
            formats.
    """

    for fmt in ("%d-%m-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(text, fmt).date()

        except ValueError:
            continue

    error_message = (
        f"Fecha no reconocida en el extracto: {text!r}. Se espera "
        f"dd-mm-aaaa, el formato del export de Degiro."
    )
    raise ValueError(error_message)
