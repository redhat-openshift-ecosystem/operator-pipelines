"""
IIB module for building a file based catalog for a bundle
"""

import argparse
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from operatorcert import iib, utils
from operatorcert.logger import setup_logger
from operatorcert.utils import SplitArgs

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Add FBC fragment to index")
    parser.add_argument(
        "--iib-url",
        default="https://iib.engineering.redhat.com",
        help="Base URL for IIB API",
    )
    parser.add_argument(
        "--indices",
        required=True,
        nargs="+",
        help="List of indices the bundle supports, e.g --indices registry/index:v4.9 "
        "registry/index:v4.8",
    )
    parser.add_argument(
        "--catalog-names",
        default=[],
        action=SplitArgs,
        help="List of catalog names to build fragment images for",
    )
    parser.add_argument(
        "--image-repository",
        required=True,
        help="Registry and repository where the fragment images are stored "
        "and where the index image will be pushed",
    )
    parser.add_argument(
        "--commit-sha",
        default="",
        help="A part of tag suffix for obtaining the fragment images and to append "
        "to the index image when copying to the destination.",
    )
    parser.add_argument(
        "--image-output",
        default="index-image-paths.txt",
        help="File name to output comma-separated list of temporary location of the "
        "unpublished index images built by IIB.",
    )
    parser.add_argument("--authfile", help="")

    parser.add_argument(
        "--hosted",
        action="store_true",
        help="Wether the pipeline is hosted or not.",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def wait_for_results(
    iib_url: str, request_ids: List[int], timeout: float = 60 * 60, delay: float = 20
) -> Any:
    """
    Wait for IIB build till it finishes

    Args:
        iib_url (Any): CLI arguments
        request_ids (List[int]): IIB identifiers
        timeout ([type], optional): Maximum wait time. Defaults to 60*60 (3600 seconds/1 hour)
        delay (int, optional): Delay between build pollin. Defaults to 20.

    Returns:
        Any: Build response
    """

    start_time = datetime.now()

    while True:
        if datetime.now() - start_time > timedelta(seconds=timeout):
            LOGGER.error(
                "Timeout: Waiting for all IIB add fragments failed: %s.", request_ids
            )
            break
        responses = []
        # gather responses for all add fragment requests
        for request_id in request_ids:
            responses.append(iib.get_build(iib_url, request_id))

        # all builds have completed
        if all(build.get("state") == "complete" for build in responses):
            LOGGER.info(
                "IIB build completed successfully for all fragments add: %s",
                request_ids,
            )
            return responses
        # any have failed
        if any(build.get("state") == "failed" for build in responses):
            for build in responses:
                if build.get("state") == "failed":
                    reason = build.get("state_reason")
                    LOGGER.error(
                        "IIB add fragment %s failed with reason: %s",
                        build["id"],
                        reason,
                    )
            return responses

        LOGGER.debug("Waiting for all IIB add fragment requests to finish.")
        LOGGER.debug("Current states [request id - state]:")
        for build in responses:
            LOGGER.debug("%s - %s", build["id"], build["state"])

        time.sleep(delay)

    return None


def map_index_to_fragment(
    indices: List[str],
    catalog_names: List[str],
    image_repository: str,
    commit_sha: str,
) -> List[Tuple[str, str]]:
    """
    Map indices to fragments for updated catalogs

    Args:
        indices (List[str]): list of original indices
        catalog_names (List[str]): List of catalog names to build fragment images for
        image_repository (str): Registry and repository where the fragment images are stored
        commit_sha (str): A tag suffix for obtaining the fragment images

    Returns:
        List[Tuple[str, str]]: List of tuples with index and fragment
    Raises:
        Exception: Exception is raised when there is no fragment image matching supported index
    """

    indices_dict = {index.split(":")[-1]: index for index in indices}
    fragments_dict = {
        catalog: f"{image_repository}:{catalog}-fragment-{commit_sha}"
        for catalog in catalog_names
    }

    index_fragment_mapping = []
    for key in fragments_dict.keys():
        if key in indices_dict:
            index_fragment_mapping.append((indices_dict[key], fragments_dict[key]))
        else:
            LOGGER.warning("Index not found for catalog %s fragment", key)

    if not index_fragment_mapping:
        raise RuntimeError("There is no fragment image matching supported index.")

    return index_fragment_mapping


def add_fbc_fragment_to_index(
    iib_url: str,
    index_fragment_mapping: List[Tuple[str, str]],
    image_output: str,
) -> Any:
    """
    Add a fragment image to index image using IIB

    Args:
        iib_url (str): url of IIB instance
        index_fragment_mapping (List[Tuple[str, str]]): List of tuples with index and fragment
        image_output (str): file name to output the location of the newly built images to
    Returns:
        List[Any]: Build responses
    Raises:
        Exception: Exception is raised when IIB build fails
    """

    request_ids = []
    for index, fragment in index_fragment_mapping:
        payload = {
            "from_index": index,
            "fbc_fragment": fragment,
        }
        resp = iib.add_fbc_build(iib_url, payload)
        request_ids.append(resp["id"])

    responses = wait_for_results(iib_url, request_ids)

    if responses is None or not all(
        response.get("state") == "complete" for response in responses
    ):
        raise RuntimeError("IIB build failed")

    output_index_image_paths(image_output, responses)

    return responses


def output_index_image_paths(
    image_output: str,
    responses: List[Dict[str, Any]],
) -> None:
    """
    Extract the paths of the from_index and the newly built images.
    Args:
        image_output: file name to output the image paths to
        responses: Responses from IIB after the add fragment is finished
    """
    LOGGER.info("Extracting manifest digests for signing...")
    index_images = []

    for resp in responses:
        # Use the original from_index for signing
        index_images.append(f"{resp['from_index']}+{resp['index_image_resolved']}")

    with open(image_output, "w", encoding="utf-8") as output_file:
        output_file.write(",".join(index_images))
    LOGGER.info("Index image paths written to output file %s.", image_output)


def main() -> None:
    """
    Main function for adding FBC fragments to index
    """
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    utils.set_client_keytab(os.environ.get("KRB_KEYTAB_FILE", "/etc/krb5.krb"))

    index_fragment_mapping = map_index_to_fragment(
        args.indices,
        args.catalog_names,
        args.image_repository,
        args.commit_sha,
    )

    iib_responses = add_fbc_fragment_to_index(
        args.iib_url,
        index_fragment_mapping,
        args.image_output,
    )
    if args.hosted:
        utils.copy_images_to_destination(
            iib_responses,
            args.image_repository,
            args.commit_sha,
            args.authfile,
        )


if __name__ == "__main__":  # pragma: no cover
    main()
