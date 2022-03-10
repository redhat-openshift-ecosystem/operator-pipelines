import argparse
import json
import logging
from typing import Any
from urllib.parse import urljoin
from requests.exceptions import HTTPError
from urllib.parse import urlparse

from operatorcert import pyxis
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Cli tool to upload signature to Pyxis"
    )

    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument(
        "--signature-data",
        help="Path to a json file that contains signed content and related metadata",
        required=True,
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def parse_repository_name(pull_spec_reference: str) -> str:
    """
    Parse repository name from container pull spec

    Args:
        pull_spec_reference (str): Container pull specification

    Returns:
        str: Repository name
    """
    pull_spec = pull_spec_reference
    if not pull_spec_reference.startswith("docker://"):
        pull_spec = f"docker://{pull_spec_reference}"
    parsed_reference = urlparse(pull_spec)
    path = parsed_reference.path.lstrip("/")
    if "@" in path:
        return path.split("@")[0]
    if ":" in path:
        return path.split(":")[0]
    return path


def upload_signature(data: Any, pyxis_url: str) -> None:
    """
    Upload signature to Pyxis

    Args:
        data (Any): Signature metadata
        pyxis_url (str): URL of Pyxis instance to upload signature to

    Returns:
        Dict[str, Any]]: Pyxis respones
    """
    payload = {
        "manifest_digest": data["manifest_digest"],
        "reference": data["docker_reference"],
        "repository": parse_repository_name(data["docker_reference"]),
        "sig_key_id": data["sig_key_id"],
        "signature_data": data["signed_claim"],
    }

    try:
        rsp_json = pyxis.post(urljoin(pyxis_url, "v1/signatures"), payload)
        LOGGER.info("Signature successfully created on Pyxis: %s", rsp_json)
    except HTTPError as err:
        if err.response.status_code == 409:
            LOGGER.warning(
                "Pyxis POST request resulted in 409 Conflict Error. Signature may have "
                "already been uploaded previously."
            )
        else:
            raise


def main():  # pragma: no cover
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(log_level)

    with open(args.signature_data, "r") as f:
        signature_data = json.load(f)
    for data in signature_data:
        upload_signature(data, args.pyxis_url)


if __name__ == "__main__":  # pragma: no cover
    main()
