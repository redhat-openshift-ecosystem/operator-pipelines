from typing import Any
from unittest.mock import MagicMock, patch

from operatorcert.entrypoints.github_labels import main, setup_argparser


@patch("operatorcert.entrypoints.github_labels.add_or_remove_labels")
@patch("operatorcert.entrypoints.github_labels.Github")
@patch("operatorcert.entrypoints.github_labels.setup_logger")
@patch("operatorcert.entrypoints.github_labels.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_github: MagicMock,
    mock_add_or_remove_labels: MagicMock,
    monkeypatch: Any,
) -> None:
    args = MagicMock()
    args.add_labels = ["label1"]
    args.remove_labels = ["label2"]
    args.remove_matching_namespace_labels = True
    args.pull_request_url = "https://github.com/foo/bar/pull/123"
    mock_setup_argparser.return_value.parse_args.return_value = args

    monkeypatch.setenv("GITHUB_TOKEN", "foo_api_token")
    main()

    mock_add_or_remove_labels.assert_called_once_with(
        mock_github(),
        "https://github.com/foo/bar/pull/123",
        ["label1"],
        ["label2"],
        True,
    )


def test_setup_argparser() -> None:
    assert setup_argparser() is not None
