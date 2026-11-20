# Standard libraries
from collections import defaultdict
from datetime import date
from decimal import Decimal

# Own modules
from degiro_renta.calculation.currency import calculate_currency_gains
from degiro_renta.calculation.dividends import (
    domestic_withholdings,
    foreign_withholdings,
    total_dividend_income,
)
from degiro_renta.calculation.double_taxation import calculate_foreign_credit
from degiro_renta.calculation.foreign_assets import build_foreign_assets
from degiro_renta.calculation.savings_base import integrate_savings_base
from degiro_renta.calculation.tax import calculate_irpf_quota, total_quota
from degiro_renta.calculation.wash_sale import (
    detect_wash_sales,
    pending_deferrals_at,
    uncovered_windows,
    wash_sale_adjustments,
)
from degiro_renta.domain.constants import DEBT_SECURITY_ISINS
from degiro_renta.domain.currency import CurrencyGain
from degiro_renta.domain.income import DividendIncome
from degiro_renta.domain.money import ZERO, to_cents
from degiro_renta.domain.operations import Sale
from degiro_renta.domain.report import ReportData
from degiro_renta.domain.savings import LossCarryforward, SavingsBase
from degiro_renta.domain.statement import AccountStatement
from degiro_renta.domain.wash_sale import WashSaleResult

# Signed amounts dated on the day they are imputed.
DatedAmounts = list[tuple[date, Decimal]]


def activity_years(sales: list[Sale], statement: AccountStatement) -> list[int]:
    """
    List the exercises in which the statement has any movement.

    Args:
        sales: Sales matched by FIFO.
        statement: Parsed Degiro account statement.

    Returns:
        Sorted exercises with at least one operation, unvalued trade,
        dividend, interest, fee, other income or currency exchange.
    """

    years: set[int] = {sale.date.year for sale in sales}
    years.update(operation.date.year for operation in statement.operations)
    years.update(dividend.date.year for dividend in statement.dividends)
    years.update(day.year for day, _ in statement.interest_entries)
    years.update(day.year for day, _ in statement.connectivity_entries)
    years.update(item.date.year for item in statement.other_income)
    years.update(item.date.year for item in statement.currency_conversions)
    years.update(item.date.year for item in statement.unvalued_operations)

    return sorted(years)


def _sum_entries_of_year(
    entries: tuple[tuple[date, Decimal], ...], year: int
) -> Decimal:
    """
    Add up the signed entries dated in a given exercise.

    Args:
        entries: Pairs of date and amount.
        year: Exercise to add up.

    Returns:
        Sum of the amounts dated in ``year``, in EUR.
    """

    return sum((amount for day, amount in entries if day.year == year), ZERO)


def _split_interest(
    entries: tuple[tuple[date, Decimal], ...], year: int
) -> tuple[Decimal, Decimal]:
    """
    Split the interest rows of an exercise into income and expense.

    Args:
        entries: Pairs of date and signed interest amount.
        year: Exercise to split.

    Returns:
        Credit interest and debit interest, both positive, in EUR.
    """

    income = ZERO
    expense = ZERO

    for day, amount in entries:
        if day.year != year:
            continue
        if amount >= 0:
            income += amount
        else:
            expense += -amount

    return income, expense


def _dividends_of_year(statement: AccountStatement, year: int) -> list[DividendIncome]:
    """
    Dividends of the statement dated in one exercise.

    Args:
        statement: Parsed Degiro account statement.
        year: Exercise to filter.

    Returns:
        Dividends paid in ``year``, in statement order.
    """

    return [dividend for dividend in statement.dividends if dividend.date.year == year]


def _split_results_by_block(
    sales: list[Sale],
    wash_sale: WashSaleResult,
    fx_gains: tuple[CurrencyGain, ...],
) -> tuple[DatedAmounts, DatedAmounts]:
    """
    Sort every result of the statement into its block of the savings base.

    Sales and two-month corrections of the financial assets of art. 25.2
    are capital income; everything else, currency exchanges included, is
    a capital gain or loss.

    Args:
        sales: Sales matched by FIFO.
        wash_sale: Two-month rule over the whole statement.
        fx_gains: Currency gains of the whole statement.

    Returns:
        Dated capital gains and losses, and dated capital income from
        financial assets.
    """

    gains: DatedAmounts = []
    debt: DatedAmounts = []

    for sale in sales:
        target = debt if sale.isin in DEBT_SECURITY_ISINS else gains
        target.append((sale.date, sale.gain_loss))

    for day, isin, amount in wash_sale_adjustments(wash_sale):
        target = debt if isin in DEBT_SECURITY_ISINS else gains
        target.append((day, amount))

    gains.extend((gain.date, gain.gain_eur) for gain in fx_gains)

    return gains, debt


def _totals_by_year(entries: DatedAmounts) -> dict[int, Decimal]:
    """
    Add up dated amounts per calendar year.

    Args:
        entries: Signed amounts with their dates.

    Returns:
        Mapping of year to the sum of its amounts.
    """

    totals: dict[int, Decimal] = defaultdict(lambda: ZERO)

    for day, amount in entries:
        totals[day.year] += amount

    return totals


def _integrate_exercises(  # noqa: PLR0913 - every block art. 49 integrates
    first: int,
    target: int,
    gains: dict[int, Decimal],
    debt: dict[int, Decimal],
    statement: AccountStatement,
) -> tuple[SavingsBase, tuple[LossCarryforward, ...]]:
    """
    Integrate every exercise in order, carrying negative balances forward.

    Args:
        first: First exercise with activity.
        target: Exercise whose savings base is returned.
        gains: Capital gains and losses per year.
        debt: Capital income from financial assets per year.
        statement: Parsed Degiro account statement.

    Returns:
        The savings base of ``target`` and the negative balances still
        pending after it.
    """

    pending: tuple[LossCarryforward, ...] = ()
    savings: SavingsBase | None = None

    for current in range(first, target + 1):
        income, _ = _split_interest(statement.interest_entries, current)
        savings, pending = integrate_savings_base(
            current,
            gains.get(current, ZERO),
            total_dividend_income(_dividends_of_year(statement, current)),
            interest_income=income,
            debt_income=debt.get(current, ZERO),
            pending=pending,
        )

    if savings is None:
        error_message = f"No se pudo calcular el ejercicio {target}."
        raise ValueError(error_message)

    return savings, pending


def build_report_data(
    sales: list[Sale],
    statement: AccountStatement,
    year: int | None = None,
) -> ReportData:
    """
    Compute the fiscal report of one exercise from the whole statement.

    Every exercise from the first one with activity up to the requested
    one is integrated in order, so negative balances of earlier years
    reach the requested one under art. 49 LIRPF. FIFO and the two-month
    rule always run over the full history, because a sale in one
    exercise depends on purchases made in any earlier one.

    Args:
        sales: Sales matched by FIFO over the statement operations.
        statement: Parsed Degiro account statement.
        year: Exercise to report. ``None`` selects the last one with
            activity.

    Returns:
        ``ReportData`` for the exercise, with every field precomputed.

    Raises:
        ValueError: If the requested exercise has no activity.
    """

    years = activity_years(sales, statement)

    if not years:
        return _empty_report()

    target = years[-1] if year is None else year

    if target not in years:
        available = ", ".join(str(item) for item in years)
        error_message = (
            f"No hay actividad en el ejercicio {target}. Ejercicios disponibles: "
            f"{available}."
        )
        raise ValueError(error_message)

    wash_sale = detect_wash_sales(sales, statement.operations)
    fx_gains = calculate_currency_gains(statement.currency_conversions)
    gains, debt = _split_results_by_block(sales, wash_sale, fx_gains)
    savings, pending = _integrate_exercises(
        years[0], target, _totals_by_year(gains), _totals_by_year(debt), statement
    )

    return _build_exercise_report(
        target=target,
        sales=sales,
        statement=statement,
        wash_sale=wash_sale,
        fx_gains=fx_gains,
        savings=savings,
        pending=pending,
    )


def _build_exercise_report(  # noqa: PLR0913 - assembles every block of one exercise
    *,
    target: int,
    sales: list[Sale],
    statement: AccountStatement,
    wash_sale: WashSaleResult,
    fx_gains: tuple[CurrencyGain, ...],
    savings: SavingsBase,
    pending: tuple[LossCarryforward, ...],
) -> ReportData:
    """
    Assemble the report of the requested exercise.

    Args:
        target: Exercise reported.
        sales: Sales matched by FIFO, all exercises.
        statement: Parsed Degiro account statement.
        wash_sale: Two-month rule over the whole statement.
        fx_gains: Currency gains of the whole statement.
        savings: Savings base of the exercise.
        pending: Negative balances pending after the exercise.

    Returns:
        ``ReportData`` of ``target``.
    """

    dividends = _dividends_of_year(statement, target)
    income, expense = _split_interest(statement.interest_entries, target)
    fees = _sum_entries_of_year(statement.connectivity_entries, target)
    sales_year = [sale for sale in sales if sale.date.year == target]
    gain_sales = [s for s in sales_year if s.isin not in DEBT_SECURITY_ISINS]
    fx_gains_year = tuple(gain for gain in fx_gains if gain.date.year == target)

    brackets = calculate_irpf_quota(savings.total) if savings.total > 0 else None
    estimated_quota = total_quota(brackets) if brackets is not None else ZERO
    credit = calculate_foreign_credit(dividends, estimated_quota, savings.total)
    quota_net = estimated_quota - credit.deduction
    domestic = domestic_withholdings(dividends)
    foreign = foreign_withholdings(dividends)

    # Realized result before taxes, then every tax actually paid: the
    # quota after the deduction, plus the foreign withholdings that were
    # never recovered, plus the costs of the account.
    realized = savings.capital_gains + savings.capital_income
    net_return: Decimal | None = None

    if sales_year or dividends or income or expense:
        net_return = to_cents(realized - quota_net - foreign - fees - expense)

    return ReportData(
        sales=gain_sales,
        dividends=dividends,
        savings_base=savings,
        domestic_withholdings=domestic,
        irpf_quota=brackets,
        # Spanish withholdings are refunded even when there is no quota
        # to subtract them from (art. 103 LIRPF).
        quota_to_pay=to_cents(quota_net - domestic),
        connectivity_fees=fees,
        net_return=net_return,
        foreign_withholdings=foreign,
        interest_expense=expense,
        other_income=tuple(
            item for item in statement.other_income if item.date.year == target
        ),
        # Not filtered by year: an unvalued trade excludes the whole
        # history of its ISIN, so every exercise is affected.
        unvalued_operations=statement.unvalued_operations,
        wash_sale=WashSaleResult(
            deferrals=tuple(
                d for d in wash_sale.deferrals if d.transfer_date.year == target
            ),
            releases=tuple(
                r for r in wash_sale.releases if r.release_date.year == target
            ),
            pending=pending_deferrals_at(sales, statement.operations, target),
            uncovered=uncovered_windows(
                sales_year, wash_sale.deferrals, statement.last_date
            ),
        ),
        year=target,
        foreign_deduction=credit.deduction,
        foreign_excess=credit.excess,
        foreign_unused_limit=credit.unused_limit,
        loss_carryforward=pending,
        currency_gains=fx_gains_year,
        debt_sales=[s for s in sales_year if s.isin in DEBT_SECURITY_ISINS],
        unverified_treaty_countries=credit.unverified_countries,
        sales_gain_loss=sum((sale.gain_loss for sale in gain_sales), ZERO),
        wash_sale_adjustment=sum(
            (
                amount
                for day, isin, amount in wash_sale_adjustments(wash_sale)
                if day.year == target and isin not in DEBT_SECURITY_ISINS
            ),
            ZERO,
        ),
        currency_gain_loss=sum((gain.gain_eur for gain in fx_gains_year), ZERO),
        realized_result=realized,
        quota_after_credit=quota_net,
        foreign_assets=build_foreign_assets(statement, target),
    )


def _empty_report() -> ReportData:
    """
    Build the report of a statement with no activity at all.

    Returns:
        ``ReportData`` with zero aggregates and no exercise.
    """

    return ReportData(
        sales=[],
        dividends=[],
        savings_base=SavingsBase(ZERO, ZERO, ZERO, ZERO, ZERO),
        domestic_withholdings=ZERO,
        irpf_quota=None,
        quota_to_pay=None,
        connectivity_fees=ZERO,
        net_return=None,
    )
