import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from operator_repo import Repo
from operator_repo.checks import CheckResult, Fail, Warn
from operatorcert.static_tests.community.bundle import (
    check_dangling_bundles,
    check_osdk_bundle_validate_operator_framework,
    check_osdk_bundle_validate_operatorhub,
    check_required_fields,
    run_operator_sdk_bundle_validate,
    check_api_version_constraints,
    check_replaces_availability,
    check_upgrade_graph_loop,
    check_using_fbc,
    ocp_to_k8s_ver,
)
from semver import Version
from tests.utils import bundle_files, create_files, merge


@pytest.mark.parametrize(
    "osdk_output, ocp_versions, expected",
    [
        (
            '{"passed": false, "outputs":'
            '[{"type": "error", "message": "foo"}, {"type": "warning", "message": "bar"}]}',
            ["4.9", "4.8"],
            {Fail("foo"), Warn("bar")},
        ),
        (
            '{"passed": false, "outputs":'
            '[{"type": "error", "message": "foo"}, {"type": "warning", "message": "bar"}]}',
            None,
            set(),
        ),
        (
            '{"passed": true, "outputs": null}',
            ["4.9", "4.8"],
            set(),
        ),
        (
            "rubbish",
            ["4.9", "4.8"],
            {Fail("operator-sdk returned non-JSON output when validating bundle")},
        ),
    ],
    indirect=False,
    ids=[
        "A warning and an error from operator-sdk",
        "No matching ocp versions",
        "No warnings or errors from operator-sdk",
        "Invalid output from operator-sdk",
    ],
)
@patch("operatorcert.static_tests.community.bundle.utils.get_ocp_supported_versions")
@patch("subprocess.run")
def test_run_operator_sdk_bundle_validate(
    mock_run: MagicMock,
    mock_version: MagicMock,
    osdk_output: str,
    ocp_versions: Optional[list[str]],
    expected: set[CheckResult],
    tmp_path: Path,
) -> None:
    create_files(tmp_path, bundle_files("test-operator", "0.0.1"))
    repo = Repo(tmp_path)
    bundle = repo.operator("test-operator").bundle("0.0.1")
    mock_version.return_value = ocp_versions
    process_mock = MagicMock()
    process_mock.stdout = osdk_output
    mock_run.return_value = process_mock
    assert set(run_operator_sdk_bundle_validate(bundle, "")) == expected


@pytest.mark.parametrize(
    "ocp_ver, expected",
    [
        pytest.param("4.2", "1.14", id="Known ocp_ver"),
        pytest.param("4.0", "1.13", id="Old ocp_ver"),
        pytest.param("4.4", "1.16", id="New ocp_ver"),
    ],
)
def test_ocp_to_k8s_ver(
    monkeypatch: pytest.MonkeyPatch, ocp_ver: str, expected: str
) -> None:
    # prevent the test from breaking when the OCP_TO_K8S mapping
    # is updated
    test_ver_map = {
        "4.1": "1.13",
        "4.2": "1.14",
        "4.3": "1.16",
    }
    test_ver_map_semver = {
        Version.parse(k, optional_minor_and_patch=True): Version.parse(
            v, optional_minor_and_patch=True
        )
        for k, v in test_ver_map.items()
    }
    monkeypatch.setattr(
        "operatorcert.static_tests.community.bundle.OCP_TO_K8S", test_ver_map
    )
    monkeypatch.setattr(
        "operatorcert.static_tests.community.bundle.OCP_TO_K8S_SEMVER",
        test_ver_map_semver,
    )
    assert ocp_to_k8s_ver(ocp_ver) == expected


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
            "metadata.annotations.createdAt": ("", "warning", "invalid"),
            "metadata.annotations.repository": ("", "warning", "invalid"),
            "metadata.annotations.support": ("", "warning", "invalid"),
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


@pytest.mark.parametrize(
    "fields",
    [
        {
            "metadata.annotations.containerImage": (
                "example/bar:tag",
                "warning",
                "valid",
            ),
        },
        {
            "metadata.annotations.containerImage": (
                "example.com/test/nested_namesapce/foo/bar:tag",
                "warning",
                "valid",
            ),
        },
        {
            "metadata.annotations.containerImage": (
                "example.com/foo/bar:tag",
                "warning",
                "valid",
            ),
        },
        {
            "metadata.annotations.containerImage": (
                "example.com/f~oo:tag",
                "warning",
                "valid",
            ),
        },
        {
            "metadata.annotations.containerImage": (
                "example.com/f~oo",
                "warning",
                "invalid",
            ),
        },
    ],
    indirect=False,
    ids=[
        "With one namespace",
        "With nested namespaces",
        "Verify the nested image reference",
        "With special characters in namespace",
        "invalid namespace",
    ],
)
def test_metadata_container_image_validation(
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


def test_check_dangling_bundles(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        bundle_files("hello", "0.0.2", csv={"spec": {"replaces": "hello.v0.0.1"}}),
        bundle_files("hello", "0.0.3", csv={"spec": {"replaces": "hello.v0.0.2"}}),
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle3 = operator.bundle("0.0.3")

    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "replaces-mode"}
        failures = list(check_dangling_bundles(bundle3))
        assert failures == []

    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "unknown-mode"}
        is_loop = list(check_dangling_bundles(bundle3))
        assert is_loop == [
            Fail("Operator(hello): unsupported updateGraph value: unknown-mode")
        ]

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
    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "replaces-mode"}
        failures = list(check_dangling_bundles(bundle3))
        assert len(failures) == 1 and isinstance(failures[0], Fail)
        assert (
            failures[0].reason
            == "Channel beta has dangling bundles: {Bundle(hello/0.0.2)}"
        )

    # Malformed .spec.replaces
    create_files(
        tmp_path,
        bundle_files("malformed", "0.0.1", csv={"spec": {"replaces": ""}}),
    )

    repo = Repo(tmp_path)
    operator = repo.operator("malformed")
    bundle1 = operator.bundle("0.0.1")
    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "replaces-mode"}
        failures = list(check_dangling_bundles(bundle1))
        assert len(failures) == 1 and isinstance(failures[0], Fail)
        assert (
            "Bundle(malformed/0.0.1) has invalid 'replaces' field:"
            in failures[0].reason
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
            set(),
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


def test_check_upgrade_graph_loop(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        bundle_files("hello", "0.0.2", csv={"spec": {"replaces": "hello.v0.0.1"}}),
    )

    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")
    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "replaces-mode"}
        is_loop = list(check_upgrade_graph_loop(bundle))
        assert is_loop == []

    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "unknown-mode"}
        is_loop = list(check_upgrade_graph_loop(bundle))
        assert is_loop == [
            Fail("Operator(hello): unsupported updateGraph value: unknown-mode")
        ]

    # Both bundles replace each other
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1", csv={"spec": {"replaces": "hello.v0.0.2"}}),
        bundle_files("hello", "0.0.2", csv={"spec": {"replaces": "hello.v0.0.1"}}),
    )

    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.1")
    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "replaces-mode"}
        is_loop = list(check_upgrade_graph_loop(bundle))
        assert len(is_loop) == 1 and isinstance(is_loop[0], Fail)
        assert (
            is_loop[0].reason
            == "Upgrade graph loop detected for bundle: [Bundle(hello/0.0.1), "
            "Bundle(hello/0.0.2), Bundle(hello/0.0.1)]"
        )

    # Malformed .spec.replaces
    create_files(
        tmp_path,
        bundle_files("malformed", "0.0.1", csv={"spec": {"replaces": ""}}),
    )

    repo = Repo(tmp_path)
    operator = repo.operator("malformed")
    bundle = operator.bundle("0.0.1")
    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "replaces-mode"}
        failures = list(check_upgrade_graph_loop(bundle))
        assert len(failures) == 1 and isinstance(failures[0], Fail)
        assert (
            "Bundle(malformed/0.0.1) has invalid 'replaces' field:"
            in failures[0].reason
        )


def test_check_replaces_availability_no_replaces(
    tmp_path: Path,
) -> None:
    bundle_annotation = {
        "com.redhat.openshift.versions": "v4.10",
    }
    replaces_bundle_annotation = {
        "com.redhat.openshift.versions": "v4.11",
    }
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1", annotations=replaces_bundle_annotation),
        bundle_files(
            "hello",
            "0.0.2",
            annotations=bundle_annotation,
        ),
    )

    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.2")
    errors = list(check_replaces_availability(bundle))

    assert set(errors) == set()


@pytest.mark.parametrize(
    "bundle_version_annotation,replaces_version_annotation,ocp_range,expected",
    [
        pytest.param(None, None, [], set(), id="No annotations"),
        pytest.param("v4.10", "v4.10", [], set(), id="Same annotations"),
        pytest.param(
            "v4.15",
            "v4.15,v4.16",
            [["v4.15", "v4.16"], ["v4.15", "v4.16"]],
            set(),
            id="Different annotation, versions match",
        ),
        pytest.param(
            "v4.15",
            "v4.16",
            [["v4.15", "v4.16"], ["v4.16"]],
            {
                Fail(
                    "Replaces bundle Bundle(hello/0.0.1) ['v4.16'] does not support "
                    "the same OCP versions as bundle Bundle(hello/0.0.2) ['v4.15', 'v4.16']. "
                    "In order to fix this issue, align the OCP version range to match the "
                    "range of the replaced bundle. "
                    "This can be done by setting the `com.redhat.openshift.versions` annotation "
                    "in the `metadata/annotations.yaml` file.\n"
                    "`Bundle(hello/0.0.2)` - `v4.15`\n"
                    "`Bundle(hello/0.0.1)` - `v4.16`"
                )
            },
            id="Different annotation, different version",
        ),
    ],
)
@patch("operatorcert.static_tests.community.bundle.utils.get_ocp_supported_versions")
def test_check_replaces_availability(
    mock_get_ocp_supported_versions: MagicMock,
    bundle_version_annotation: str,
    replaces_version_annotation: str,
    ocp_range: Any,
    expected: Any,
    tmp_path: Path,
) -> None:
    bundle_annotation = {
        "com.redhat.openshift.versions": bundle_version_annotation,
    }
    replaces_bundle_annotation = {
        "com.redhat.openshift.versions": replaces_version_annotation,
    }
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1", annotations=replaces_bundle_annotation),
        bundle_files(
            "hello",
            "0.0.2",
            annotations=bundle_annotation,
            csv={"spec": {"replaces": "hello.v0.0.1"}},
        ),
    )

    mock_get_ocp_supported_versions.side_effect = ocp_range

    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    bundle = operator.bundle("0.0.2")
    errors = list(check_replaces_availability(bundle))

    assert set(errors) == expected


@pytest.mark.parametrize(
    "files, bundle_to_check, expected",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
            ],
            ("hello", "0.0.1"),
            "is recommended for new operators",
            id="New bundle warning",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files("hello", "0.0.2"),
            ],
            ("hello", "0.0.2"),
            "This operator does not use FBC. Consider",
            id="Updating existing operator",
        ),
    ],
)
def test_using_fbc(
    tmp_path: Path,
    files: list[dict[str, Any]],
    bundle_to_check: tuple[str, str],
    expected: str,
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator_name, bundle_version = bundle_to_check
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version)

    results = list(check_using_fbc(bundle))

    assert len(results) == 1
    assert expected in results[0].reason
