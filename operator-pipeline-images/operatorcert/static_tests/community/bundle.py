"""
    Bundle checks for the community operator static test suite

    A bundle check is a function with a name starting with "check_"
    and taking a Bundle argument and yielding OperatorCheck objects
    (either Fail or Warn) to describe the issues found in the given Bundle.
"""

import logging
import json
import re
import subprocess
from collections.abc import Iterator
from typing import Any, List

from operator_repo import Bundle
from operator_repo.checks import CheckResult, Fail, Warn
from operator_repo.utils import lookup_dict
import requests

from .validations import (
    validate_capabilities,
    validate_categories,
    validate_icon,
    validate_links,
    validate_list_of_strings,
    validate_maintainers,
    validate_semver,
    validate_timestamp,
)

LOGGER = logging.getLogger("operator-cert")

# convert table for OCP <-> k8s versions
# for now these are hardcoded pairs -> if new version of OCP:k8s is released,
# this table should be updated
K8S_TO_OCP = {
    "4.5": "1.18",
    "4.6": "1.19",
    "4.7": "1.20",
    "4.8": "1.21",
    "4.9": "1.22",
    "4.10": "1.23",
    "4.11": "1.24",
    "4.12": "1.25",
    "4.13": "1.26",
    "4.14": "1.27",
    "4.15": "1.28",
    "4.16": "1.29",
}


class GraphLoopException(Exception):
    """
    Exception raised when a loop is detected in the update graph
    """


def process_ocp_version(ocp_metadata_version: Any) -> Any:
    """
    Helper function to process the OCP version.
    OCP version can be either range of mim-max supported versions
    (v4.7-v4.9), range of up to max supported version (v4.10)
    or exact single version (=v4.9)
    """
    # we are calling indices to extract the supported OCP version
    # which is then used in operator-sdk bundle validate
    # to run API deprecation test
    indices_url = "https://catalog.redhat.com/api/containers/v1/operators/indices"
    params = {
        "filter": "organization==community-operators",
        "sort_by": "ocp_version[desc]",
        "include": "data.ocp_version",
        "page_size": 1,
    }
    if ocp_metadata_version:
        params["ocp_versions_range"] = ocp_metadata_version

    rsp = requests.get(indices_url, params=params, timeout=60)  # type: ignore[arg-type]

    try:
        rsp.raise_for_status()
    except requests.HTTPError as exc:
        LOGGER.error("GET request to fetch the indices failed with: %s", exc)
        return None

    get_indices = rsp.json().get("data")
    ocp_version = get_indices[0].get("ocp_version") if get_indices else None

    return ocp_version


def run_operator_sdk_bundle_validate(
    bundle: Bundle, test_suite_selector: str
) -> Iterator[CheckResult]:
    """Run `operator-sdk bundle validate` using given test suite settings"""
    ocp_annotation = bundle.annotations.get("com.redhat.openshift.versions", None)

    ocp_version_to_convert = process_ocp_version(ocp_annotation)

    kube_version_for_deprecation_test = K8S_TO_OCP.get(ocp_version_to_convert)

    if kube_version_for_deprecation_test is None:
        LOGGER.info(
            "There was no OCP version specified. API deprecation test for the testing "
            "suite - %s - was run with 'None' value.",
            test_suite_selector,
        )

    cmd = [
        "operator-sdk",
        "bundle",
        "validate",
        "-o",
        "json-alpha1",
        bundle.root,
        "--select-optional",
        test_suite_selector,
        f"--optional-values=k8s-version={kube_version_for_deprecation_test}",
    ]
    sdk_result = json.loads(
        subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False
        ).stdout
    )
    for output in sdk_result.get("outputs") or []:
        output_type = output.get("type")
        output_message = output.get("message", "")
        if output_type == "error":
            yield Fail(output_message)
        else:
            yield Warn(output_message)


def check_osdk_bundle_validate_operatorhub(bundle: Bundle) -> Iterator[CheckResult]:
    """Run `operator-sdk bundle validate` using operatorhub settings"""
    yield from run_operator_sdk_bundle_validate(bundle, "name=operatorhub")


def check_osdk_bundle_validate_operator_framework(
    bundle: Bundle,
) -> Iterator[CheckResult]:
    """Run `operator-sdk bundle validate` using operatorframework settings"""
    yield from run_operator_sdk_bundle_validate(bundle, "suite=operatorframework")


def check_required_fields(bundle: Bundle) -> Iterator[CheckResult]:
    """Ensure the CSV contains all required fields"""
    # From https://github.com/operator-framework/community-operators/blob/master/
    # docs/packaging-required-fields.md#required-fields-for-operatorhub
    required_fields = [
        # Field, validation, fatal
        ("metadata.annotations.capabilities", validate_capabilities, True),
        ("metadata.annotations.categories", validate_categories, False),
        (
            "metadata.annotations.containerImage",
            re.compile(r"[^/]+/[^/]+/[^/:]+:.+"),
            True,
        ),
        ("metadata.annotations.createdAt", validate_timestamp, True),
        ("metadata.annotations.repository", re.compile(r"https?://.+"), False),
        ("metadata.annotations.support", re.compile(r".{3,}", re.DOTALL), True),
        ("metadata.annotations.alm-examples", re.compile(r".{30,}", re.DOTALL), True),
        ("metadata.annotations.description", re.compile(r".{10,}", re.DOTALL), False),
        ("spec.displayName", re.compile(r".{3,50}"), True),
        ("spec.description", re.compile(r".{20,}", re.DOTALL), True),
        ("spec.icon", validate_icon, True),
        ("spec.version", validate_semver, True),
        ("spec.maintainers", validate_maintainers, True),
        ("spec.provider.name", re.compile(r".{3,}"), True),
        ("spec.links", validate_links, True),
        ("spec.keywords", validate_list_of_strings, True),
    ]

    csv = bundle.csv
    for field, validation, fatal in required_fields:
        value = lookup_dict(csv, field)
        if value is None:
            success = False
            message = f"CSV does not define {field}"
        else:
            success = True
            if isinstance(validation, re.Pattern):
                success = bool(validation.match(str(value)))
            elif callable(validation):
                success = validation(value)
            message = f"CSV contains an invalid value for {field}"
        if success:
            continue
        yield Fail(message) if fatal else Warn(message)


def check_dangling_bundles(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Check dangling bundles in the operator update graph
    A dangling bundle is a bundle that is not referenced by any other bundle
    and is not a HEAD of a channel

    Example:
    Channel beta: A -> B -> C (head)
                    -> D

    Bundle D is dangling

    Args:
        bundle (Bundle): Operator bundle that is being checked

    Yields:
        Iterator[CheckResult]: Failure if a dangling bundle is found
    """
    all_channels: set[str] = set(bundle.channels)
    if bundle.default_channel is not None:
        all_channels.add(bundle.default_channel)
    operator = bundle.operator
    for channel in sorted(all_channels):
        channel_bundles = operator.channel_bundles(channel)
        channel_head = operator.head(channel)
        try:
            graph = operator.update_graph(channel)
        except NotImplementedError as exc:
            yield Fail(str(exc))
            return
        dangling_bundles = {
            x for x in channel_bundles if x not in graph and x != channel_head
        }
        if dangling_bundles:
            yield Fail(f"Channel {channel} has dangling bundles: {dangling_bundles}")


def check_upgrade_graph_loop(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Detect loops in the upgrade graph

    Example:

    Channel beta: A -> B -> C -> B

    Args:
        bundle (Bundle): Operator bundle

    Yields:
        Iterator[CheckResult]: Failure if a loop is detected
    """
    all_channels: set[str] = set(bundle.channels)
    if bundle.default_channel is not None:
        all_channels.add(bundle.default_channel)
    operator = bundle.operator
    for channel in sorted(all_channels):
        visited: List[Bundle] = []
        try:
            channel_bundles = operator.channel_bundles(channel)
            try:
                graph = operator.update_graph(channel)
            except NotImplementedError as exc:
                yield Fail(str(exc))
                return
            follow_graph(graph, channel_bundles[0], visited)
        except GraphLoopException as exc:
            yield Fail(str(exc))


def follow_graph(graph: Any, bundle: Bundle, visited: List[Bundle]) -> List[Bundle]:
    """
    Follow operator upgrade graph and raise exception if loop is detected

    Args:
        graph (Any): Operator update graph
        bundle (Bundle): Current bundle that started the graph traversal
        visited (List[Bundle]): List of bundles visited so far

    Raises:
        GraphLoopException: Graph loop detected

    Returns:
        List[Bundle]: List of bundles visited so far
    """
    if bundle in visited:
        visited.append(bundle)
        raise GraphLoopException(f"Upgrade graph loop detected for bundle: {visited}")
    if bundle not in graph:
        return visited

    visited.append(bundle)
    next_bundles = graph[bundle]
    for next_bundle in next_bundles:
        follow_graph(graph, next_bundle, visited)
    return visited
