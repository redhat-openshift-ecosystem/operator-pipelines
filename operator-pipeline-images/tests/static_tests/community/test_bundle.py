import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock, patch

import pytest
from operator_repo import Repo
from operator_repo.checks import CheckResult, Fail, Warn
from operatorcert.static_tests.community.bundle import (
    check_dangling_bundles,
    check_osdk_bundle_validate_operator_framework,
    check_osdk_bundle_validate_operatorhub,
    check_required_fields,
    check_upgrade_graph_loop,
    run_operator_sdk_bundle_validate,
    process_ocp_version,
    check_api_version_constraints,
)
from tests.utils import bundle_files, create_files, merge

from requests import HTTPError


@pytest.mark.parametrize(
    ["ocp", "expected"],
    [
        ({"data": [{"ocp_version": "4.13"}]}, "4.13"),
        ({"data": []}, None),
    ],
)
@patch("operatorcert.static_tests.community.bundle.requests")
def test_process_ocp_version(
    mock_get: MagicMock, ocp: Dict[str, List[Dict[str, str]]], expected: str
) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ocp
    mock_get.get.return_value = mock_response
    assert process_ocp_version(ocp) == expected


@patch("operatorcert.static_tests.community.bundle.requests.get")
def test_process_ocp_version_error(mock_get: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError(
        "404, GET request to fetch the indices failed"
    )
    mock_get.return_value = mock_response
    result = process_ocp_version("4.12")
    assert result is None


@pytest.mark.parametrize("version", ["4.8-4.9", "4.9", None])
@pytest.mark.parametrize(
    "osdk_output, expected",
    [
        (
            '{"passed": false, "outputs":'
            '[{"type": "error", "message": "foo"}, {"type": "warning", "message": "bar"}]}',
            {Fail("foo"), Warn("bar")},
        ),
        (
            '{"passed": true, "outputs": null}',
            set(),
        ),
    ],
    indirect=False,
    ids=[
        "A warning and an error",
        "No warnings or errors",
    ],
)
@patch("operatorcert.static_tests.community.bundle.process_ocp_version")
@patch("subprocess.run")
def test_run_operator_sdk_bundle_validate(
    mock_run: MagicMock,
    mock_version: MagicMock,
    version: Any,
    osdk_output: str,
    expected: set[CheckResult],
    tmp_path: Path,
) -> None:
    create_files(tmp_path, bundle_files("test-operator", "0.0.1"))
    repo = Repo(tmp_path)
    bundle = repo.operator("test-operator").bundle("0.0.1")
    mock_version.return_value = version
    process_mock = MagicMock()
    process_mock.stdout = osdk_output
    mock_run.return_value = process_mock
    assert set(run_operator_sdk_bundle_validate(bundle, "")) == expected


@patch("operatorcert.static_tests.community.bundle.run_operator_sdk_bundle_validate")
def test_check_osdk_bundle_validate_operator_framework(mock_sdk: MagicMock) -> None:
    bundle = MagicMock()
    list(check_osdk_bundle_validate_operator_framework(bundle))
    mock_sdk.assert_called_once_with(bundle, "suite=operatorframework")


@patch("operatorcert.static_tests.community.bundle.run_operator_sdk_bundle_validate")
def test_check_osdk_bundle_validate_operatorhub(mock_sdk: MagicMock) -> None:
    bundle = MagicMock()
    list(check_osdk_bundle_validate_operatorhub(bundle))
    mock_sdk.assert_called_once_with(bundle, "name=operatorhub")


def _make_nested_dict(path: str, value: Any) -> Dict[str, Any]:
    """
    _make_nested_dict("foo.bar", "baz") -> {"foo": {"bar": "baz"}}
    """
    result: Dict[str, Any] = {}
    current = result
    keys = path.split(".")
    for key in keys[:-1]:
        current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return result


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {
            "metadata.annotations.capabilities": ("", "warning", "invalid"),
            "metadata.annotations.categories": ("", "warning", "invalid"),
            "metadata.annotations.containerImage": ("", "warning", "invalid"),
            "metadata.annotations.createdAt": ("", "failure", "invalid"),
            "metadata.annotations.repository": ("", "warning", "invalid"),
            "metadata.annotations.support": ("", "warning", "invalid"),
            "metadata.annotations.alm-examples": ("", "failure", "invalid"),
            "metadata.annotations.description": ("", "warning", "invalid"),
            "spec.displayName": ("", "failure", "invalid"),
            "spec.description": ("", "failure", "invalid"),
            "spec.icon": ("", "failure", "invalid"),
            "spec.version": ("", "failure", "invalid"),
            "spec.maintainers": ("", "failure", "invalid"),
            "spec.provider.name": ("", "failure", "invalid"),
            "spec.links": ("", "failure", "invalid"),
            "spec.keywords": ("", "warning", "invalid"),
        },
        {
            "metadata.annotations.capabilities": ("Basic Install", "warning", "valid"),
            "metadata.annotations.categories": ("Storage,Security", "warning", "valid"),
            "metadata.annotations.containerImage": (
                "example.com/foo/bar:tag",
                "warning",
                "valid",
            ),
            "metadata.annotations.createdAt": (
                "2023-08-15T12:00:00Z",
                "failure",
                "valid",
            ),
            "metadata.annotations.repository": (
                "https://example.com/foo/bar.git",
                "warning",
                "valid",
            ),
            "metadata.annotations.support": (
                "Accusamus quidem quam enim dolor.",
                "warning",
                "valid",
            ),
            "metadata.annotations.alm-examples": (
                "Accusamus quidem quam enim dolor.",
                "failure",
                "valid",
            ),
            "metadata.annotations.description": (
                "Accusamus quidem quam enim dolor.",
                "warning",
                "valid",
            ),
            "spec.displayName": (
                "Accusamus quidem quam enim dolor.",
                "failure",
                "valid",
            ),
            "spec.description": (
                "Accusamus quidem quam enim dolor.",
                "failure",
                "valid",
            ),
            "spec.icon": (
                [{"base64data": "Zm9v", "mediatype": "image/svg+xml"}],
                "failure",
                "valid",
            ),
            "spec.version": ("0.0.1", "failure", "valid"),
            "spec.maintainers": (
                [{"name": "John Doe", "email": "jdoe@example.com"}],
                "failure",
                "valid",
            ),
            "spec.provider.name": ({"name": "ACME Corp."}, "failure", "valid"),
            "spec.links": (
                [{"name": "example", "url": "https://example.com/"}],
                "failure",
                "valid",
            ),
            "spec.keywords": (["foo", "bar"], "warning", "valid"),
        },
    ],
    indirect=False,
    ids=[
        "All missing",
        "All invalid",
        "All valid",
    ],
)
def test_required_fields(
    tmp_path: Path, fields: dict[str, tuple[Any, str, str]]
) -> None:
    csv_fields: Dict[str, Any] = {}
    for path, (value, _, _) in fields.items():
        merge(csv_fields, _make_nested_dict(path, value))
    create_files(tmp_path, bundle_files("test-operator", "0.0.1", csv=csv_fields))
    repo = Repo(tmp_path)
    bundle = repo.operator("test-operator").bundle("0.0.1")

    re_missing = re.compile(r"CSV does not define (.+)")
    re_invalid = re.compile(r"CSV contains an invalid value for (.+)")

    collected_results = {}

    for result in check_required_fields(bundle):
        match_missing = re_missing.match(result.reason)
        if match_missing:
            collected_results[match_missing.group(1)] = (result.kind, "missing")
            continue
        match_invalid = re_invalid.match(result.reason)
        if match_invalid:
            collected_results[match_invalid.group(1)] = (result.kind, "invalid")

    expected_problems = {k for k, (_, __, t) in fields.items() if t != "valid"}
    expected_successes = set(fields.keys()) - expected_problems
    assert {k: v for k, v in collected_results.items() if k in expected_problems} == {
        k: (s, t) for k, (_, s, t) in fields.items() if t != "valid"
    }
    assert all(
        t == "missing" for k, (_, t) in collected_results.items() if k not in fields
    )
    assert expected_successes.intersection(collected_results.keys()) == set()


@patch("operator_repo.core.Operator.config")
def test_check_dangling_bundles(mock_config: MagicMock, tmp_path: Path) -> None:
    mock_config.get.return_value = "replaces-mode"
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        bundle_files("hello", "0.0.2", csv={"spec": {"replaces": "hello.v0.0.1"}}),
        bundle_files("hello", "0.0.3", csv={"spec": {"replaces": "hello.v0.0.2"}}),
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle3 = operator.bundle("0.0.3")
    failures = list(check_dangling_bundles(bundle3))
    assert failures == []

    mock_config.get.return_value = "unknown-mode"
    is_loop = list(check_dangling_bundles(bundle3))
    assert is_loop == [
        Fail("Operator(hello): unsupported updateGraph value: unknown-mode")
    ]

    mock_config.get.return_value = "replaces-mode"
    # Bundle 0.0.2 is not referenced by any bundle and it is not a HEAD of channel
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        bundle_files("hello", "0.0.2", csv={"spec": {"replaces": "hello.v0.0.1"}}),
        bundle_files("hello", "0.0.3", csv={"spec": {"replaces": "hello.v0.0.1"}}),
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle3 = operator.bundle("0.0.3")
    failures = list(check_dangling_bundles(bundle3))
    assert len(failures) == 1 and isinstance(failures[0], Fail)
    assert (
        failures[0].reason == "Channel beta has dangling bundles: {Bundle(hello/0.0.2)}"
    )


@patch("operator_repo.core.Operator.config")
def test_check_upgrade_graph_loop(mock_config: MagicMock, tmp_path: Path) -> None:
    mock_config.get.return_value = "replaces-mode"
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        bundle_files("hello", "0.0.2", csv={"spec": {"replaces": "hello.v0.0.1"}}),
    )

    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")
    is_loop = list(check_upgrade_graph_loop(bundle))
    assert is_loop == []

    mock_config.get.return_value = "unknown-mode"
    is_loop = list(check_upgrade_graph_loop(bundle))
    assert is_loop == [
        Fail("Operator(hello): unsupported updateGraph value: unknown-mode")
    ]

    mock_config.get.return_value = "replaces-mode"
    # Both bundles replace each other
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1", csv={"spec": {"replaces": "hello.v0.0.2"}}),
        bundle_files("hello", "0.0.2", csv={"spec": {"replaces": "hello.v0.0.1"}}),
    )

    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")
    is_loop = list(check_upgrade_graph_loop(bundle))
    assert len(is_loop) == 1 and isinstance(is_loop[0], Fail)
    assert (
        is_loop[0].reason
        == "Upgrade graph loop detected for bundle: [Bundle(hello/0.0.1), "
        "Bundle(hello/0.0.2), Bundle(hello/0.0.1)]"
    )


@pytest.mark.parametrize(
    "csv, annotations, expected",
    [
        pytest.param(
            None, None, set(), id="No minKubeVersion, no com.redhat.openshift.versions"
        ),
        pytest.param(
            None,
            {"com.redhat.openshift.versions": "v4.11"},
            set(),
            id="No minKubeVersion, valid com.redhat.openshift.versions",
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.24.0"}},
            {"com.redhat.openshift.versions": "=v4.11"},
            set(),
            id='Valid minKubeVersion, valid com.redhat.openshift.versions ("=")',
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.0.0"}},
            {"com.redhat.openshift.versions": "=v3.1"},
            {Fail("Unknown OCP version in com.redhat.openshift.versions: 3.1")},
            id='Valid minKubeVersion, unknown com.redhat.openshift.versions ("=")',
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "foo"}},
            {"com.redhat.openshift.versions": "v4.11"},
            {Fail("Invalid minKubeVersion: foo is not valid SemVer string")},
            id="Invalid minKubeVersion, valid com.redhat.openshift.versions",
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.24.0"}},
            {"com.redhat.openshift.versions": "v4.11"},
            set(),
            id="Valid minKubeVersion, valid and consistent com.redhat.openshift.versions",
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.24.0"}},
            {"com.redhat.openshift.versions": "v4.11-v4.13"},
            set(),
            id='Valid minKubeVersion, valid and consistent com.redhat.openshift.versions ("-")',
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.16.0"}},
            {"com.redhat.openshift.versions": "v4.5,v4.6"},
            set(),
            id='Valid minKubeVersion, valid and consistent com.redhat.openshift.versions (",")',
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.16.0"}},
            {"com.redhat.openshift.versions": "v4.5,v4.7"},
            {
                Warn(
                    "Comma separated list of versions in com.redhat.openshift.versions is only "
                    "supported for v4.5 and v4.6"
                )
            },
            id='Valid minKubeVersion, unsupported version in com.redhat.openshift.versions (",")',
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.24.0"}},
            None,
            {
                Fail(
                    "minKubeVersion is set to 1.24.0 but com.redhat.openshift.versions is not set"
                )
            },
            id="Valid minKubeVersion, no com.redhat.openshift.versions",
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.24.0"}},
            {"com.redhat.openshift.versions": "v4.10"},
            {Fail("OCP version(s) 4.10 conflict with minKubeVersion=1.24.0")},
            id="Valid minKubeVersion, valid but inconsistent com.redhat.openshift.versions",
        ),
        pytest.param(
            {"spec": {"minKubeVersion": "1.24.0"}},
            {"com.redhat.openshift.versions": "foo"},
            {
                Fail(
                    "Invalid com.redhat.openshift.versions: foo is not valid SemVer string"
                )
            },
            id="Valid minKubeVersion, invalid com.redhat.openshift.versions",
        ),
    ],
)
def test_check_api_version_constraints(
    csv: Optional[Dict[str, Any]],
    annotations: Optional[Dict[str, Any]],
    expected: Set[CheckResult],
    tmp_path: Path,
) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1", annotations=annotations, csv=csv),
    )
    bundle = Repo(tmp_path).operator("hello").bundle("0.0.1")
    assert set(check_api_version_constraints(bundle)) == expected
