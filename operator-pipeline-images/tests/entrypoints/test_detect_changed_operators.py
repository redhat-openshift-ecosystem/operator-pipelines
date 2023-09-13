import pathlib
import tarfile
from pathlib import Path
from typing import Any
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from git.repo import Repo as GitRepo
import pytest
from operatorcert.entrypoints import detect_changed_operators
from operatorcert.entrypoints.detect_changed_operators import github_pr_affected_files


@pytest.mark.parametrize(
    # The tar file contains an operator repository with the following
    # commits (last to first):
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
    ],
)
@patch("operatorcert.entrypoints.detect_changed_operators.github_pr_affected_files")
def test_detect_changed_operators(
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

    result = detect_changed_operators.detect_changed_operators(
        after_dir,
        before_dir,
        "https://example.com/foo/bar/pull/1",
    )

    for key in set(result.keys()) | set(expected.keys()):
        assert sorted(result[key]) == sorted(
            expected[key]
        ), f"Invalid value for {key}: expected {expected[key]} but {result[key]} was returned"


@patch("operatorcert.entrypoints.detect_changed_operators.detect_changed_operators")
@patch("operatorcert.entrypoints.detect_changed_operators.setup_logger")
def test_detect_changed_operators_main(
    mock_logger: MagicMock, mock_detect: MagicMock, capsys: Any, tmpdir: Any
) -> None:
    args = [
        "detect_changed_operators",
        "--repo-path=/tmp/repo",
        "--base-repo-path=/tmp/base-repo",
        "--pr-url=https://example.com/foo/bar/pull/1",
    ]
    mock_detect.return_value = {"foo": ["bar"]}
    with patch("sys.argv", args):
        detect_changed_operators.main()
    mock_detect.assert_called_once_with(
        pathlib.Path("/tmp/repo"),
        pathlib.Path("/tmp/base-repo"),
        "https://example.com/foo/bar/pull/1",
    )
    assert capsys.readouterr().out.strip() == '{"foo": ["bar"]}'
    mock_logger.assert_called_once_with(level="INFO")

    mock_logger.reset_mock()
    mock_detect.reset_mock()

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
    mock_detect.return_value = {"bar": ["baz"]}
    with patch("sys.argv", args):
        detect_changed_operators.main()
    mock_detect.assert_called_once_with(
        pathlib.Path("/tmp/repo"),
        pathlib.Path("/tmp/base-repo"),
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
