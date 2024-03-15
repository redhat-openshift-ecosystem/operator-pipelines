from pathlib import Path
from typing import Any

import pytest
from operator_repo import Repo
from operator_repo.checks import Fail, Warn
from operatorcert.static_tests.community.operator import (
    check_ci_upgrade_graph,
    check_operator_name_unique,
)
from tests.utils import bundle_files, create_files


def test_check_operator_name_unique(tmp_path: Path) -> None:
    create_files(tmp_path, bundle_files("test-operator", "0.0.1"))
    repo = Repo(tmp_path)
    operator = repo.operator("test-operator")
    assert list(check_operator_name_unique(operator)) == []
    create_files(
        tmp_path,
        bundle_files(
            "test-operator",
            "0.0.2",
            csv={"metadata": {"name": "other-operator.v0.0.2"}},
        ),
    )
    assert [x.kind for x in check_operator_name_unique(operator)] == ["failure"]


@pytest.mark.parametrize(
    "graph_mode, expected",
    [
        pytest.param(
            "",
            {
                Warn(
                    "The 'updateGraph' option is missing in ci.yaml. The default upgrade graph 'replaces-mode' will be used."
                )
            },
            id="empty",
        ),
        pytest.param(
            "replaces-mode",
            set(),
            id="replaces",
        ),
        pytest.param(
            "semver-mode",
            set(),
            id="semver",
        ),
        pytest.param(
            "unknown-mode",
            {
                Fail(
                    "The 'updateGraph' option in ci.yaml must be one of ['replaces-mode', 'semver-mode']",
                )
            },
            id="unknown",
        ),
    ],
)
def test_check_ci_upgrade_graph(graph_mode: str, expected: Any, tmp_path: Path) -> None:
    create_files(
        tmp_path,
        bundle_files(
            "test-operator",
            "0.0.1",
            other_files={
                "operators/test-operator/ci.yaml": {"updateGraph": graph_mode}
            },
        ),
    )
    repo = Repo(tmp_path)
    operator = repo.operator("test-operator")
    result = check_ci_upgrade_graph(operator)

    assert set(result) == expected
