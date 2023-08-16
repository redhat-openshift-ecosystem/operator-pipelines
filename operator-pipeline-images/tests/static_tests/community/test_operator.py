from pathlib import Path

from operator_repo import Repo

from operatorcert.static_tests.community.operator import check_operator_name
from tests.utils import create_files, bundle_files


def test_check_operator_name(tmp_path: Path) -> None:
    create_files(tmp_path, bundle_files("test-operator", "0.0.1"))
    repo = Repo(tmp_path)
    operator = repo.operator("test-operator")
    assert list(check_operator_name(operator)) == []
    create_files(
        tmp_path,
        bundle_files(
            "test-operator",
            "0.0.2",
            csv={"metadata": {"name": "other-operator.v0.0.2"}},
        ),
    )
    assert [x.kind for x in check_operator_name(operator)] == ["failure"]
