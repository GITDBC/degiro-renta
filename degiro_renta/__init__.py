# Standard libraries
import importlib.metadata

# Own modules
from degiro_renta.calculation.fifo import calculate_fifo
from degiro_renta.calculation.report_data import build_report_data
from degiro_renta.calculation.savings_base import compute_savings_base
from degiro_renta.calculation.tax import SAVINGS_BRACKETS, calculate_irpf_quota
from degiro_renta.calculation.yearly import compute_yearly_results
from degiro_renta.domain.models import (
    AccountStatement,
    AcquisitionMatch,
    DividendIncome,
    Lot,
    Operation,
    OperationType,
    ReportData,
    Sale,
    SavingsBase,
    TaxBracket,
    YearlyResult,
)
from degiro_renta.parsing import parse_account_xlsx
from degiro_renta.reporting import print_report

__version__: str = importlib.metadata.version("degiro_renta")

__all__: list[str] = [
    "AccountStatement",
    "AcquisitionMatch",
    "DividendIncome",
    "Lot",
    "Operation",
    "OperationType",
    "ReportData",
    "SAVINGS_BRACKETS",
    "Sale",
    "SavingsBase",
    "TaxBracket",
    "YearlyResult",
    "__version__",
    "build_report_data",
    "calculate_fifo",
    "calculate_irpf_quota",
    "compute_savings_base",
    "compute_yearly_results",
    "parse_account_xlsx",
    "print_report",
]
