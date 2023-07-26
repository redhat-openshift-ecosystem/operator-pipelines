import pathlib
import tarfile
from unittest.mock import MagicMock, patch

import pytest

from operatorcert.entrypoints import detect_changed_operators


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
    False,
    [
        "Add new bundle for new operator",
        "Add new bundle for existing operator",
        "Add bundles for multiple operators",
        "Modify bundles for multiple operators and add extra files",
        "Delete a bundle and remove extra files",
        "Add ci.yaml to an operator",
        "Delete an operator",
    ],
)
def test_detect_changed_operators(tmp_path, head_commit, base_commit, expected):
    data_dir = pathlib.Path(__file__).parent.parent.resolve() / "data"
    tar = tarfile.open(str(data_dir / "test-repo.tar"))
    tar.extractall(tmp_path)

    result = detect_changed_operators.detect_changed_operators(
        str(tmp_path), head_commit, base_commit
    )

    for key in set(result.keys()) | set(expected.keys()):
        assert sorted(result[key]) == sorted(
            expected[key]
        ), f"Invalid value for {key}: expected {expected[key]} but {result[key]} was returned"


@patch("operatorcert.entrypoints.detect_changed_operators.detect_changed_operators")
@patch("operatorcert.entrypoints.detect_changed_operators.setup_logger")
def test_detect_changed_operators_main(
    mock_logger: MagicMock, mock_detect: MagicMock, capsys, tmpdir
) -> None:
    args = [
        "detect_changed_operators",
        "--repo-path=/tmp/repo",
        "--head-commit=2",
        "--base-commit=1",
    ]
    mock_detect.return_value = {"foo": ["bar"]}
    with patch("sys.argv", args):
        detect_changed_operators.main()
    mock_detect.assert_called_once_with("/tmp/repo", "2", "1")
    assert capsys.readouterr().out.strip() == '{"foo": ["bar"]}'
    mock_logger.assert_called_once_with(level="INFO")

    mock_logger.reset_mock()
    mock_detect.reset_mock()

    out_file = tmpdir / "out.json"
    out_file_name = str(out_file)
    args = [
        "detect_changed_operators",
        "--repo-path=/tmp/other_repo",
        "--head-commit=4",
        "--base-commit=3",
        f"--output-file={out_file_name}",
        "--verbose",
    ]
    mock_detect.return_value = {"bar": ["baz"]}
    with patch("sys.argv", args):
        detect_changed_operators.main()
    mock_detect.assert_called_once_with("/tmp/other_repo", "4", "3")
    assert out_file.read().strip() == '{"bar": ["baz"]}'
    mock_logger.assert_called_once_with(level="DEBUG")
