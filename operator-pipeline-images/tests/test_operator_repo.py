import pathlib

import pytest
from operatorcert.operator_repo import (
    Repo,
    InvalidRepoException,
    InvalidOperatorException,
    InvalidBundleException,
)

OPERATOR_REPO_PATH = str(
    pathlib.Path(__file__).parent.resolve() / "data" / "operator-repo"
)


def test_repo() -> None:
    repo = Repo(OPERATOR_REPO_PATH)
    assert repo.root() == OPERATOR_REPO_PATH
    # assert len(set(repo)) == 4
    assert OPERATOR_REPO_PATH in repr(repo)
    assert repo.config == {}


def test_repo_invalid(tmp_path) -> None:
    with pytest.raises(InvalidRepoException):
        Repo(tmp_path)


def test_operator() -> None:
    repo = Repo(OPERATOR_REPO_PATH)
    op1 = repo.operator("operator-e2e")
    op2 = repo.operator("operator-clone-e2e")
    op3 = repo.operator("invalid-operator")
    op4 = repo.operator("operator-no-semver")
    with pytest.raises(InvalidOperatorException):
        repo.operator("empty-operator")
    assert op1 != op2
    assert op1 == repo.operator("operator-e2e")
    assert "operator-e2e" in repr(op1)
    assert set(repo) == {op1, op2, op3, op4}
    assert len(set(op1)) == 1
    assert len(set(op2)) == 2
    assert op2 < op1
    assert op1.root() == repo.root() + "/operators/operator-e2e"
    assert op1.config == {}


def test_bundle() -> None:
    repo = Repo(OPERATOR_REPO_PATH)
    bundle1 = repo.operator("operator-clone-e2e").bundle("0.0.100")
    bundle2 = repo.operator("operator-clone-e2e").bundle("0.0.101")
    bundle3 = repo.operator("operator-e2e").bundle("0.0.100")
    with pytest.raises(InvalidBundleException, match="missing .metadata.name"):
        _ = repo.operator("invalid-operator").bundle("0.0.1")
    with pytest.raises(InvalidBundleException, match="not found"):
        _ = repo.operator("invalid-operator").bundle("0.0.2")
    with pytest.raises(InvalidBundleException, match="Not a valid bundle"):
        _ = repo.operator("invalid-operator").bundle("0.0.3")
    assert bundle1 != bundle2
    assert bundle2 != bundle3
    assert "operator-clone-e2e/0.0.100" in repr(bundle1)
    assert "operator-clone-e2e/0.0.101" in repr(bundle2)
    assert bundle1 < bundle2
    with pytest.raises(ValueError):
        _ = repo.operator("operator-e2e").bundle("0.0.100") < bundle2
    assert (
        bundle3.annotations["operators.operatorframework.io.bundle.package.v1"]
        == "operator-e2e"
    )
    assert bundle1.operator() == repo.operator("operator-clone-e2e")
    assert bundle2.root() == repo.operator("operator-clone-e2e").root() + "/0.0.101"
    assert bundle1.dependencies == []
    bundle4 = repo.operator("operator-no-semver").bundle("0.0.99.0")
    bundle5 = repo.operator("operator-no-semver").bundle("0.0.100.0")
    assert bundle4 != bundle5
    assert bundle4 > bundle5
