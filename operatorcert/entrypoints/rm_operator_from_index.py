"""
IIB module for removing operators from an index images
"""

import argparse
import logging
import os
from typing import Any, Dict, List, Optional

from operatorcert import iib, utils
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Remove operator to index image")
    parser.add_argument(
        "--rm-catalog-operators",
        required=True,
        help="Operators to remove from the index",
    )
    parser.add_argument(
        "--indices",
        required=True,
        nargs="+",
        help="List of indices the bundle supports, e.g --indices registry/index:v4.9 "
        "registry/index:v4.8",
    )
    parser.add_argument(
        "--fragment-builds-output",
        help="Path to a text file where results from fragment builds will be stored",
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

    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


class IndexImage:
    """
    A data class for an index image
    """

    def __init__(self, index_image: str, iib_build_image: Optional[str] = None):
        self.index_image = index_image
        self.iib_build_image = iib_build_image

        self.version = index_image.split(":")[-1]

        self.operators_to_remove: List[str] = []

    def __str__(self) -> str:
        """
        String representation of the index image

        Returns:
            str: A string representation of the index image
        """
        return f"{self.version} - {self.index_image}+{self.iib_build_image}"

    def __repr__(self) -> str:
        """
        String representation of the index image

        Returns:
            str: A string representation of the index image
        """
        return f"[{self.__class__.__name__}] {self.__str__()}"

    def index_pullspec(self) -> str:
        """
        Decide which pullspec to use for the index image based
        on whether IIb build exists

        Returns:
            str: A pullspec of the index image
        """

        return self.iib_build_image if self.iib_build_image else self.index_image

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, IndexImage)
            and value.index_image == self.index_image
            and value.iib_build_image == self.iib_build_image
        )


def rm_operator_from_index(
    index_images: List[IndexImage],
    iib_url: str,
) -> Any:
    """
    Submit a batch build request to IIB to remove operators from the index images.

    Args:
        index_images (List[IndexImage]): List of index images objects
        iib_url (str): IIb API URL

    Returns:
        Any: IIB batch build response
    """
    payload: Dict[str, Any] = {"build_requests": []}
    for index_image in index_images:
        if not index_image.operators_to_remove:
            continue

        build_request = {
            "from_index": index_image.index_pullspec(),
            "operators": index_image.operators_to_remove,
        }
        payload["build_requests"].append(build_request)

    resp = iib.add_builds(iib_url, payload)

    batch_id = resp[0]["batch"]
    response = iib.wait_for_batch_results(iib_url, batch_id)
    if response is None or not all(
        build.get("state") == "complete" for build in response["items"]
    ):
        raise RuntimeError("IIB build failed")

    return response


def all_index_images(indices: List[str], fragment_builds: str) -> List[IndexImage]:
    """
    Create a list of index images based on the list of indices and fragment builds.
    The priority is given to the fragment builds. In case a fragment build exists for
    given version it is used. Otherwise, the official index image is used.

    Args:
        indices (List[str]): List of official index images
        fragment_builds (str): A string with fragment builds in the format
        of "index+image" separated by commas

    Returns:
        List[IndexImage]: A list of index images objects
    """
    index_images = []
    versions = []

    if fragment_builds:
        for fragments in fragment_builds.split(","):
            index, iib_build_image = fragments.split("+")
            index_image = IndexImage(index, iib_build_image)
            if index_image.version not in versions:
                versions.append(index_image.version)
                index_images.append(index_image)
    for index in indices:
        index_image = IndexImage(index)
        if index_image.version not in versions:
            # In case no fragment build exists for the version,
            # use the official index
            versions.append(index_image.version)
            index_images.append(IndexImage(index))

    index_images.sort(key=lambda x: x.version)
    return index_images


def find_index_by_version(
    version: str, index_images: List[IndexImage]
) -> Optional[IndexImage]:
    """
    Find index image by version from the list of index images

    Args:
        version (str): A version of the index image that should be found
        index_images (List[IndexImage]): List of index images objects

    Returns:
        Optional[IndexImage]: An index image object if found, otherwise None
    """
    for index_image in index_images:
        if index_image.version == version:
            return index_image
    return None


def map_operators_to_indices(
    operators_to_remove: str, index_images: List[IndexImage]
) -> None:
    """
    Map operators to be removed to the index images based on a version

    Args:
        operators_to_remove (str): Operators to be removed in the format of
        "version/operator" separated by commas
        index_images (List[IndexImage]): List of index images objects

    """

    for catalog_operators in operators_to_remove.split(","):
        catalog_version, operator_name = catalog_operators.split("/")

        index_image = find_index_by_version(catalog_version, index_images)
        if not index_image:
            LOGGER.error("Index image not found for version %s", catalog_version)
            continue
        index_image.operators_to_remove.append(operator_name)


def merge_rm_output_with_fbc_output(
    index_images: List[IndexImage], iib_rm_response: Any
) -> None:
    """
    Assign the IIB build image to the index image after a successful removal process

    Args:
        index_images (List[IndexImage]): List of all index images
        iib_rm_response (Any): IIB batch build response
    """
    for build in iib_rm_response["items"]:
        from_index = build["from_index"]
        for index_image in index_images:
            if index_image.index_pullspec() == from_index:
                # Find IIB build image for the index image and assign it to
                # the index image
                index_image.iib_build_image = build["index_image_resolved"]
                break


def save_output_to_file(index_images: List[IndexImage], image_output: str) -> None:
    """
    Save output of the index images list to a file

    The index images are saved in the format of "index_image+iib_build_image"
    separated by commas.

    Args:
        index_images (List[IndexImage]): List of index images objects to be
        stored in output file
        image_output (str): An output file name
    """
    LOGGER.info("Extracting manifest digests for signing...")
    output_index_images = []

    for index_image in index_images:
        output_index_images.append(
            f"{index_image.index_image}+{index_image.iib_build_image}"
        )

    with open(image_output, "w", encoding="utf-8") as output_file:
        output_file.write(",".join(output_index_images))
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

    # In case there was a previous run of fragment builds, read the output and use
    # it as a base for removal process. In case the file does not exist, set it to
    # an empty string.
    if not os.path.exists(args.fragment_builds_output):
        fragment_builds = ""
    else:
        with open(args.fragment_builds_output, "r", encoding="utf-8") as fragment_file:
            fragment_builds = fragment_file.read().strip()

    LOGGER.info("Fragment builds: %s", fragment_builds)

    # Merge official index supported images with the ones built by
    # IIB in the previous step
    index_images = all_index_images(args.indices, fragment_builds)

    # Map operators to be removed to the index images
    map_operators_to_indices(args.rm_catalog_operators, index_images)

    # Remove operators from the index images using IIB API
    iib_rm_response = rm_operator_from_index(index_images, args.iib_url)

    # Merge the output from the removal process with the output from the
    # fragment builds and use only the images that were built by IIB
    merge_rm_output_with_fbc_output(index_images, iib_rm_response)
    updated_index_images = [index for index in index_images if index.iib_build_image]

    if args.image_output:
        save_output_to_file(updated_index_images, args.image_output)


if __name__ == "__main__":  # pragma: no cover
    main()
