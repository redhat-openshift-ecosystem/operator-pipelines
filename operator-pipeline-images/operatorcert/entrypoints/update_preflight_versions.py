"""
Tool automating invalidation of older versions of Preflight in Pyxis based on
rules in https://issues.redhat.com/browse/ISV-4964.
"""

from datetime import datetime, timedelta
from typing import Any
import sys
import argparse as ap
from dataclasses import dataclass
import urllib.parse
import json
import logging
import pprint
from itertools import islice
from packaging.version import Version
import requests

from requests import Response

from operatorcert import pyxis

logger = logging.getLogger(__name__)


@dataclass
class PreflightVersion:
    """Object representing a Preflight version in Pyxis."""

    id: str
    created: datetime
    version: Version
    enabled_for_testing: bool


def parse_versions(data: dict[str, Any]) -> list[PreflightVersion]:
    """Parse raw Pyxis dictionary into PreflightVersion object."""
    versions = []
    for version in data["data"]:
        _id = version["_id"]
        enabled = version["enabled_for_testing"]
        created = datetime.fromisoformat(version["creation_date"])
        version = Version(version["version"])
        versions.append(
            PreflightVersion(
                id=_id, created=created, version=version, enabled_for_testing=enabled
            )
        )

    return versions


def get_version_data_page(url: str, page: int, page_size: int) -> bytes:
    """Get single page of preflight data."""
    preflight_filter = "name==github.com/redhat-openshift-ecosystem/openshift-preflight"
    params = {
        "filter": preflight_filter,
        "page": page,
        "page_size": page_size,
    }

    resp: Response = pyxis.get(url, params, auth_required=False)
    if resp.status_code != 200:
        logger.warning("Pyxis returned code %s: %s", resp.status_code, resp.content)
        raise RuntimeError()

    return resp.content


def get_versions(pyxis_url: str, page_size: int = 100) -> list[PreflightVersion]:
    """Get a list of current Preflight versions in Pyxis."""
    url = urllib.parse.urljoin(pyxis_url, "v1/tools")

    versions: list[PreflightVersion] = []

    page = 0
    data = json.loads(get_version_data_page(url, page, page_size))

    versions.extend(parse_versions(data))

    total = int(data["total"])
    while len(versions) != total:
        page += 1
        data = json.loads(get_version_data_page(url, page, page_size))
        versions.extend(parse_versions(data))
        total = int(data["total"])

    return versions


def get_versions_to_disable(versions: list[PreflightVersion]) -> list[PreflightVersion]:
    """Get Preflight versions to disable based on current versions in Pyxis."""
    versions.sort(reverse=True, key=lambda v: v.version)

    to_update = []

    # ignore two newest versions
    # only look at versions that are currently enabled
    older_versions = filter(lambda v: v.enabled_for_testing, islice(versions, 2, None))

    for version in older_versions:
        now = datetime.now(version.created.tzinfo)

        if now - version.created > timedelta(days=90):
            to_update.append(version)

    return to_update


def disable_version(pyxis_url: str, version: PreflightVersion) -> None:
    """Disable a Preflight version in Pyxis."""
    url = urllib.parse.urljoin(pyxis_url, f"v1/tools/id/{version.id}")
    pyxis.patch(url, {"enabled_for_testing": False})


def synchronize_versions(pyxis_url: str, dry_run: bool, log_current: bool):
    """
    Invalidate older versions of Preflight in Pyxis based on rules in
    https://issues.redhat.com/browse/ISV-4964
    """
    current = get_versions(pyxis_url)
    if log_current or dry_run:
        logger.info("Current versions in Pyxis: %s", pprint.pformat(current))
    to_disable = get_versions_to_disable(current)

    if dry_run:  # pragma: no cover
        logger.info(
            "Versions to be disabled: %s",
            pprint.pformat([(v.id, v.version) for v in to_disable]),
        )
        return

    for version in to_disable:
        disable_version(pyxis_url, version)
        logger.info(
            "Disabled version: %s", pprint.pformat((version.id, version.version))
        )


def main():  # pragma: no cover
    """
    Invalidate older versions of Preflight in Pyxis based on rules in
    https://issues.redhat.com/browse/ISV-4964
    """
    logging.basicConfig(level=logging.DEBUG)
    parser = ap.ArgumentParser(
        description="Tool automating invalidation of older Preflight versions in Pyxis. "
        "https://issues.redhat.com/browse/ISV-4964"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="print versions to be disabled and exit",
    )
    parser.add_argument(
        "-c", "--log-current", action="store_true", help="log current versions in Pyxis"
    )
    parser.add_argument(
        "--pyxis-url",
        default="https://pyxis.engineering.redhat.com/",
        help="base URL for Pyxis container metadata API",
    )
    args = parser.parse_args()

    retries = 5
    while retries > 0:
        try:
            synchronize_versions(args.pyxis_url, args.dry_run, args.log_current)
            break
        except (requests.HTTPError, RuntimeError):
            retries -= 1

    if retries == 0:
        logger.error("Failed to update preflight versions")
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
