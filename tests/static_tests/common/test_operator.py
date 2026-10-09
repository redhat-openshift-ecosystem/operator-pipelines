from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from operatorcert.operator_repo import Repo
from operatorcert.operator_repo.checks import Fail
from operatorcert.static_tests.common.operator import (
    check_catalog_usage_ci_config,
    check_leaks_in_changed_files,
    check_schema_operator_ci_config,
)
from operatorcert.static_tests.helpers import set_affected_operator_files
from tests.utils import bundle_files, create_files


@pytest.mark.parametrize(
    "files, operator_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {"operators/hello/ci.yaml": {"fbc": "hello"}},
            ],
            "hello",
            {
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'hello' is not of type 'object'",
                ),
            },
            id="Testing the validation for invalid fbc field type",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {"enabled": True, "catalog_mapping": "hello"}
                    }
                },
            ],
            "hello",
            {
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'hello' is not of type 'array'",
                ),
            },
            id="Testing the validation for invalid catalog_mapping array data",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {"enabled": True, "catalog_mapping": [{"hello": ""}]}
                    }
                },
            ],
            "hello",
            {
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'template_name' is a required property",
                ),
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'type' is a required property",
                ),
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'catalog_names' is a required property",
                ),
            },
            id="Testing with missing all required fields in catalog_mapping array",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {
                            "enabled": True,
                            "catalog_mapping": [{"type": "demo.type"}],
                        }
                    }
                },
            ],
            "hello",
            {
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'template_name' is a required property",
                ),
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'catalog_names' is a required property",
                ),
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data "
                    "which does not comply with the schema: "
                    "'demo.type' is not one of ['olm.template.basic', 'olm.semver']",
                ),
            },
            id="Testing with missing required fields and invalid enum value in catalog_mapping array",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {
                            "enabled": True,
                            "catalog_mapping": [
                                {
                                    "template_name": "foo",
                                    "catalog_names": ["1.0", "1.0"],
                                    "type": "olm.template.basic",
                                }
                            ],
                        }
                    }
                },
            ],
            "hello",
            {
                (
                    Fail,
                    "Operator's 'ci.yaml' contains invalid data which does not comply with "
                    "the schema: ['1.0', '1.0'] has non-unique elements",
                )
            },
            id="Testing duplicated items in catalog_names.",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {
                            "enabled": True,
                            "catalog_mapping": [
                                {
                                    "template_name": "foo",
                                    "catalog_names": ["1.0", "2.0"],
                                    "type": "olm.template.basic",
                                }
                            ],
                        }
                    }
                },
            ],
            "hello",
            set(),
            id="Testing with all valid fields with required data for ci.yaml schema.",
        ),
    ],
    indirect=False,
)
def test_check_schema_operator_ci_config(
    tmp_path: Path,
    files: list[dict[str, Any]],
    operator_to_check: str,
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator = repo.operator(operator_to_check)
    assert {
        (x.__class__, x.reason) for x in check_schema_operator_ci_config(operator)
    } == expected_results


@pytest.mark.parametrize(
    "files, operator_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {"operators/hello/ci.yaml": {"fbc": {}}},
            ],
            "hello",
            set(),
            id="No catalog mapping in ci.yaml",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {
                            "catalog_mapping": [
                                {
                                    "template_name": "foo",
                                    "catalog_names": ["1.0", "2.0", "3.0"],
                                    "type": "olm.template.basic",
                                },
                                {
                                    "template_name": "bar",
                                    "catalog_names": ["2.0", "3.0", "4.0"],
                                    "type": "olm.template.basic",
                                },
                            ]
                        }
                    }
                },
            ],
            "hello",
            {
                (
                    Fail,
                    "Operator's 'ci.yaml' contains multiple templates '['foo', 'bar']' "
                    "for the same catalog '2.0'.",
                ),
                (
                    Fail,
                    "Operator's 'ci.yaml' contains multiple templates '['foo', 'bar']' "
                    "for the same catalog '3.0'.",
                ),
            },
            id="Operator with multiple templates for the same catalog",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/ci.yaml": {
                        "fbc": {
                            "catalog_mapping": [
                                {
                                    "template_name": "foo",
                                    "catalog_names": ["1.0", "2.0"],
                                    "type": "olm.template.basic",
                                },
                                {
                                    "template_name": "bar",
                                    "catalog_names": ["3.0", "4.0"],
                                    "type": "olm.template.basic",
                                },
                            ]
                        }
                    }
                },
            ],
            "hello",
            set(),
            id="Operator with no intersection in catalog names",
        ),
    ],
    indirect=False,
)
def test_check_catalog_usage_ci_config(
    tmp_path: Path,
    files: list[dict[str, Any]],
    operator_to_check: str,
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)

    operator = repo.operator(operator_to_check)
    assert {
        (x.__class__, x.reason) for x in check_catalog_usage_ci_config(operator)
    } == expected_results


def test_check_leaks_in_changed_files_no_affected_files(tmp_path: Path) -> None:
    create_files(tmp_path, bundle_files("hello", "0.0.1"))
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    assert list(check_leaks_in_changed_files(operator)) == []


def test_check_leaks_in_changed_files_filters_other_operators(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files("hello", "0.0.1"),
        bundle_files("other", "0.0.1"),
    )
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    set_affected_operator_files(
        [
            "operators/other/0.0.1/manifests/other.clusterserviceversion.yaml",
            "catalogs/v4.15/hello/catalog.yaml",
        ]
    )
    assert list(check_leaks_in_changed_files(operator)) == []


@patch("operatorcert.static_tests.common.operator.paths_with_leaks")
def test_check_leaks_in_changed_files_reports_leaks(
    mock_paths_with_leaks: Any, tmp_path: Path
) -> None:
    create_files(tmp_path, bundle_files("hello", "0.0.1"))
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    leaky_rel = "operators/hello/0.0.1/manifests/hello.clusterserviceversion.yaml"
    leaky_abs = (tmp_path / leaky_rel).resolve()
    set_affected_operator_files([leaky_rel, "operators/hello/missing.yaml"])
    mock_paths_with_leaks.return_value = {leaky_abs}

    results = list(check_leaks_in_changed_files(operator))
    assert len(results) == 1
    assert isinstance(results[0], Fail)
    assert leaky_rel in results[0].reason
    assert "Potential secret leak detected" in results[0].reason
    assert "SUPERSECRET" not in results[0].reason
    mock_paths_with_leaks.assert_called_once()
    scanned_paths = mock_paths_with_leaks.call_args[0]
    assert leaky_abs in scanned_paths


@patch("operatorcert.static_tests.common.operator.paths_with_leaks")
def test_check_leaks_in_changed_files_outside_repo_path(
    mock_paths_with_leaks: Any, tmp_path: Path
) -> None:
    create_files(tmp_path, bundle_files("hello", "0.0.1"))
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    leaky_rel = "operators/hello/0.0.1/manifests/hello.clusterserviceversion.yaml"
    set_affected_operator_files([leaky_rel])
    outside = Path("/tmp/outside-repo-leak")
    mock_paths_with_leaks.return_value = {outside}

    results = list(check_leaks_in_changed_files(operator))
    assert len(results) == 1
    assert str(outside) in results[0].reason


@patch("operatorcert.static_tests.common.operator.paths_with_leaks")
def test_check_leaks_in_changed_files_clean(
    mock_paths_with_leaks: Any, tmp_path: Path
) -> None:
    create_files(tmp_path, bundle_files("hello", "0.0.1"))
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    leaky_rel = "operators/hello/0.0.1/manifests/hello.clusterserviceversion.yaml"
    set_affected_operator_files([leaky_rel])
    mock_paths_with_leaks.return_value = set()

    assert list(check_leaks_in_changed_files(operator)) == []


@patch("operatorcert.static_tests.common.operator.paths_with_leaks")
def test_check_leaks_in_changed_files_scan_error_is_generic(
    mock_paths_with_leaks: Any, tmp_path: Path
) -> None:
    create_files(tmp_path, bundle_files("hello", "0.0.1"))
    repo = Repo(tmp_path)
    operator = repo.operator("hello")
    leaky_rel = "operators/hello/0.0.1/manifests/hello.clusterserviceversion.yaml"
    set_affected_operator_files([leaky_rel])
    secret = "SUPERSECRET_TOKEN_VALUE"
    mock_paths_with_leaks.side_effect = RuntimeError(f"scanner boom {secret}")

    results = list(check_leaks_in_changed_files(operator))
    assert len(results) == 1
    assert isinstance(results[0], Fail)
    assert "internal error" in results[0].reason
    assert secret not in results[0].reason
