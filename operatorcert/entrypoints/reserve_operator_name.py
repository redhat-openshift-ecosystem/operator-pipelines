import argparse
import logging
import sys
from urllib.parse import urljoin

from operatorcert.pyxis import post_with_cert, get_with_cert

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
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
    parser.add_argument("--source", help="Source of the operator package")
    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com/",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument("--cert-path", help="Path to Pyxis auth cert")
    parser.add_argument("--key-path", help="Path to Pyxis auth key")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def check_operator_name(args) -> None:
    rsp = get_with_cert(
        urljoin(
            args.pyxis_url,
            f"v1/operators/packages?filter=package_name=={args.operator_name}",
        ),
        args.cert_path,
        args.key_path,
    )

    rsp.raise_for_status()

    packages = rsp.json().get("data")

    if packages:
        # package names are unique, so there should only be 1
        package = packages[0]
        if package["association"] != args.association:
            LOGGER.error(
                f"Operator name {args.operator_name} is already taken by another "
                f"association."
            )
            sys.exit(1)
        else:
            LOGGER.info(
                f"Operator name {args.operator_name} is already reserved by this "
                f"association ({args.association})."
            )
            sys.exit(0)
    else:
        LOGGER.info(f"Operator name {args.operator_name} is available.")


def reserve_operator_name(args) -> None:
    post_data = {
        "association": args.association,
        "package_name": args.operator_name,
        "source": args.source,
    }
    post_with_cert(
        urljoin(args.pyxis_url, "v1/operators/packages"),
        post_data,
        args.cert_path,
        args.key_path,
    )

    LOGGER.info(
        f"Operator name {args.operator_name} successfully reserved by "
        f"{args.association}"
    )


def main() -> None:
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    logging.basicConfig(level=log_level)

    check_operator_name(args)
    reserve_operator_name(args)


if __name__ == "__main__":
    main()
