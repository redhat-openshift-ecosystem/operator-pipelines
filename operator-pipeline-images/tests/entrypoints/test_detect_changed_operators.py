import pathlib
import tarfile
from pathlib import Path
from typing import Any
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from git.repo import Repo as GitRepo
import pytest
from operatorcert.entrypoints import detect_changed_operators
from operatorcert.entrypoints.detect_changed_operators import (
    github_pr_affected_files,
    ValidationError,
)
from operator_repo import Repo


@pytest.mark.parametrize(
    # The tar file contains an operator repository with the following
    # commits (last to first):
    # 1ca2aa1 Delete 4.15 catalog
    # 8500957 Remove operator-2 from v4.15
    # ff7cdcd Update operator-1 in 4.15 catalog
    # 4db21de Add operator-2 to 4.15 catalog
    # c8d3509 Add 4.15 catalog with operator-1
    # 2e9eae2 Remove operator-clone-e2e
    # a5501e2 Add ci.yaml to operator-clone-e2e
    # 2c06647 Remove extra files
    # 4143429 Remove operator-e2e/0.0.101
    # 2d55a2e Add extra files
    # 9f7ef05 Modify operator-e2e/0.0.101
    # ad1e1de Modify operator-clone-e2e/0.0.100
    # 6626c9a Add operator-clone-e2e/0.0.100
    # 32e0f85 Add operator-e2e/0.0.101
    # 6a75661 Add operator-e2e/0.0.100
    # db1a066 Empty repo
    "head_commit, base_commit, expected",
    [
        (
            "6a75661",
            # Add operator-e2e/0.0.100
            # Empty repo
            "db1a066",
            {
                "extra_files": [],
                "affected_operators": ["operator-e2e"],
                "added_operators": ["operator-e2e"],
                "modified_operators": [],
                "deleted_operators": [],
                "affected_bundles": ["operator-e2e/0.0.100"],
                "added_bundles": ["operator-e2e/0.0.100"],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": [],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": [],
                "added_catalogs": [],
                "modified_catalogs": [],
                "deleted_catalogs": [],
            },
        ),
        (
            "32e0f85",
            # Add operator-e2e/0.0.101
            # Add operator-e2e/0.0.100
            "6a75661",
            {
                "extra_files": [],
                "affected_operators": ["operator-e2e"],
                "added_operators": [],
                "modified_operators": ["operator-e2e"],
                "deleted_operators": [],
                "affected_bundles": ["operator-e2e/0.0.101"],
                "added_bundles": ["operator-e2e/0.0.101"],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": [],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": [],
                "added_catalogs": [],
                "modified_catalogs": [],
                "deleted_catalogs": [],
            },
        ),
        (
            "6626c9a",
            # Add operator-clone-e2e/0.0.100
            # Add operator-e2e/0.0.101
            # Add operator-e2e/0.0.100
            "6a75661",
            {
                "extra_files": [],
                "affected_operators": ["operator-e2e", "operator-clone-e2e"],
                "added_operators": ["operator-clone-e2e"],
                "modified_operators": ["operator-e2e"],
                "deleted_operators": [],
                "affected_bundles": [
                    "operator-e2e/0.0.101",
                    "operator-clone-e2e/0.0.100",
                ],
                "added_bundles": ["operator-e2e/0.0.101", "operator-clone-e2e/0.0.100"],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": [],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": [],
                "added_catalogs": [],
                "modified_catalogs": [],
                "deleted_catalogs": [],
            },
        ),
        (
            "2d55a2e",
            # Add extra files
            # Modify operator-e2e/0.0.101
            # Modify operator-clone-e2e/0.0.100
            # Add operator-clone-e2e/0.0.100
            "6626c9a",
            {
                "extra_files": ["empty.txt", "operators/empty.txt"],
                "affected_operators": ["operator-e2e", "operator-clone-e2e"],
                "added_operators": [],
                "modified_operators": ["operator-e2e", "operator-clone-e2e"],
                "deleted_operators": [],
                "affected_bundles": [
                    "operator-e2e/0.0.101",
                    "operator-clone-e2e/0.0.100",
                ],
                "added_bundles": [],
                "modified_bundles": [
                    "operator-e2e/0.0.101",
                    "operator-clone-e2e/0.0.100",
                ],
                "deleted_bundles": [],
                "affected_catalog_operators": [],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": [],
                "added_catalogs": [],
                "modified_catalogs": [],
                "deleted_catalogs": [],
            },
        ),
        (
            "2c06647",
            # Remove extra files
            # Remove operator-e2e/0.0.101
            # Add extra files
            "2d55a2e",
            {
                "extra_files": ["empty.txt", "operators/empty.txt"],
                "affected_operators": ["operator-e2e"],
                "added_operators": [],
                "modified_operators": ["operator-e2e"],
                "deleted_operators": [],
                "affected_bundles": ["operator-e2e/0.0.101"],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": ["operator-e2e/0.0.101"],
                "affected_catalog_operators": [],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": [],
                "added_catalogs": [],
                "modified_catalogs": [],
                "deleted_catalogs": [],
            },
        ),
        (
            "a5501e2",
            # Add ci.yaml to operator-clone-e2e
            # Remove extra files
            "2c06647",
            {
                "extra_files": [],
                "affected_operators": ["operator-clone-e2e"],
                "added_operators": [],
                "modified_operators": ["operator-clone-e2e"],
                "deleted_operators": [],
                "affected_bundles": [],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": [],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": [],
                "added_catalogs": [],
                "modified_catalogs": [],
                "deleted_catalogs": [],
            },
        ),
        (
            "2e9eae2",
            # Remove operator-clone-e2e
            # Add ci.yaml to operator-clone-e2e
            "a5501e2",
            {
                "extra_files": [],
                "affected_operators": ["operator-clone-e2e"],
                "added_operators": [],
                "modified_operators": [],
                "deleted_operators": ["operator-clone-e2e"],
                "affected_bundles": ["operator-clone-e2e/0.0.100"],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": ["operator-clone-e2e/0.0.100"],
                "affected_catalog_operators": [],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": [],
                "added_catalogs": [],
                "modified_catalogs": [],
                "deleted_catalogs": [],
            },
        ),
        (
            "c8d3509f",
            # Add v4.15/operator-1
            "2e9eae2",
            {
                "extra_files": [],
                "affected_operators": [],
                "added_operators": [],
                "modified_operators": [],
                "deleted_operators": [],
                "affected_bundles": [],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": ["v4.15/operator-1"],
                "added_catalog_operators": ["v4.15/operator-1"],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": ["v4.15"],
                "added_catalogs": ["v4.15"],
                "modified_catalogs": [],
                "deleted_catalogs": [],
            },
        ),
        (
            "4db21de1",
            # Add v4.15/operator-2
            "c8d3509f",
            {
                "extra_files": [],
                "affected_operators": [],
                "added_operators": [],
                "modified_operators": [],
                "deleted_operators": [],
                "affected_bundles": [],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": ["v4.15/operator-2"],
                "added_catalog_operators": ["v4.15/operator-2"],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": [],
                "affected_catalogs": ["v4.15"],
                "added_catalogs": [],
                "modified_catalogs": ["v4.15"],
                "deleted_catalogs": [],
            },
        ),
        (
            "ff7cdcd6",
            # Modify v4.15/operator-1
            "4db21de1",
            {
                "extra_files": [],
                "affected_operators": [],
                "added_operators": [],
                "modified_operators": [],
                "deleted_operators": [],
                "affected_bundles": [],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": ["v4.15/operator-1"],
                "added_catalog_operators": [],
                "modified_catalog_operators": ["v4.15/operator-1"],
                "deleted_catalog_operators": [],
                "affected_catalogs": ["v4.15"],
                "added_catalogs": [],
                "modified_catalogs": ["v4.15"],
                "deleted_catalogs": [],
            },
        ),
        (
            "85009570",
            # Delete v4.15/operator-2
            "ff7cdcd6",
            {
                "extra_files": [],
                "affected_operators": [],
                "added_operators": [],
                "modified_operators": [],
                "deleted_operators": [],
                "affected_bundles": [],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": ["v4.15/operator-2"],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": ["v4.15/operator-2"],
                "affected_catalogs": ["v4.15"],
                "added_catalogs": [],
                "modified_catalogs": ["v4.15"],
                "deleted_catalogs": [],
            },
        ),
        (
            "1ca2aa12",
            # Delete v4.15 catalog
            "85009570",
            {
                "extra_files": [],
                "affected_operators": [],
                "added_operators": [],
                "modified_operators": [],
                "deleted_operators": [],
                "affected_bundles": [],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalog_operators": ["v4.15/operator-1"],
                "added_catalog_operators": [],
                "modified_catalog_operators": [],
                "deleted_catalog_operators": ["v4.15/operator-1"],
                "affected_catalogs": ["v4.15"],
                "added_catalogs": [],
                "modified_catalogs": [],
                "deleted_catalogs": ["v4.15"],
            },
        ),
        (
            "ff7cdcd",
            # Modify v4.15/operator-1
            # Add v4.15/operator-2
            # Empty repo
            "c8d3509",
            {
                "affected_operators": [],
                "added_operators": [],
                "modified_operators": [],
                "deleted_operators": [],
                "affected_bundles": [],
                "added_bundles": [],
                "modified_bundles": [],
                "deleted_bundles": [],
                "affected_catalogs": ["v4.15"],
                "added_catalogs": [],
                "modified_catalogs": ["v4.15"],
                "deleted_catalogs": [],
                "affected_catalog_operators": ["v4.15/operator-1", "v4.15/operator-2"],
                "added_catalog_operators": ["v4.15/operator-2"],
                "modified_catalog_operators": ["v4.15/operator-1"],
                "deleted_catalog_operators": [],
                "extra_files": [],
            },
        ),
    ],
    indirect=False,
    ids=[
        "Add new bundle for new operator",
        "Add new bundle for existing operator",
        "Add bundles for multiple operators",
        "Modify bundles for multiple operators and add extra files",
        "Delete a bundle and remove extra files",
        "Add ci.yaml to an operator",
        "Delete an operator",
        "Add new catalog with new operator",
        "Add new operator to existing catalog",
        "Modify operator in existing catalog",
        "Delete operator in existing catalog",
        "Delete catalog",
        "Modify operator in existing catalog and add new operator",
    ],
)
@patch("operatorcert.entrypoints.detect_changed_operators.github_pr_affected_files")
def test_detect_changes(
    mock_affected_files: MagicMock,
    tmp_path: pathlib.Path,
    head_commit: str,
    base_commit: str,
    expected: Any,
) -> None:
    data_dir = pathlib.Path(__file__).parent.parent.resolve() / "data"
    tar = tarfile.open(str(data_dir / "test-repo.tar"))
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()
    tar.extractall(before_dir)
    tar.extractall(after_dir)
    before_git = GitRepo(before_dir)
    after_git = GitRepo(after_dir)
    before_git.head.reset(base_commit, index=True, working_tree=True)
    after_git.head.reset(head_commit, index=True, working_tree=True)

    affected_files = {
        y
        for x in after_git.head.commit.diff(base_commit)
        for y in (x.a_path, x.b_path)
        if y
        is not None  # According to the GitPython docs, a_path and b_path can be None
    }
    mock_affected_files.return_value = affected_files

    result = detect_changed_operators.detect_changes(
        Repo(after_dir),
        Repo(before_dir),
        "https://example.com/foo/bar/pull/1",
    )
    print(result)
    for key in set(result.keys()) | set(expected.keys()):
        assert sorted(result[key]) == sorted(
            expected[key]
        ), f"Invalid value for {key}: expected {expected[key]} but {result[key]} was returned"


@patch("operatorcert.entrypoints.detect_changed_operators._update_result")
@patch("operatorcert.entrypoints.detect_changed_operators.OperatorRepo")
@patch("operatorcert.entrypoints.detect_changed_operators.detect_changes")
@patch("operatorcert.entrypoints.detect_changed_operators.setup_logger")
def test_detect_changed_operators_main(
    mock_logger: MagicMock,
    mock_detect: MagicMock,
    mock_repo: MagicMock,
    mock_update: MagicMock,
    capsys: Any,
    tmpdir: Any,
) -> None:
    args = [
        "detect_changed_operators",
        "--repo-path=/tmp/repo",
        "--base-repo-path=/tmp/base-repo",
        "--pr-url=https://example.com/foo/bar/pull/1",
    ]
    return_value = {"foo": ["bar"]}
    mock_detect.return_value = return_value
    mock_update.return_value = return_value
    repo_head = MagicMock()
    repo_base = MagicMock()
    mock_repo.side_effect = [repo_head, repo_base, repo_head, repo_base]
    with patch("sys.argv", args):
        detect_changed_operators.main()
    mock_detect.assert_called_once_with(
        repo_head,
        repo_base,
        "https://example.com/foo/bar/pull/1",
    )
    assert capsys.readouterr().out.strip() == '{"foo": ["bar"]}'
    mock_logger.assert_called_once_with(level="INFO")

    mock_logger.reset_mock()
    mock_detect.reset_mock()
    mock_update.reset_mock()

    out_file = tmpdir / "out.json"
    out_file_name = str(out_file)
    args = [
        "detect_changed_operators",
        "--repo-path=/tmp/repo",
        "--base-repo-path=/tmp/base-repo",
        "--pr-url=https://example.com/foo/bar/pull/1",
        f"--output-file={out_file_name}",
        "--verbose",
    ]
    return_value = {"bar": ["baz"]}
    mock_detect.return_value = return_value
    mock_update.return_value = return_value
    with patch("sys.argv", args):
        detect_changed_operators.main()
    mock_detect.assert_called_once_with(
        repo_head,
        repo_base,
        "https://example.com/foo/bar/pull/1",
    )
    assert out_file.read().strip() == '{"bar": ["baz"]}'
    mock_logger.assert_called_once_with(level="DEBUG")


@pytest.fixture
def mock_pull() -> MagicMock:
    @dataclass
    class FileMock:
        filename: str

    result = MagicMock()
    result.get_files = MagicMock(
        return_value=[FileMock("foo.txt"), FileMock("bar.yaml")]
    )
    return result


@patch("operatorcert.entrypoints.detect_changed_operators.Auth.Token")
@patch("operatorcert.entrypoints.detect_changed_operators.Github")
def test_github_pr_affected_files(
    mock_github: MagicMock,
    mock_token: MagicMock,
    mock_pull: MagicMock,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    mock_token.return_value = "auth_result"

    mock_repo = MagicMock()
    mock_repo.get_pull = MagicMock(return_value=mock_pull)
    mock_gh = MagicMock()
    mock_gh.get_repo = MagicMock(return_value=mock_repo)
    mock_github.return_value = mock_gh

    assert github_pr_affected_files("https://example.com/foo/bar/pull/123") == {
        "foo.txt",
        "bar.yaml",
    }
    mock_github.assert_called_once_with(auth="auth_result")
    mock_gh.get_repo.assert_called_once_with("foo/bar")
    mock_repo.get_pull.assert_called_once_with(123)
    mock_pull.get_files.assert_called_once()


@patch("operatorcert.entrypoints.detect_changed_operators.Github")
def test_github_pr_affected_files_no_token(
    mock_github: MagicMock,
    mock_pull: MagicMock,
    monkeypatch: Any,
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    mock_repo = MagicMock()
    mock_repo.get_pull = MagicMock(return_value=mock_pull)
    mock_gh = MagicMock()
    mock_gh.get_repo = MagicMock(return_value=mock_repo)
    mock_github.return_value = mock_gh

    assert github_pr_affected_files("https://example.com/foo/bar/pull/123") == {
        "foo.txt",
        "bar.yaml",
    }
    mock_github.assert_called_once_with()
    mock_gh.get_repo.assert_called_once_with("foo/bar")
    mock_repo.get_pull.assert_called_once_with(123)
    mock_pull.get_files.assert_called_once()


def test_github_pr_affected_files_invalid_url(
    monkeypatch: Any,
) -> None:
    with pytest.raises(ValueError):
        github_pr_affected_files("http://example.com/invalid/url")


@pytest.mark.parametrize(
    "result, valid, message",
    [
        pytest.param(
            {
                "extra_files": ["empty.txt", "operators/empty.txt"],
                "affected_operators": ["operator-e2e", "operator-clone-e2e"],
                "modified_bundles": ["operator-e2e/0.0.101"],
                "deleted_bundles": ["operator-clone-e2e/0.0.100"],
                "added_bundles": ["operator-e2e/0.0.101", "operator-clone-e2e/0.0.100"],
                "affected_catalog_operators": ["v4.15/operator-1", "v4.15/operator-2"],
            },
            False,
            "The PR affects non-operator files: ['empty.txt', 'operators/empty.txt']\n"
            "The PR affects more than one operator: ['operator-clone-e2e', 'operator-e2e']\n"
            "The PR modifies existing bundles: ['operator-e2e/0.0.101']\n"
            "The PR deletes existing bundles: ['operator-clone-e2e/0.0.100']\n"
            "The PR affects more than one bundle: ['operator-clone-e2e/0.0.100', 'operator-e2e/0.0.101']\n"
            "The PR affects more than one catalog operator: ['operator-1', 'operator-2']",
            id="Invalid changes detected",
        ),
        pytest.param(
            {
                "extra_files": [],
                "affected_operators": ["operator-e2e"],
                "modified_bundles": [],
                "deleted_bundles": [],
                "added_bundles": ["operator-e2e/0.0.101"],
                "affected_catalog_operators": ["v4.15/operator-1", "v4.16/operator-1"],
            },
            True,
            None,
            id="Valid result",
        ),
    ],
)
def test__validate_result(result: dict[str, Any], valid: bool, message: str) -> None:
    if valid:
        detect_changed_operators._validate_result(result)
    else:
        with pytest.raises(ValidationError) as exc:
            detect_changed_operators._validate_result(result)
        assert str(exc.value) == message


@pytest.mark.parametrize(
    "result, expected",
    [
        pytest.param(
            {
                "added_bundles": ["operator-e2e/0.0.101"],
                "affected_operators": ["operator-e2e"],
            },
            {
                "added_bundles": ["operator-e2e/0.0.101"],
                "affected_operators": ["operator-e2e"],
                "operator_name": "operator-e2e",
                "bundle_version": "0.0.101",
                "operator_path": "operators/operator-e2e",
                "bundle_path": "operators/operator-e2e/0.0.101",
            },
            id="Bundle is added",
        ),
        pytest.param(
            {
                "added_bundles": [],
                "affected_operators": ["operator-e2e"],
            },
            {
                "added_bundles": [],
                "affected_operators": ["operator-e2e"],
                "operator_name": "operator-e2e",
                "bundle_version": "",
                "operator_path": "operators/operator-e2e",
                "bundle_path": "",
            },
            id="Operator is updated",
        ),
        pytest.param(
            {
                "added_bundles": [],
                "affected_operators": [],
            },
            {
                "added_bundles": [],
                "affected_operators": [],
                "operator_name": "",
                "bundle_version": "",
                "operator_path": "",
                "bundle_path": "",
            },
            id="No bundle added or operator affected",
        ),
    ],
)
def test__update_result(result: dict[str, Any], expected: dict[str, Any]) -> None:
    assert detect_changed_operators._update_result(result) == expected
