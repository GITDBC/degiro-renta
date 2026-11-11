# Standard libraries
from collections import deque
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class OperationType(StrEnum):
    """
    Stock operation type recognized by the parser.

    Inherits from ``str`` to keep compatibility with direct
    comparisons against the ``"Compra"``/``"Venta"`` literals used by
    existing renderers and by the Degiro XLSX statement data.
    """

    BUY = "Compra"
    SELL = "Venta"


class StatementRowKind(StrEnum):
    """
    What a row of the Degiro account statement represents.

    Every row is classified into one of these, so a description the
    parser does not recognize lands in ``UNKNOWN`` and is reported
    instead of dropped in silence. A statement exported in another
    language, or a movement type Degiro adds later, then shows up as a
    warning rather than as a report that quietly declares less.
    """

    OPERATION = "operation"
    FEE = "fee"
    CONNECTIVITY_FEE = "connectivity_fee"
    CURRENCY_EXCHANGE = "currency_exchange"
    DIVIDEND = "dividend"
    DIVIDEND_WITHHOLDING = "dividend_withholding"
    INTEREST = "interest"
    OTHER_INCOME = "other_income"
    CASH_MOVEMENT = "cash_movement"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Operation:
    """
    Normalized buy or sell operation in the broker's real EUR.

    Attributes:
        date: Operation date.
        time: Time in ``HH:MM`` format.
        isin: ISIN identifier of the instrument.
        product: Descriptive product name.
        operation_type: ``OperationType.BUY`` or ``OperationType.SELL``.
        quantity: Number of units.
        amount_eur: Consideration in EUR (sign included).
        fee_eur: Fees attributable to the operation (sign included).
    """

    date: date
    time: str
    isin: str
    product: str
    operation_type: OperationType
    quantity: int
    amount_eur: Decimal
    fee_eur: Decimal


@dataclass(frozen=True)
class AcquisitionMatch:
    """
    Portion of a sale imputed to a single acquisition date.

    The Spanish return asks for the acquisition date and value of every
    transferred element, so a sale that consumes lots bought on
    different days needs one declared line per acquisition date even
    though the broker executed a single order.

    Attributes:
        acquisition_date: Date of the purchase that supplied the units.
        quantity: Units taken from that acquisition date.
        acquisition_cost: Acquisition value of those units in EUR,
            fees included (art. 35.1.b LIRPF).
        transfer_value: Share of the transfer value attributed to those
            units, net of the sale fee (art. 35.2 LIRPF).
    """

    acquisition_date: date
    quantity: int
    acquisition_cost: Decimal
    transfer_value: Decimal

    @property
    def gain_loss(self) -> Decimal:
        """
        Gain or loss attributable to this acquisition date.

        Returns:
            Transfer value minus acquisition cost, in EUR.
        """

        return self.transfer_value - self.acquisition_cost


@dataclass(frozen=True)
class Sale:
    """
    Sale matched against FIFO lots with its acquisition cost.

    Attributes:
        date: Sale date.
        isin: ISIN identifier of the instrument.
        product: Descriptive product name.
        quantity: Units sold.
        acquisition_cost: FIFO acquisition cost imputed in EUR.
        transfer_value: Transfer value net of fees in EUR.
        gain_loss: Capital gain or loss
            (``transfer_value - acquisition_cost``).
        matches: Breakdown per acquisition date, in FIFO order. Empty
            when the caller builds the sale without lot detail.
    """

    date: date
    isin: str
    product: str
    quantity: int
    acquisition_cost: Decimal
    transfer_value: Decimal
    gain_loss: Decimal
    matches: tuple[AcquisitionMatch, ...] = ()


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
class CurrencyConversion:
    """
    Currency exchange with no trade of its own to be folded into.

    A conversion between euros and another currency alters the
    composition of the patrimony, so it is a capital gain or loss in its
    own right (art. 37.1.h LIRPF, ``casilla 1634``). When Degiro
    converts as part of a purchase or a sale, the result is already
    inside the acquisition and transfer values, which are taken from the
    euro leg the broker actually moved. A conversion that pairs with no
    trade has nowhere to hide, so it travels on its own to be reported.

    Attributes:
        date: Date of the exchange.
        time: Time in ``HH:MM`` format.
        eur_amount: Signed euro leg of the exchange.
        foreign_amount: Signed leg in the other currency.
        foreign_currency: Currency code of the non-euro leg.
    """

    date: date
    time: str
    eur_amount: Decimal
    foreign_amount: Decimal
    foreign_currency: str


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


@dataclass(frozen=True)
class UnvaluedOperation:
    """
    Trade the statement gives no way to express in euros.

    Happens on a Manual FX account: the order is settled against a
    balance already held in the foreign currency, so no
    ``Cambio de Divisa`` row accompanies it and the statement never
    states what the trade cost in euros. Guessing a rate would put an
    invented number in a tax report, so the whole ISIN is left out and
    listed here.

    Attributes:
        date: Operation date.
        isin: ISIN identifier of the instrument.
        product: Descriptive product name.
        description: Statement description, verbatim.
        amount: Signed amount in the currency of the trade.
        currency: Currency code of that amount.
    """

    date: date
    isin: str
    product: str
    description: str
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class UnclassifiedRow:
    """
    Statement row whose description the parser does not recognize.

    Attributes:
        date: Row date as written in the statement.
        description: Statement description, verbatim.
        amount: Signed amount as read.
        currency: Currency code of that amount, empty when absent.
    """

    date: str
    description: str
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class WashSaleAlert:
    """
    Loss that art. 33.5.f LIRPF may keep out of this year's base.

    A loss on listed securities is not integrated when homogeneous
    securities were acquired within the two months before or after the
    transmission: it is deferred until they are transmitted for good.
    Whether it applies depends on facts a statement cannot settle
    (homogeneity across brokers, what is still held), so the affected
    amount is reported and left inside the base rather than removed on
    the tool's own authority.

    Attributes:
        transfer_date: Date of the transmission that closed in loss.
        acquisition_date: Acquisition date of the transferred units.
        isin: ISIN identifier of the instrument.
        product: Descriptive product name.
        quantity: Units the loss belongs to.
        loss_eur: The loss itself, as a negative amount in EUR.
        repurchase_dates: Dates of the purchases found inside the
            window, excluding the acquisition the loss comes from.
        position_closed: Whether the ISIN was left with no open lots at
            the end of the statement, in which case the deferred loss
            surfaces in the same year.
    """

    transfer_date: date
    acquisition_date: date
    isin: str
    product: str
    quantity: int
    loss_eur: Decimal
    repurchase_dates: tuple[date, ...]
    position_closed: bool


@dataclass
class Lot:
    """
    Purchase lot pending consumption by FIFO.

    Mutable: the quantity is decremented as sales consume it.

    Attributes:
        quantity: Units remaining in the lot.
        unit_cost: Unit cost in EUR (includes the purchase fee).
        date: Date of the original purchase.
    """

    quantity: int
    unit_cost: Decimal
    date: date


@dataclass(frozen=True)
class TaxBracket:
    """
    Savings-base bracket (art. 66 LIRPF) with its base and quota.

    Attributes:
        lower: Lower bound of the bracket in EUR.
        upper: Upper bound of the bracket in EUR, or ``None`` if last.
        rate: Applied tax rate (e.g. ``0.19``).
        base: Taxable base covered by this bracket in EUR.
        quota: Resulting quota (``base * rate``) in EUR.
    """

    lower: Decimal
    upper: Decimal | None
    rate: Decimal
    base: Decimal
    quota: Decimal


@dataclass(frozen=True)
class AccountStatement:
    """
    Everything the fiscal report needs from a Degiro account export.

    Attributes:
        operations: Normalized buy/sell operations, chronologically
            sorted. Excludes every ISIN that could not be valued in
            euros, so a FIFO chain is never built on a partial history.
        dividends: Dividends collected, with their withholdings.
        connectivity_fees: Absolute total of market connectivity fees
            in EUR.
        interest_income: Credit interest collected, in EUR.
        interest_expense: Absolute total of debit interest charged, in
            EUR.
        other_income: Promotions, rebates and refunds credited.
        currency_conversions: Currency exchanges that pair with no
            trade.
        unvalued_operations: Trades with no euro consideration in the
            statement, whose ISIN was left out of ``operations``.
        unclassified_rows: Rows whose description the parser does not
            recognize.
    """

    operations: list[Operation]
    dividends: list[DividendIncome]
    connectivity_fees: Decimal
    interest_income: Decimal = Decimal(0)
    interest_expense: Decimal = Decimal(0)
    other_income: tuple[OtherIncome, ...] = ()
    currency_conversions: tuple[CurrencyConversion, ...] = ()
    unvalued_operations: tuple[UnvaluedOperation, ...] = ()
    unclassified_rows: tuple[UnclassifiedRow, ...] = ()


@dataclass(frozen=True)
class SavingsBase:
    """
    Savings-base integration of capital income and capital gains.

    Art. 49 LIRPF integrates both balances separately: when the capital
    gains balance is negative it may offset the positive balance of
    ``rendimientos del capital mobiliario`` only up to 25% of it, and the
    remainder carries forward to the next four years. Dividends and
    credit interest are both such returns, so the 25% is measured over
    their sum rather than over the dividends alone.

    Attributes:
        capital_gains: Net balance of capital gains/losses in EUR
            (negative when the year closes at a loss).
        dividend_income: Gross dividend income in EUR.
        interest_income: Credit interest collected in EUR.
        offset_applied: Losses actually offset against capital income.
        carryforward_losses: Losses left to carry to future years.
        total: Resulting taxable savings base in EUR.
    """

    capital_gains: Decimal
    dividend_income: Decimal
    offset_applied: Decimal
    carryforward_losses: Decimal
    total: Decimal
    interest_income: Decimal = Decimal(0)

    @property
    def capital_income(self) -> Decimal:
        """
        Positive balance of ``rendimientos del capital mobiliario``.

        Returns:
            Gross dividends plus credit interest, in EUR.
        """

        return self.dividend_income + self.interest_income


@dataclass(frozen=True)
class YearlyResult:
    """
    Realized result of a single fiscal year, with its running total.

    Capital gains and dividends are reported per year because IRPF is
    settled per year, and cumulatively because the running total is
    what tells the investor how the account has done since it was
    opened. Losses pending offset are not tracked here: they depend on
    the four-year carryforward window (art. 49 LIRPF) and on balances
    outside this statement.

    Attributes:
        year: Calendar year of the operations.
        gain_loss: Net capital gains/losses realized that year in EUR.
        dividend_income: Gross dividends collected that year in EUR.
        withholdings: Withholdings practised that year, as a positive
            amount in EUR.
        sale_count: Number of sales matched that year.
        cumulative_gain_loss: Capital gains/losses accumulated from the
            first year up to and including this one.
        cumulative_dividend_income: Gross dividends accumulated from
            the first year up to and including this one.
    """

    year: int
    gain_loss: Decimal
    dividend_income: Decimal
    withholdings: Decimal
    sale_count: int
    cumulative_gain_loss: Decimal
    cumulative_dividend_income: Decimal

    @property
    def total(self) -> Decimal:
        """
        Realized result of the year before taxes.

        Returns:
            Capital gains plus gross dividends of the year, in EUR.
        """

        return self.gain_loss + self.dividend_income

    @property
    def cumulative_total(self) -> Decimal:
        """
        Realized result accumulated up to and including this year.

        Returns:
            Accumulated capital gains plus accumulated gross dividends,
            in EUR.
        """

        return self.cumulative_gain_loss + self.cumulative_dividend_income


@dataclass(frozen=True)
class ReportData:
    """
    Precomputed report aggregates, decoupled from the output format.

    Holds all the information required to render the report in any
    format (stdout, CSV, Excel) without recomputing.

    Attributes:
        sales: Sales matched by FIFO.
        total_gain_loss: Sum of capital gain/loss for the period.
        dividends: Dividends collected during the period.
        savings_base: Integration of capital income and capital gains.
        domestic_withholdings: Spanish withholdings, which are a
            payment on account and subtract from the quota. Deliberately
            not named after the total: ``savings_base`` exposes a
            ``total_withholdings`` function that sums every withholding
            regardless of origin, and only the Spanish part is an
            advance of this same tax.
        irpf_quota: Bracket breakdown over the savings base, or
            ``None`` if the base is not positive.
        quota_to_pay: Quota left to pay after subtracting the
            withholdings already practised; negative means a refund.
            ``None`` when ``irpf_quota`` is ``None``.
        connectivity_fees: Absolute total of connectivity fees.
        net_return: Return after taxes and custody fees, or ``None``
            when not applicable.
        pending_lots: Open portfolio after applying FIFO.
        yearly_results: Realized result per year with running totals,
            oldest year first.
        foreign_withholdings: Withholdings practised abroad, which are
            not a payment on account and only give the right to the
            deduction of art. 80 LIRPF.
        interest_income: Credit interest integrated into the base.
        interest_expense: Absolute total of debit interest charged.
        other_income: Promotions and rebates, reported but not
            integrated.
        currency_conversions: Currency exchanges with no trade attached.
        unvalued_operations: Trades excluded for having no euro
            consideration.
        wash_sale_alerts: Losses that art. 33.5.f LIRPF may defer.
    """

    sales: list[Sale]
    total_gain_loss: Decimal
    dividends: list[DividendIncome]
    savings_base: SavingsBase
    domestic_withholdings: Decimal
    irpf_quota: list[TaxBracket] | None
    quota_to_pay: Decimal | None
    connectivity_fees: Decimal
    net_return: Decimal | None
    pending_lots: dict[str, deque[Lot]]
    yearly_results: list[YearlyResult]
    foreign_withholdings: Decimal = Decimal(0)
    interest_income: Decimal = Decimal(0)
    interest_expense: Decimal = Decimal(0)
    other_income: tuple[OtherIncome, ...] = ()
    currency_conversions: tuple[CurrencyConversion, ...] = ()
    unvalued_operations: tuple[UnvaluedOperation, ...] = ()
    wash_sale_alerts: tuple[WashSaleAlert, ...] = ()
