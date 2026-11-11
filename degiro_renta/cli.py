# Standard libraries
import argparse
import logging
import sys
from pathlib import Path

# Own modules
from degiro_renta import __version__
from degiro_renta.calculation.fifo import calculate_fifo
from degiro_renta.calculation.report_data import build_report_data
from degiro_renta.parsing import parse_account_xlsx
from degiro_renta.reporting import print_report


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
        help="Calcula ganancias/pérdidas patrimoniales IRPF.",
    )
    tax_p.add_argument(
        "account_path",
        type=Path,
        help="Ruta al XLSX de Estado de cuenta (Account.xlsx).",
    )

    return parser


def run_tax(args: argparse.Namespace) -> None:
    """
    Execute the IRPF tax calculation flow.

    Parses the Degiro Account.xlsx, applies FIFO matching to the trades
    and integrates the dividends collected into the same savings base.
    Everything else the statement carries (interest, promotions,
    currency swaps, trades with no euro value) travels with it, so no
    row is dropped without the report saying so. The aggregates
    themselves live in ``calculation.build_report_data``, which is what
    keeps them independent of how the report is rendered.

    Args:
        args: Parsed CLI arguments with account_path.

    Returns:
        None.
    """

    statement = parse_account_xlsx(args.account_path)
    sales, lots = calculate_fifo(statement.operations)

    print_report(build_report_data(sales, lots, statement))


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Parses arguments, runs the tax command and returns an integer exit
    code. Errors, logs and warnings go to stderr, so the tables stay
    readable on stdout.

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

    # Warnings about statement rows that fit no concept go to stderr.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        run_tax(args)

    except KeyboardInterrupt:
        return 130

    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    return 0
