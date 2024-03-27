"""
    Bundle checks for the community operator static test suite

    A bundle check is a function with a name starting with "check_"
    and taking a Bundle argument and yielding OperatorCheck objects
    (either Fail or Warn) to describe the issues found in the given Bundle.
"""

import json
import logging
import re
import subprocess
from collections.abc import Iterator

from operator_repo import Bundle
from operator_repo.checks import CheckResult, Fail, Warn
from operator_repo.utils import lookup_dict
from semver import Version
from operatorcert import utils

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
OCP_TO_K8S = {
    "4.1": "1.13",
    "4.2": "1.14",
    "4.3": "1.16",
    "4.4": "1.17",
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


def _parse_semver(version: str) -> Version:
    return Version.parse(version.strip(), optional_minor_and_patch=True).replace(
        prerelease=None, build=None
    )


def _parse_ocp_version(version: str) -> Version:
    return _parse_semver(version.strip().removeprefix("v")).replace(patch=0)


OCP_TO_K8S_SEMVER = {
    _parse_ocp_version(ocp_ver): _parse_semver(k8s_ver)
    for ocp_ver, k8s_ver in OCP_TO_K8S.items()
}


def run_operator_sdk_bundle_validate(
    bundle: Bundle, test_suite_selector: str
) -> Iterator[CheckResult]:
    """Run `operator-sdk bundle validate` using given test suite settings"""
    ocp_annotation = bundle.annotations.get("com.redhat.openshift.versions", None)

    ocp_versions = utils.get_ocp_supported_versions(
        "community-operators", ocp_annotation
    )
    ocp_latest_version = ocp_versions[0] if ocp_versions else None

    kube_version_for_deprecation_test = OCP_TO_K8S.get(ocp_latest_version)

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
        ("metadata.annotations.capabilities", validate_capabilities, False),
        ("metadata.annotations.categories", validate_categories, False),
        (
            "metadata.annotations.containerImage",
            re.compile(r"([^/]+/){1,}[^/:]+:.+"),
            False,
        ),
        ("metadata.annotations.createdAt", validate_timestamp, False),
        ("metadata.annotations.repository", re.compile(r"https?://.+"), False),
        ("metadata.annotations.support", re.compile(r".{3,}", re.DOTALL), False),
        ("metadata.annotations.description", re.compile(r".{10,}", re.DOTALL), False),
        ("spec.displayName", re.compile(r".{3,50}"), True),
        ("spec.description", re.compile(r".{20,}", re.DOTALL), True),
        ("spec.icon", validate_icon, True),
        ("spec.version", validate_semver, True),
        ("spec.maintainers", validate_maintainers, True),
        ("spec.provider.name", re.compile(r".{3,}"), True),
        ("spec.links", validate_links, True),
        ("spec.keywords", validate_list_of_strings, False),
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
        except (NotImplementedError, ValueError) as exc:
            yield Fail(str(exc))
            return
        dangling_bundles = {
            x for x in channel_bundles if x not in graph and x != channel_head
        }
        if dangling_bundles:
            yield Fail(f"Channel {channel} has dangling bundles: {dangling_bundles}")


def check_api_version_constraints(bundle: Bundle) -> Iterator[CheckResult]:
    """Check that the ocp and k8s api version constraints are consistent"""
    ocp_versions_str = bundle.annotations.get("com.redhat.openshift.versions")
    k8s_version_min_str = bundle.csv.get("spec", {}).get("minKubeVersion")
    if not k8s_version_min_str:
        # minKubeVersion is not specified: no conflict
        return
    try:
        k8s_version_min = _parse_semver(k8s_version_min_str)
    except (ValueError, TypeError) as exc:
        yield Fail(f"Invalid minKubeVersion: {exc}")
        return
    if ocp_versions_str:
        selector = ocp_versions_str.strip()
        try:
            if "-" in selector:
                # Version range, example: v4.10-v4.12
                ver_a, ver_b = (
                    _parse_ocp_version(ver) for ver in selector.split("-", 1)
                )
                ocp_versions = {
                    ver for ver in OCP_TO_K8S_SEMVER if ver_a <= ver <= ver_b
                }
            elif "," in selector:
                # Deprecated comma separated list of versions. Only supported versions
                # for this syntax are 4.5 and 4.6 but we do not enforce that here
                # because there are some community operators that currently use this
                # with other ocp versions
                versions = {_parse_ocp_version(ver) for ver in selector.split(",")}
                min_version = min(versions)
                if versions != {_parse_ocp_version(ver) for ver in ["v4.5", "v4.6"]}:
                    yield Warn(
                        "Comma separated list of versions in "
                        "com.redhat.openshift.versions is only supported for v4.5 and "
                        "v4.6"
                    )
                ocp_versions = {ver for ver in OCP_TO_K8S_SEMVER if ver >= min_version}
            else:
                # com.redhat.openshift.versions contains a single version
                if selector.startswith("="):
                    # Select a specific version
                    version = _parse_ocp_version(selector.removeprefix("="))
                    if version not in OCP_TO_K8S_SEMVER:
                        yield Fail(
                            "Unknown OCP version in "
                            "com.redhat.openshift.versions: "
                            f"{version.major}.{version.minor}"
                        )
                        return
                    ocp_versions = {version}
                else:
                    # Any version >= the specified value
                    ocp_versions = {
                        ver
                        for ver in OCP_TO_K8S_SEMVER
                        if ver >= _parse_ocp_version(selector)
                    }
        except (ValueError, TypeError) as exc:
            yield Fail(f"Invalid com.redhat.openshift.versions: {exc}")
            return
    else:
        # If no selector is specified, the bundle can potentially run on any
        # ocp version. If we reach this point, minKubeVersion was specified
        yield Fail(
            f"minKubeVersion is set to {k8s_version_min} but "
            "com.redhat.openshift.versions is not set"
        )
        return
    conflicting = {
        ver for ver in ocp_versions if OCP_TO_K8S_SEMVER[ver] < k8s_version_min
    }
    if conflicting:
        conflicting_str = ",".join(
            f"{ver.major}.{ver.minor}" for ver in sorted(conflicting)
        )
        yield Fail(
            f"OCP version(s) {conflicting_str} conflict with "
            f"minKubeVersion={k8s_version_min}"
        )
