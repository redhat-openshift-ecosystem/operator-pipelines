from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from operator_repo import Repo
from operator_repo.checks import Fail, Warn
from operatorcert.static_tests.common.bundle import (
    check_operator_name,
    check_upgrade_graph_loop,
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
