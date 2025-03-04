from pathlib import Path
from typing import Any
from unittest.mock import PropertyMock, patch

import pytest
from operatorcert.operator_repo import Repo
from operatorcert.operator_repo.checks import Fail, Warn
from operatorcert.static_tests.community.operator import (
    check_ci_upgrade_graph,
    check_operator_name_unique,
    check_upgrade_graph_loop,
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
        is_loop = list(check_upgrade_graph_loop(operator))
        assert is_loop == []

    with patch.object(
        type(operator), "config", new_callable=PropertyMock
    ) as mock_config:
        mock_config.return_value = {"updateGraph": "unknown-mode"}
        is_loop = list(check_upgrade_graph_loop(operator))
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
        is_loop = list(check_upgrade_graph_loop(operator))
        assert len(is_loop) == 1 and isinstance(is_loop[0], Fail)
        assert (
            "Upgrade graph loop detected:" in is_loop[0].reason
            and "Bundle(hello/0.0.1)" in is_loop[0].reason
            and "Bundle(hello/0.0.2)" in is_loop[0].reason
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
        failures = list(check_upgrade_graph_loop(operator))
        assert len(failures) == 1 and isinstance(failures[0], Fail)
        assert (
            "Bundle(malformed/0.0.1) has invalid 'replaces' field:"
            in failures[0].reason
        )
