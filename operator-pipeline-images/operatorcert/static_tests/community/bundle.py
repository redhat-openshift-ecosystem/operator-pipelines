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
from bisect import bisect
from collections.abc import Iterator

from operatorcert import utils
from operatorcert.operator_repo import Bundle
from operatorcert.operator_repo.checks import CheckResult, Fail, Warn
from operatorcert.operator_repo.utils import lookup_dict
from operatorcert.static_tests.helpers import skip_fbc
from semver import Version

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


def _parse_semver(version: str) -> Version:
    return Version.parse(version.strip(), optional_minor_and_patch=True).replace(
        prerelease=None, build=None
    )


def _parse_ocp_version(version: str) -> Version:
    return _parse_semver(version.strip().removeprefix("v")).replace(patch=0)


# convert table for OCP <-> k8s versions
# for now these are hardcoded pairs -> if new version of OCP:k8s is released,
# this table should be updated
# This is documented at https://access.redhat.com/solutions/4870701
# When adding an upcoming release the document above won't include the new
# version: to find the corresponding k8s version look at
# https://github.com/openshift/kubernetes/blob/release-4.YY/CHANGELOG/README.md
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
    "4.17": "1.30",
}

OCP_TO_K8S_SEMVER = {
    _parse_ocp_version(ocp_ver): _parse_semver(k8s_ver)
    for ocp_ver, k8s_ver in OCP_TO_K8S.items()
}


def find_closest_ocp_version(ocp_ver: Version) -> Version:
    """
    Find the closest openshift version between all known versions
    """
    all_ocp_versions = sorted(OCP_TO_K8S_SEMVER.keys())
    pos = bisect(all_ocp_versions, ocp_ver)
    if pos == 0:
        return all_ocp_versions[0]
    return all_ocp_versions[pos - 1]


def ocp_to_k8s_ver(ocp_ver: str) -> str:
    """
    Lookup the corresponding k8s version for an openshift version
    """
    try:
        return OCP_TO_K8S[ocp_ver]
    except KeyError:
        closest_ocp = find_closest_ocp_version(_parse_ocp_version(ocp_ver))
        LOGGER.warning(
            "Using openshift version %s in place of unknown openshift version %s",
            closest_ocp,
            ocp_ver,
        )
        k8s = OCP_TO_K8S_SEMVER[closest_ocp]
        return f"{k8s.major}.{k8s.minor}"


def run_operator_sdk_bundle_validate(
    bundle: Bundle, test_suite_selector: str
) -> Iterator[CheckResult]:
    """Run `operator-sdk bundle validate` using given test suite settings"""
    ocp_annotation = bundle.annotations.get("com.redhat.openshift.versions", None)

    ocp_versions = utils.get_ocp_supported_versions(
        "community-operators", ocp_annotation
    )
    if ocp_versions:
        ocp_latest_version = ocp_versions[0]

        kube_version_for_deprecation_test = ocp_to_k8s_ver(ocp_latest_version)

        cmd = [
            "operator-sdk",
            "bundle",
            "validate",
            "-o",
            "json-alpha1",
            str(bundle.root),
            "--select-optional",
            test_suite_selector,
            f"--optional-values=k8s-version={kube_version_for_deprecation_test}",
        ]
        try:
            sdk_result = json.loads(
                subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False
                ).stdout
            )
        except json.JSONDecodeError:
            yield Fail("operator-sdk returned non-JSON output when validating bundle")
            return
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


@skip_fbc
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


@skip_fbc
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
                    version = find_closest_ocp_version(
                        _parse_ocp_version(selector.removeprefix("="))
                    )
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


@skip_fbc
def check_replaces_availability(bundle: Bundle) -> Iterator[CheckResult]:
    """
    Check if the current bundle and the replaced bundle support the same OCP versions

    Args:
        bundle (Bundle): Operator bundle

    Yields:
        Iterator[CheckResult]: Failure if the version of the replaced bundle
        does not match with the current bundle
    """

    replaces = bundle.csv.get("spec", {}).get("replaces")
    if not replaces:
        return
    delimiter = ".v" if ".v" in replaces else "."
    replaces_version = replaces.split(delimiter, 1)[1]

    ver_to_dir = {
        x.csv_operator_version: x.operator_version
        for x in bundle.operator.all_bundles()
    }
    replaces_bundle = bundle.operator.bundle(ver_to_dir[replaces_version])

    ocp_versions_str = bundle.annotations.get("com.redhat.openshift.versions")
    replaces_ocp_version_str = replaces_bundle.annotations.get(
        "com.redhat.openshift.versions"
    )
    if ocp_versions_str == replaces_ocp_version_str:
        # The annotations match, no need to check further
        return
    organization = bundle.operator.repo.config.get("organization")

    indexes = set(utils.get_ocp_supported_versions(organization, ocp_versions_str))
    replaces_indexes = set(
        utils.get_ocp_supported_versions(organization, replaces_ocp_version_str)
    )

    if indexes - replaces_indexes == set():
        # The replaces bundle supports all the same versions as the current bundle
        return
    yield Fail(
        f"Replaces bundle {replaces_bundle} {sorted(replaces_indexes)} does not support "
        f"the same OCP versions as bundle {bundle} {sorted(indexes)}. In order to fix this issue, "
        "align the OCP version range to match the range of the replaced bundle. "
        "This can be done by setting the `com.redhat.openshift.versions` annotation in the "
        "`metadata/annotations.yaml` file.\n"
        f"`{bundle}` - `{ocp_versions_str}`\n"
        f"`{replaces_bundle}` - `{replaces_ocp_version_str}`"
    )
    yield from []


NON_FBC_SUGGESTION = (
    "[File Based Catalog (FBC)]"
    "(https://github.com/redhat-openshift-ecosystem/community-operators-prod/"
    "discussions/5031#discussion-7097441) "
    "is a new way to manage operator metadata. "
    "This operator does not use FBC. Consider [migrating]"
    "(https://redhat-openshift-ecosystem.github.io/operator-pipelines/users/fbc_onboarding/) "
    "for better maintainability."
)
NON_FBC_WARNING = (
    "[File Based Catalog (FBC)]"
    "(https://github.com/redhat-openshift-ecosystem/community-operators-prod/"
    "discussions/5031#discussion-7097441) "
    "is a new way to manage operator metadata. "
    "This operator does not use FBC and it is recommended for new operators to "
    "[start directly with FBC]"
    "(https://redhat-openshift-ecosystem.github.io/operator-pipelines/users/fbc_workflow/)."
)


@skip_fbc
def check_using_fbc(bundle: Bundle) -> Iterator[CheckResult]:
    """
    This check is used only for non-FBC bundles and suggests
    using the File Based Catalog for new Operators
    or recommends migrating existing Operators to FBC.

    Args:
        bundle (Bundle): Tested operator bundle
    """
    all_bundles = set(bundle.operator.all_bundles())
    other_bundles = all_bundles - {bundle}
    if other_bundles:
        # not a first bundle, existing operator
        yield Warn(NON_FBC_SUGGESTION)
    else:
        # TODO: change to Fail when FBC mandatory for new operators
        yield Warn(NON_FBC_WARNING)
