import argparse
import json
import logging
import pathlib
import sys

from operatorcert import ocp_version_info
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Determines the OCP version under test."
    )
    parser.add_argument("bundle_path", help="Location of operator bundle")
    parser.add_argument(
        "organization",
        choices=("certified-operators", "redhat-marketplace"),
        help="Location of operator bundle",
    )
    parser.add_argument(
        "--pyxis-url",
        default="https://catalog.redhat.com/api/containers/",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument(
        "--output-file",
        help="Path to a json file where ocp version will be stored",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def main() -> None:
    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level, log_format="%(message)s")

    bundle_path = pathlib.Path(args.bundle_path)
    version_info = ocp_version_info(bundle_path, args.pyxis_url, args.organization)

    LOGGER.info(json.dumps(version_info))

    if args.output_file:
        with open(args.output_file, "w") as output_file:
            json.dump(version_info, output_file)


if __name__ == "__main__":  # pragma: no cover
    main()
