from unittest.mock import MagicMock, patch

from operatorcert import buildah


@patch("operatorcert.buildah.run_command")
def test_build_image(mock_run_command: MagicMock) -> None:
    result = buildah.build_image("dockerfile", "context", "image")
    assert result == mock_run_command.return_value

    mock_run_command.assert_called_once_with(
        [
            "buildah",
            "bud",
            "--format",
            "docker",
            "-f",
            "dockerfile",
            "-t",
            "image",
            "context",
        ]
    )


@patch("operatorcert.buildah.run_command")
def test_push_image(mock_run_command: MagicMock) -> None:
    result = buildah.push_image("image", "authfile")
    assert result == mock_run_command.return_value

    mock_run_command.assert_called_once_with(
        ["buildah", "push", "--authfile", "authfile", "image", "docker://image"]
    )
