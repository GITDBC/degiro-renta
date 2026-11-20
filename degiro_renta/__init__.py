# Standard libraries
import importlib.metadata

# Own modules
from degiro_renta.calculation.fifo import calculate_fifo
from degiro_renta.calculation.report_data import build_report_data
from degiro_renta.parsing import parse_account_xlsx
from degiro_renta.reporting import print_report

__version__: str = importlib.metadata.version("degiro_renta")

__all__: list[str] = [
    "__version__",
    "build_report_data",
    "calculate_fifo",
    "parse_account_xlsx",
    "print_report",
]
