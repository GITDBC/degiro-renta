# Standard libraries
import argparse
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

# Own modules
from degiro_renta import __version__
from degiro_renta.calculation.fifo import calculate_fifo
from degiro_renta.calculation.report_data import activity_years, build_report_data
from degiro_renta.parsing import parse_account_xlsx
from degiro_renta.reporting import print_report
from degiro_renta.reporting.helpers import Notice

# Logger every module of the package logs under.
PACKAGE_LOGGER: Final[str] = "degiro_renta"

# Heading the warnings about the statement are listed under.
STATEMENT_CATEGORY: Final[str] = "Extracto"


class _RecordCollector(logging.Handler):
    """
    Logging handler that keeps the warnings instead of printing them.

    Anything below a warning is handed to the root logger untouched, so
    collecting the warnings does not silence the rest of the log.

    Attributes:
        records: Warnings and errors received, in order.
    """

    def __init__(self) -> None:
        """
        Start with no record kept.

        Returns:
            None.
        """

        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """
        Keep a warning or an error, pass anything else on.

        Args:
            record: Record emitted by the package.

        Returns:
            None.
        """

        if record.levelno >= logging.WARNING:
            self.records.append(record)
        else:
            logging.getLogger().handle(record)


@contextmanager
def collect_notices() -> Iterator[list[Notice]]:
    """
    Divert the warnings of the package so the report can show them.

    They are not printed to stderr meanwhile: they travel with the
    report, under its title. If the run fails midway they are logged as
    usual, so none is lost. The logger is left as it was found.

    Yields:
        The notices, filled in once the block ends without error.
    """

    package = logging.getLogger(PACKAGE_LOGGER)
    collector = _RecordCollector()
    notices: list[Notice] = []
    propagate = package.propagate
    failed = False

    package.addHandler(collector)
    package.propagate = False

    try:
        yield notices

    except BaseException:
        failed = True
        raise

    finally:
        package.removeHandler(collector)
        package.propagate = propagate

        if failed:
            for record in collector.records:
                package.handle(record)

    notices.extend(
        Notice(
            record.getMessage(),
            STATEMENT_CATEGORY,
            severe=record.levelno >= logging.ERROR,
        )
        for record in collector.records
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build the CLI argument parser.

    Returns:
        Configured ArgumentParser instance.
    """

    parser = argparse.ArgumentParser(
        prog="degiro-renta",
        description="Informe fiscal IRPF a partir del extracto de Degiro.",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    sub = parser.add_subparsers(dest="command")

    tax_p = sub.add_parser(
        "tax",
        help="Calcula la base del ahorro del IRPF de un ejercicio.",
    )
    tax_p.add_argument(
        "account_path",
        type=Path,
        help="Ruta al XLSX de Estado de cuenta (Account.xlsx).",
    )
    tax_p.add_argument(
        "--year",
        type=int,
        default=None,
        help="Ejercicio a calcular. Por defecto, el último con actividad.",
    )

    years_p = sub.add_parser(
        "years",
        help="Lista los ejercicios con actividad en el extracto.",
    )
    years_p.add_argument(
        "account_path",
        type=Path,
        help="Ruta al XLSX de Estado de cuenta (Account.xlsx).",
    )

    return parser


def run_tax(args: argparse.Namespace) -> None:
    """
    Execute the IRPF tax calculation flow.

    Parses the Degiro Account.xlsx, applies FIFO matching to the trades
    and builds the savings base of the exercise: capital gains and
    losses, dividends, interest and financial assets, with the two-month
    rule and the currency exchanges applied. Whatever cannot be
    integrated (promotions, trades with no euro value, unrecognized
    rows) is reported, so no row is dropped in silence. The aggregates
    themselves live in ``calculation.build_report_data``, which is what
    keeps them independent of how the report is rendered.

    Args:
        args: Parsed CLI arguments with account_path and year.

    Returns:
        None.
    """

    with collect_notices() as notices:
        statement = parse_account_xlsx(args.account_path)
        sales, _ = calculate_fifo(statement.operations)
        data = build_report_data(sales, statement, year=args.year)

    print_report(data, notices=notices)


def run_years(args: argparse.Namespace) -> None:
    """
    List the exercises that the statement covers, one per line.

    Args:
        args: Parsed CLI arguments with account_path.

    Returns:
        None.
    """

    statement = parse_account_xlsx(args.account_path)
    sales, _ = calculate_fifo(statement.operations)
    years = activity_years(sales, statement)

    if not years:
        print("El extracto no tiene actividad.")
        return

    for year in years:
        print(year)

    print(f"Por defecto se calcula el último: {years[-1]}.")


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Parses arguments, runs the selected subcommand and returns an
    integer exit code. Errors go to stderr. The warnings of ``tax`` are
    shown under the title of the report; those of ``years``, or of a run
    that fails, go to stderr too, so the tables stay readable on stdout.

    Args:
        argv: Arguments list (optional, for testing). Uses sys.argv
            if None.

    Returns:
        Exit code: 0 success, 1 error, 130 keyboard interrupt.
    """

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Whatever the package logs outside a report goes to stderr.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        if args.command == "years":
            run_years(args)
        else:
            run_tax(args)

    except KeyboardInterrupt:
        return 130

    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    return 0
