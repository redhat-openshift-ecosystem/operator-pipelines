from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from operator_repo import Repo
from operator_repo.checks import Fail, Warn
from operatorcert.static_tests.common.bundle import (
    check_operator_name,
    check_upgrade_graph_loop,
    check_replaces_availability,
)
from requests import HTTPError
from tests.utils import bundle_files, create_files, merge

from typing import Any


@pytest.mark.parametrize(
    "annotation_package,csv_package,expected",
    [
        pytest.param("foo", "foo", set(), id="Name matches"),
        pytest.param(
            "foo",
            "bar",
            {
                Warn(
                    "Bundle package annotation is set to 'foo'. Expected value "
                    "is 'bar' based on the CSV name. To fix this issue define "
                    "the annotation in 'metadata/annotations.yaml' file that "
                    "matches the CSV name."
                )
            },
            id="Name does not match",
        ),
    ],
)
def test_check_operator_name(
    annotation_package: str, csv_package: str, expected: Any, tmp_path: Path
) -> None:
    annotations = {
        "operators.operatorframework.io.bundle.package.v1": annotation_package,
    }
    create_files(tmp_path, bundle_files(csv_package, "0.0.1", annotations=annotations))

    repo = Repo(tmp_path)
    bundle = repo.operator(csv_package).bundle("0.0.1")

    assert set(check_operator_name(bundle)) == expected


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

    # Malformed .spec.replaces
    create_files(
        tmp_path,
        bundle_files("malformed", "0.0.1", csv={"spec": {"replaces": ""}}),
    )

    repo = Repo(tmp_path)
    operator = repo.operator("malformed")
    bundle = operator.bundle("0.0.1")
    failures = list(check_upgrade_graph_loop(bundle))
    assert len(failures) == 1 and isinstance(failures[0], Fail)
    assert "Bundle(malformed/0.0.1) has invalid 'replaces' field:" in failures[0].reason


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
@patch("operatorcert.static_tests.common.bundle.utils.get_ocp_supported_versions")
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
