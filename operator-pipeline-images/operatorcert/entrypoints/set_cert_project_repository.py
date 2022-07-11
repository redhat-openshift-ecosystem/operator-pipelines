"""
Script for setting the cert project status
"""
import argparse
import logging
from datetime import datetime, timezone
from typing import Any
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
        "--registry",
        default="quay.io",
        help="Hostname of the registry where the repository can be accessed (certProject.container.registry)",
    )
    parser.add_argument(
        "--repository",
        required=True,
        help="Path of the repository in the registry (certProject.container.repository)",
    )
    parser.add_argument(
        "--docker-config",
        type=argparse.FileType("r", encoding="UTF-8"),
        required=True,
        help="Path to the docker-config json file (certProject.container.docker_config_json)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def set_cert_project_repository(args: Any) -> None:

    payload = {
        "container": {
            "registry": args.registry,
            "repository": args.repository,
            "docker_config_json": args.docker_config.read(),
        }
    }
    LOGGER.debug(
        "Setting repository info for cert project %s: registry=%s repository=%s",
        args.cert_project_id,
        args.registry,
        args.repository,
    )
    pyxis.patch(
        urljoin(
            args.pyxis_url,
            f"/v1/projects/certification/id/{args.cert_project_id}",
        ),
        payload,
    )
    LOGGER.debug(
        "Repository info for cert project %s successfully updated", args.cert_project_id
    )


def main() -> None:  # pragma: no cover
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    set_cert_project_repository(args)


if __name__ == "__main__":  # pragma: no cover
    main()
