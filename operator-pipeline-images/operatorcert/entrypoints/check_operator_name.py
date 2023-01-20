import argparse
import logging
import sys
from urllib.parse import urljoin

from operatorcert import pyxis
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Reserve the given operator package name"
    )
    parser.add_argument("--association", help="Association of the operator package")
    parser.add_argument("--operator-name", help="Unique name of the operator package")
    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com/",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def check_operator_name(args) -> None:
    rsp = pyxis.get(
        urljoin(
            args.pyxis_url,
            f"v1/operators/packages?filter=association=={args.association}",
        )
    )

    rsp.raise_for_status()

    packages = rsp.json().get("data")

    if packages:
        # there should only be 1 package for given association/isv_pid
        package = packages[0]
        if package["package_name"] != args.operator_name:
            LOGGER.error(
                f"There is already different operator name ({package['package_name']}) "
                f"reserved for association {args.association}."
            )
            sys.exit(1)
        else:
            LOGGER.info(
                f"Association ({args.association}) has already correct "
                f"operator name ({args.operator_name}) registered."
            )
    else:
        LOGGER.info(
            f"There isn't operator name registered for association {args.association}."
        )


def main() -> None:  # pragma: no cover
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    check_operator_name(args)


if __name__ == "__main__":  # pragma: no cover
    main()
