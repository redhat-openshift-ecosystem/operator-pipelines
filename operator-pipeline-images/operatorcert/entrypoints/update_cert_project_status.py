"""
Script for updating the cert project status
"""
import argparse
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from operatorcert import pyxis
from operatorcert.logger import setup_logger
from operatorcert.utils import store_results

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Get the Certification Project Status")
    parser.add_argument(
        "--cert-project-id",
        help="Identifier of certification project from Red Hat Connect",
    )
    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com/",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument(
        "--certification-status",
        choices=("In Progress", "Published"),
        required=True,
        help="certProject data field certification_status value",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def update_cert_project_status(args: Any) -> None:
    payload = {
        "certification_status": args.certification_status,
        "certification_date": datetime.now(timezone.utc).isoformat(),
    }
    rsp = pyxis.patch(
        urljoin(
            args.pyxis_url,
            f"/v1/projects/certification/id/{args.cert_project_id}",
        ),
        payload,
    )

    cert_project = rsp

    store_results({"cert_project": cert_project})


def main() -> None:  # pragma: no cover
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    update_cert_project_status(args)


if __name__ == "__main__":  # pragma: no cover
    main()
