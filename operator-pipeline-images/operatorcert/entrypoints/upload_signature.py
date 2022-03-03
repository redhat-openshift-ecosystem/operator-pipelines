import argparse
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
        "--manifest-digest",
        help="Manifest digest for the signed content, usually in the format sha256:xxx",
        required=True,
    )
    parser.add_argument(
        "--reference",
        help="Docker reference for the signed content, e.g. registry.redhat.io/redhat/community-operator-index:v4.9",
        required=True,
    )
    parser.add_argument(
        "--sig-key-id",
        help="The signing key id that the content was signed with",
        required=True,
    )
    parser.add_argument("--signature-data", help="The signed content", required=True)
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


def upload_signature(args: Any) -> None:
    """
    Upload signature to Pyxis

    Args:
        args (Any): CLI arguments

    Returns:
        Dict[str, Any]]: Pyxis respones
    """
    payload = {
        "manifest_digest": args.manifest_digest,
        "reference": args.reference,
        "repository": parse_repository_name(args.reference),
        "sig_key_id": args.sig_key_id,
        "signature_data": args.signature_data,
    }

    try:
        rsp_json = pyxis.post(urljoin(args.pyxis_url, "v1/signatures"), payload)
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

    upload_signature(args)


if __name__ == "__main__":  # pragma: no cover
    main()
