import argparse
import json
import logging
import pathlib
import sys

from operatorcert import ocp_version_info


def setup_argparser() -> argparse.ArgumentParser:
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

    return parser


def main() -> None:
    logging.basicConfig(stream=sys.stdout, level="INFO", format="%(message)s")

    parser = setup_argparser()
    args = parser.parse_args()

    bundle_path = pathlib.Path(args.bundle_path)
    version_info = ocp_version_info(bundle_path, args.pyxis_url, args.organization)
    logging.info(json.dumps(version_info))


if __name__ == "__main__":
    main()
