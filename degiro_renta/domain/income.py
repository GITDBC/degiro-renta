# Standard libraries
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class DividendIncome:
    """
    Dividend collected on a position, with its withholding at source.

    Dividends are ``rendimientos del capital mobiliario`` and feed the
    same savings base as capital gains (art. 49 LIRPF). Where the
    withholding was practised decides what can be done with it: a
    Spanish one is a 19% payment on account that subtracts from the
    quota, while a foreign one is not, and only gives the right to the
    double-taxation deduction of art. 80 LIRPF, capped by the treaty
    and by the average effective rate. Both are tracked apart from the
    gross amount and from each other.

    Attributes:
        date: Payment date.
        isin: ISIN identifier of the paying instrument.
        product: Descriptive product name.
        gross_eur: Gross dividend in EUR before withholding.
        withholding_eur: Withholding practised, as a positive amount.
        domestic: Whether the withholding is Spanish, and therefore a
            payment on account. Defaults to ``True``.
    """

    date: date
    isin: str
    product: str
    gross_eur: Decimal
    withholding_eur: Decimal
    domestic: bool = True

    @property
    def net_eur(self) -> Decimal:
        """
        Amount actually credited to the account.

        Returns:
            Gross dividend minus the withholding, in EUR.
        """

        return self.gross_eur - self.withholding_eur


@dataclass(frozen=True)
class OtherIncome:
    """
    Amount credited that is neither a dividend nor a transmission.

    Promotions, rebates and refunds reach the cash balance without
    being a return on an instrument or the sale of one. Their
    qualification depends on what the broker paid them for, so they are
    reported verbatim instead of being integrated into a base they may
    not belong to.

    Attributes:
        date: Date the amount was credited.
        description: Statement description, verbatim.
        amount_eur: Signed amount in EUR.
    """

    date: date
    description: str
    amount_eur: Decimal
