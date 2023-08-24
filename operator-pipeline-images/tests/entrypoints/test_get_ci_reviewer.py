from unittest.mock import MagicMock, patch
from operatorcert.entrypoints.get_ci_reviewer import (
    parse_ci_reviewer,
    main,
    setup_argparser,
)


@patch("operatorcert.entrypoints.get_ci_reviewer.pathlib.Path")
@patch("operatorcert.entrypoints.get_ci_reviewer.load_yaml")
def test_your_function(mock_load_yaml, mock_pathlib_path):
    mock_load_yaml.return_value = {"reviewers": ["lackomacko", "jezkobezko"]}

    operator = "test_operator"

    mock_path = MagicMock()
    mock_pathlib_path.return_value = mock_path

    git_username = "jezkobezko"

    result = parse_ci_reviewer(mock_path, git_username, operator)

    assert result["all_reviewers"] == ["lackomacko", "jezkobezko"]
    assert result["is_reviewer"] == "true"


@patch("operatorcert.entrypoints.get_ci_reviewer.load_yaml")
@patch("operatorcert.entrypoints.get_ci_reviewer.setup_argparser")
def test_main(mock_setup_argparser: MagicMock, mock_load_yaml: MagicMock):
    mock_load_yaml.return_value = {"reviewers": ["lackomacko", "jezkobezko"]}
    args = MagicMock()
    args.repo_path = "/repo/path/"
    args.git_username = "lackomacko"
    args.operator_name = "test_operator"
    mock_setup_argparser.return_value.parse_args.return_value = args

    main()


def test_setup_argparser():
    assert setup_argparser() is not None
