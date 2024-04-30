from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from operator_repo import Repo
from operator_repo.checks import Fail, Warn
from operatorcert.static_tests.common.bundle import check_operator_name
from tests.utils import bundle_files, create_files

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
