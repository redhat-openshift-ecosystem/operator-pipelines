from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from operator_repo import Repo
from operator_repo.checks import Fail, Warn
from operatorcert.static_tests.common.bundle import check_operator_name
from tests.utils import bundle_files, create_files

from typing import Any


@pytest.mark.parametrize(
    "files, bundle_to_check, expected_results",
    [
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
            ],
            ("hello", "0.0.1"),
            set(),
            id="Names ok",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                    annotations={
                        "operators.operatorframework.io.bundle.package.v1": "foo"
                    },
                ),
            ],
            ("hello", "0.0.1"),
            {
                (
                    Fail,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the operator's directory name (hello)",
                ),
                (
                    Fail,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the name defined in the CSV (hello)",
                ),
            },
            id="Wrong annotations.yaml name",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                {
                    "operators/hello/0.0.1/metadata/annotations.yaml": {
                        "annotations": {}
                    }
                },
            ],
            ("hello", "0.0.1"),
            {
                (Fail, "Bundle does not define the operator name in annotations.yaml"),
            },
            id="Empty annotations.yaml",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files(
                    "hello",
                    "0.0.2",
                    annotations={
                        "operators.operatorframework.io.bundle.package.v1": "foo"
                    },
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                    annotations={
                        "operators.operatorframework.io.bundle.package.v1": "foo"
                    },
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the operator's directory name (hello)",
                ),
                (
                    Warn,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the name defined in the CSV (hello)",
                ),
                (
                    Warn,
                    "Operator name from annotations.yaml is not consistent"
                    " across bundles: ['foo', 'hello']",
                ),
            },
            id="Wrong annotations.yaml name, inconsistent bundles",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files(
                    "hello",
                    "0.0.2",
                    csv={"metadata": {"name": "foo.v0.0.2"}},
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                    csv={"metadata": {"name": "foo.v0.0.3"}},
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (hello) does not match"
                    " the name defined in the CSV (foo)",
                ),
                (
                    Warn,
                    "Operator name from the CSV is not consistent across bundles: ['foo', 'hello']",
                ),
            },
            id="Wrong CSV name, inconsistent bundles",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files("hello", "0.0.2"),
                bundle_files(
                    "hello",
                    "0.0.3",
                    annotations={
                        "operators.operatorframework.io.bundle.package.v1": "foo"
                    },
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the operator's directory name (hello)",
                ),
                (
                    Warn,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the name defined in the CSV (hello)",
                ),
                (
                    Fail,
                    "Operator name from annotations.yaml (foo) does not match"
                    " the name defined in other bundles (hello)",
                ),
            },
            id="Wrong annotations.yaml name, consistent bundles",
        ),
        pytest.param(
            [
                bundle_files("hello", "0.0.1"),
                bundle_files("hello", "0.0.2"),
                bundle_files(
                    "hello",
                    "0.0.3",
                    csv={"metadata": {"name": "foo.v0.0.3"}},
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (hello) does not match"
                    " the name defined in the CSV (foo)",
                ),
                (
                    Fail,
                    "Operator name from the CSV (foo) does not match the name"
                    " defined in other bundles (hello)",
                ),
            },
            id="Wrong CSV name, consistent bundles",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                    csv={"metadata": {"name": "foo.v0.0.1"}},
                ),
                bundle_files(
                    "hello",
                    "0.0.2",
                    csv={"metadata": {"name": "foo.v0.0.2"}},
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                    csv={"metadata": {"name": "foo.v0.0.3"}},
                ),
            ],
            ("hello", "0.0.3"),
            {
                (
                    Warn,
                    "Operator name from annotations.yaml (hello) does not match"
                    " the name defined in the CSV (foo)",
                ),
            },
            id="Wrong CSV name in all bundles",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                    csv={"metadata": {"name": "hello"}},
                ),
                bundle_files(
                    "hello",
                    "0.0.2",
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                ),
            ],
            ("hello", "0.0.3"),
            set(),
            id="Invalid CSV name in old bundle",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                bundle_files(
                    "hello",
                    "0.0.2",
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                    csv={"metadata": {"name": "hello"}},
                ),
            ],
            ("hello", "0.0.3"),
            {
                (Fail, "Invalid operator name in CSV for Bundle(hello/0.0.3)"),
            },
            id="Invalid CSV name in new bundle",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                {"operators/hello/0.0.1/metadata/annotations.yaml": ":invalid"},
                bundle_files(
                    "hello",
                    "0.0.2",
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                ),
            ],
            ("hello", "0.0.3"),
            set(),
            id="Invalid annotations.yaml name in old bundle",
        ),
        pytest.param(
            [
                bundle_files(
                    "hello",
                    "0.0.1",
                ),
                bundle_files(
                    "hello",
                    "0.0.2",
                ),
                bundle_files(
                    "hello",
                    "0.0.3",
                ),
                {"operators/hello/0.0.3/metadata/annotations.yaml": ":invalid"},
            ],
            ("hello", "0.0.3"),
            {
                (
                    Fail,
                    "Invalid operator name in annotations.yaml for Bundle(hello/0.0.3)",
                ),
            },
            id="Invalid annotations.yaml name in new bundle",
        ),
    ],
    indirect=False,
)
def test_operator_name(
    tmp_path: Path,
    files: list[dict[str, Any]],
    bundle_to_check: tuple[str, str],
    expected_results: set[tuple[type, str]],
) -> None:
    create_files(tmp_path, *files)
    repo = Repo(tmp_path)
    operator_name, bundle_version = bundle_to_check
    operator = repo.operator(operator_name)
    bundle = operator.bundle(bundle_version)
    assert {
        (x.__class__, x.reason) for x in check_operator_name(bundle)
    } == expected_results
