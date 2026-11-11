# Standard libraries
from decimal import Decimal
from typing import Final

# Quantum for rounding money to cents.
CENT_QUANTIZE: Final[Decimal] = Decimal("0.01")
