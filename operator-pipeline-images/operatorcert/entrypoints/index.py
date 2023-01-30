import argparse
import logging
import os
import time
from datetime import datetime, timedelta
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
        help="List of indices the bundle supports, e.g --indices registry/index:v4.9 registry/index:v4.8",
    )
    parser.add_argument(
        "--image-output",
        default="index-image-paths.txt",
        help="File name to output comma-separated list of temporary location of the unpublished index images built by IIB.",
    )
    parser.add_argument(
        "--iib-url",
        default="https://iib.engineering.redhat.com",
        help="Base URL for IIB API",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def wait_for_results(iib_url: str, batch_id: int, timeout=60 * 60, delay=20) -> Any:
    """
    Wait for IIB build till it finishes

    Args:
        iib_url (Any): CLI arguments
        batch_id (int): IIB batch identifier
        timeout ([type], optional): Maximum wait time. Defaults to 60*60 (3600 seconds/1 hour)
        delay (int, optional): Delay between build pollin. Defaults to 20.

    Returns:
        Any: Build response
    """
    start_time = datetime.now()
    loop = True

    while loop:
        response = iib.get_builds(iib_url, batch_id)

        builds = response["items"]

        # all builds have completed
        if all([build.get("state") == "complete" for build in builds]):
            LOGGER.info(f"IIB batch build completed successfully: {batch_id}")
            return response
        # any have failed
        elif any([build.get("state") == "failed" for build in builds]):
            for build in builds:
                if build.get("state") == "failed":
                    LOGGER.error(f"IIB build failed: {build['id']}")
                    reason = build.get("state_reason")
                    LOGGER.info(f"Reason: {reason}")
            return response

        LOGGER.debug(f"Waiting for IIB batch build: {batch_id}")
        LOGGER.debug("Current states [build id - state]:")
        for build in builds:
            LOGGER.debug(f"{build['id']} - {build['state']}")

        if datetime.now() - start_time > timedelta(seconds=timeout):
            LOGGER.error(f"Timeout: Waiting for IIB batch build failed: {batch_id}.")
            break

        LOGGER.info(f"Waiting for IIB batch build to finish: {batch_id}")
        time.sleep(delay)
    return None


def add_bundle_to_index(
    bundle_pullspec: str,
    iib_url: str,
    indices: List[str],
    image_output: str,
) -> None:
    """
    Add a bundle to index image using IIB

    Args:
        bundle_pullspec: bundle pullspec
        iib_url: url of IIB instance
        indices: list of original indices
        image_output: file name to output the location of the newly built images to
    Raises:
        Exception: Exception is raised when IIB build fails
    """

    payload = {"build_requests": []}

    for index in indices:
        payload["build_requests"].append(
            {
                "from_index": index,
                "bundles": [bundle_pullspec],
                "add_arches": ["amd64", "s390x", "ppc64le"],
            }
        )

    resp = iib.add_builds(iib_url, payload)

    batch_id = resp[0]["batch"]
    response = wait_for_results(iib_url, batch_id)
    if response is None or not all(
        [build.get("state") == "complete" for build in response["items"]]
    ):
        raise Exception("IIB build failed")
    else:
        output_index_image_paths(image_output, response)


def output_index_image_paths(
    image_output: str,
    response: Dict[str, Any],
):
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

    with open(image_output, "w") as f:
        f.write(",".join(index_images))
    LOGGER.info(f"Index image paths written to output file {image_output}.")


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

    add_bundle_to_index(
        args.bundle_pullspec,
        args.iib_url,
        args.indices,
        args.image_output,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
