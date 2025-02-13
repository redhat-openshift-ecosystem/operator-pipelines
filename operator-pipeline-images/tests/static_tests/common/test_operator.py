from pathlib import Path
import pytest
from operator_repo import Repo
from operator_repo.checks import Fail
from operatorcert.static_tests.common.operator import (
    check_validate_schema_ci_config,
)
from tests.utils import bundle_files, create_files

from typing import Any


@pytest.mark.parametrize(
    "files, bundle_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {"operators/hello/ci.yaml": {"fbc": "hello"}},
            ],
            ("hello", "0.0.1"),
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
            ("hello", "0.0.1"),
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
            ("hello", "0.0.1"),
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
            ("hello", "0.0.1"),
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
                                    "catalog_names": ["1.0", "2.0"],
                                    "type": "olm.template.basic",
                                }
                            ],
                        }
                    }
                },
            ],
            ("hello", "0.0.1"),
            set(),
            id="Testing with all valid fields with required data for ci.yaml schema.",
        ),
    ],
    indirect=False,
)
def test_check_validate_schema_ci_config(
    tmp_path: Path,
    files: list[dict[str, Any]],
    bundle_to_check: tuple[str, str],
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator_name, bundle_version = bundle_to_check
    operator = repo.operator(operator_name)
    assert {
        (x.__class__, x.reason) for x in check_validate_schema_ci_config(operator)
    } == expected_results
