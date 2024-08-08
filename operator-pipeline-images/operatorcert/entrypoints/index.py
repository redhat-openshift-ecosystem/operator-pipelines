"""
IIB module for building a index images for a bundle
"""

import argparse
import logging
import os
from typing import Any, Dict, List

from operatorcert import iib, utils
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Add bundle to index image")
    parser.add_argument(
        "--bundle-pullspec", required=True, help="Operator bundle pullspec"
    )
    parser.add_argument(
        "--indices",
        required=True,
        nargs="+",
        help="List of indices the bundle supports, e.g --indices registry/index:v4.9 "
        "registry/index:v4.8",
    )
    parser.add_argument(
        "--image-output",
        default="index-image-paths.txt",
        help="File name to output comma-separated list of temporary location of the "
        "unpublished index images built by IIB.",
    )
    parser.add_argument(
        "--iib-url",
        default="https://iib.engineering.redhat.com",
        help="Base URL for IIB API",
    )
    parser.add_argument(
        "--index-image-destination",
        help="A location of a destination registry to copy the index images to.",
    )
    parser.add_argument(
        "--index-image-destination-tag-suffix",
        default="",
        help="A tag suffix to append to the index image when copying to the destination.",
    )
    parser.add_argument(
        "--mode",
        choices=["replaces", "semver", "semver-skippatch"],
        default=None,
        help="A graph update mode that defines how channel graphs are updated.",
    )
    parser.add_argument("--authfile", help="")

    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def add_bundle_to_index(
    bundle_pullspec: str,
    iib_url: str,
    indices: List[str],
    image_output: str,
    mode: str,
) -> Any:
    """
    Add a bundle to index image using IIB

    Args:
        bundle_pullspec (str): bundle pullspec
        iib_url (str): url of IIB instance
        indices (List[str]): list of original indices
        image_output (str): file name to output the location of the newly built images to
        mode (str): A mode that defines how the update graph will be updated
    Returns:
        Any: Build response
    Raises:
        Exception: Exception is raised when IIB build fails
    """

    payload: Dict[str, Any] = {"build_requests": []}

    for index in indices:
        build_request = {
            "from_index": index,
            "bundles": [bundle_pullspec],
            "add_arches": ["amd64", "s390x", "ppc64le"],
        }
        if mode:
            build_request["graph_update_mode"] = mode
        payload["build_requests"].append(build_request)

    resp = iib.add_builds(iib_url, payload)

    batch_id = resp[0]["batch"]
    response = iib.wait_for_batch_results(iib_url, batch_id)
    if response is None or not all(
        build.get("state") == "complete" for build in response["items"]
    ):
        raise RuntimeError("IIB build failed")

    output_index_image_paths(image_output, response)

    return response


def output_index_image_paths(
    image_output: str,
    response: Dict[str, Any],
) -> None:
    """
    Extract the paths of the from_index and the newly built images.
    Args:
        image_output: file name to output the image paths to
        response: Response from IIB after the build is finished
    """
    LOGGER.info("Extracting manifest digests for signing...")
    index_images = []

    for build in response["items"]:
        # The original from_index is used for signing
        index_images.append(f"{build['from_index']}+{build['index_image_resolved']}")

    with open(image_output, "w", encoding="utf-8") as output_file:
        output_file.write(",".join(index_images))
    LOGGER.info("Index image paths written to output file %s.", image_output)


def main() -> None:  # pragma: no cover
    """
    Main function
    """
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    utils.set_client_keytab(os.environ.get("KRB_KEYTAB_FILE", "/etc/krb5.krb"))

    iib_response = add_bundle_to_index(
        args.bundle_pullspec,
        args.iib_url,
        args.indices,
        args.image_output,
        args.mode,
    )
    if args.index_image_destination:
        utils.copy_images_to_destination(
            iib_response.get("items", []),
            args.index_image_destination,
            args.index_image_destination_tag_suffix,
            args.authfile,
        )


if __name__ == "__main__":  # pragma: no cover
    main()
