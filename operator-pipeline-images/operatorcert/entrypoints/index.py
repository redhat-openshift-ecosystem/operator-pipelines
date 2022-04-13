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
    parser = argparse.ArgumentParser(description="Publish bundle to index image")
    parser.add_argument(
        "--bundle-pullspec", required=True, help="Operator bundle pullspec"
    )
    parser.add_argument(
        "--from-index", required=True, help="Base index pullspec (without tag)"
    )
    parser.add_argument(
        "--indices",
        required=True,
        nargs="+",
        help="List of indices the bundle supports, e.g --indices registry/index:v4.9 registry/index:v4.8",
    )
    parser.add_argument(
        "--output",
        default="manifest-digests.txt",
        help="File name to output comma-separated list of manifest digests to.",
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
                LOGGER.error(f"IIB build failed: {build['id']}")
                state_history = build.get("state_history", [])
                if state_history:
                    reason = state_history[0].get("state_reason")
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


def publish_bundle(
    from_index: str,
    bundle_pullspec: str,
    iib_url: str,
    indices: List[str],
    output: str,
) -> None:
    """
    Publish a bundle to index image using IIB

    Args:
        iib_url: url of IIB instance
        bundle_pullspec: bundle pullspec
        from_index: target index pullspec
        indices: list of original indices
        output: file name to output resulting manifest digests to
    Raises:
        Exception: Exception is raised when IIB build fails
    """

    user = os.getenv("QUAY_USER")
    token = os.getenv("QUAY_TOKEN")

    payload = {"build_requests": []}

    index_versions = parse_indices(indices)
    for version in index_versions:
        payload["build_requests"].append(
            {
                "from_index": f"{from_index}:{version}",
                "bundles": [bundle_pullspec],
                "overwrite_from_index": True,
                "add_arches": ["amd64", "s390x", "ppc64le"],
                "overwrite_from_index_token": f"{user}:{token}",
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
        extract_manifest_digests(indices, index_versions, output, response)


def extract_manifest_digests(
    indices: List[str],
    index_versions: List[str],
    output: str,
    response: Dict[str, Any],
):

    LOGGER.info("Extracting manifest digests for signing...")
    manifest_digests = []
    # go through each version to ensure order is the same as the indices list
    for i in range(0, len(index_versions)):
        index = indices[i]
        version = index_versions[i]
        for build in response["items"]:
            if build["index_image"].endswith(version):
                digest = build["index_image_resolved"].split("@")[-1]
                manifest_digests.append(f"{index}@{digest}")
    with open(output, "w") as f:
        f.write(",".join(manifest_digests))
    LOGGER.info(f"Manifest digests written to output file {output}.")


def parse_indices(indices: List[str]) -> List[str]:
    """
    Parses a list of indices and returns only the versions,
    e.g [registry/index:v4.9, registry/index:v4.8] -> [v4.9, v4.8]
    Args:
        indices: List of indices

    Returns:
        Parsed list of versions
    """
    versions = []
    for index in indices:
        # split by : from right and get the rightmost result
        split = index.rsplit(":", 1)
        if len(split) == 1:
            # unable to split by :
            raise Exception(f"Unable to extract version from index {index}")
        else:
            versions.append(split[1])
    return versions


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

    publish_bundle(
        args.from_index,
        args.bundle_pullspec,
        args.iib_url,
        args.indices,
        args.output,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
