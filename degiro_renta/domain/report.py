# Standard libraries
from dataclasses import dataclass, field
from decimal import Decimal

# Own modules
from degiro_renta.domain.currency import CurrencyGain
from degiro_renta.domain.foreign_assets import ForeignAssets
from degiro_renta.domain.income import DividendIncome, OtherIncome
from degiro_renta.domain.money import ZERO
from degiro_renta.domain.operations import Sale, UnvaluedOperation
from degiro_renta.domain.savings import LossCarryforward, SavingsBase, TaxBracket
from degiro_renta.domain.wash_sale import WashSaleResult


@dataclass(frozen=True)
class ReportData:
    """
    Precomputed aggregates of one exercise, decoupled from the output.

    Holds every fiscal figure the report prints. Rendering computes no
    tax: it lays the figures out and only adds up columns to show their
    totals.

    Attributes:
        sales: Sales of the exercise whose result is a capital gain or
            loss.
        dividends: Dividends collected in the exercise.
        savings_base: Integration of capital income and capital gains.
        domestic_withholdings: Spanish withholdings, which are a
            payment on account and subtract from the quota. Foreign ones
            are kept apart in ``foreign_withholdings``, since only the
            Spanish part is an advance of this same tax.
        irpf_quota: Bracket breakdown over the savings base, or
            ``None`` if the base is not positive.
        quota_to_pay: Quota left to pay after subtracting the deduction
            of art. 80 and the Spanish withholdings; negative means a
            refund. ``None`` only when there is no exercise.
        connectivity_fees: Connectivity fees charged in the exercise.
        net_return: Realized result after the quota, the foreign
            withholdings, the connectivity fees and the debit interest,
            or ``None`` when the exercise has no result.
        foreign_withholdings: Withholdings practised abroad, which are
            not a payment on account and only give the right to the
            deduction of art. 80 LIRPF.
        interest_expense: Debit interest charged in the exercise.
        other_income: Promotions and rebates of the exercise, reported
            but not integrated.
        unvalued_operations: Trades excluded for having no euro
            consideration, from the whole statement.
        wash_sale: Outcome of the two-month rule in the exercise:
            deferred losses, releases, what is pending at its end and
            the losses whose window the statement does not cover.
        year: Exercise reported, or ``None`` when there is no activity.
        foreign_deduction: Deduction for foreign withholdings applied to
            the quota (art. 80 LIRPF).
        foreign_excess: Foreign withholding above the treaty cap,
            reclaimable at the source country.
        foreign_unused_limit: Creditable foreign withholding that the
            limit of art. 80.1.b prevented from being deducted.
        loss_carryforward: Negative balances still pending after the
            exercise, with the last exercise that can offset them.
        currency_gains: Gains and losses on currency exchanges with no
            trade attached, computed FIFO.
        debt_sales: Sales of the exercise of financial assets of art.
            25.2 LIRPF, whose result is capital income.
        unverified_treaty_countries: Countries whose foreign withholding
            was capped with a treaty rate not verified for them.
        sales_gain_loss: Result of the sales in ``sales``.
        wash_sale_adjustment: Correction of the two-month rule to the
            capital gains and losses of the exercise: deferred losses
            added back, released ones subtracted.
        currency_gain_loss: Result of the currency exchanges with no
            trade attached.
        realized_result: Capital gains and losses plus capital income of
            the exercise, before taxes and costs.
        quota_after_credit: Estimated quota once the deduction of art.
            80 is subtracted.
        foreign_assets: What the account holds abroad when the exercise
            closes, for the modelo 720. ``None`` when there is no
            exercise.
    """

    sales: list[Sale]
    dividends: list[DividendIncome]
    savings_base: SavingsBase
    domestic_withholdings: Decimal
    irpf_quota: list[TaxBracket] | None
    quota_to_pay: Decimal | None
    connectivity_fees: Decimal
    net_return: Decimal | None
    foreign_withholdings: Decimal = ZERO
    interest_expense: Decimal = ZERO
    other_income: tuple[OtherIncome, ...] = ()
    unvalued_operations: tuple[UnvaluedOperation, ...] = ()
    wash_sale: WashSaleResult = WashSaleResult()
    year: int | None = None
    foreign_deduction: Decimal = ZERO
    foreign_excess: Decimal = ZERO
    foreign_unused_limit: Decimal = ZERO
    loss_carryforward: tuple[LossCarryforward, ...] = ()
    currency_gains: tuple[CurrencyGain, ...] = ()
    debt_sales: list[Sale] = field(default_factory=list)
    unverified_treaty_countries: tuple[str, ...] = ()
    sales_gain_loss: Decimal = ZERO
    wash_sale_adjustment: Decimal = ZERO
    currency_gain_loss: Decimal = ZERO
    realized_result: Decimal = ZERO
    quota_after_credit: Decimal = ZERO
    foreign_assets: ForeignAssets | None = None
