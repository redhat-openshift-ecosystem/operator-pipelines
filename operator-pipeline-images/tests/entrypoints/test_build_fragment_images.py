from pathlib import Path
from typing import Any
from unittest import mock
from unittest.mock import MagicMock, patch, call

import operatorcert.entrypoints.build_fragment_images as build_fragment_images
from tests.utils import create_files


@patch("operatorcert.entrypoints.build_fragment_images.os.remove")
@patch("operatorcert.entrypoints.build_fragment_images.os.path.exists")
@patch("operatorcert.entrypoints.build_fragment_images.run_command")
def test_create_dockerfilee(
    mock_run_command: MagicMock, mock_exists: MagicMock, mock_remove: MagicMock
) -> None:
    mock_exists.return_value = True

    result = build_fragment_images.create_dockerfile("catalogs", "catalog1")
    assert result == "catalogs/catalog1.Dockerfile"

    mock_remove.assert_called_once_with("catalogs/catalog1.Dockerfile")
    mock_run_command.assert_called_once_with(
        ["opm", "generate", "dockerfile", "catalogs/catalog1"]
    )


@patch("operatorcert.entrypoints.build_fragment_images.run_command")
def test_build_fragment_image(mock_run_command: MagicMock) -> None:
    result = build_fragment_images.build_fragment_image(
        "dockerfile", "context", "image"
    )
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


@patch("operatorcert.entrypoints.build_fragment_images.run_command")
def test_push_fragment_image(mock_run_command: MagicMock) -> None:
    result = build_fragment_images.push_fragment_image("image", "authfile")
    assert result == mock_run_command.return_value

    mock_run_command.assert_called_once_with(
        ["buildah", "push", "--authfile", "authfile", "image", "docker://image"]
    )


@patch("operatorcert.entrypoints.build_fragment_images.push_fragment_image")
@patch("operatorcert.entrypoints.build_fragment_images.build_fragment_image")
@patch("operatorcert.entrypoints.build_fragment_images.create_dockerfile")
def test_create_fragment_image(
    mock_create_dockerfile: MagicMock, mock_build: MagicMock, mock_push: MagicMock
) -> None:
    args = MagicMock()
    args.tag_suffix = "foo"
    args.repository_destination = "bar"
    result = build_fragment_images.create_fragment_image("catalogs", "catalog1", args)

    assert result == "bar:catalog1-foo"
    mock_create_dockerfile.assert_called_once_with("catalogs", "catalog1")
    mock_build.assert_called_once_with(
        mock_create_dockerfile.return_value, "catalogs", "bar:catalog1-foo"
    )
    mock_push.assert_called_once_with("bar:catalog1-foo", args.authfile)


@patch("operatorcert.entrypoints.create_github_gist.json.dump")
@patch("operatorcert.entrypoints.build_fragment_images.create_fragment_image")
@patch("operatorcert.entrypoints.build_fragment_images.setup_logger")
@patch("operatorcert.entrypoints.build_fragment_images.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_create_fragment_image: MagicMock,
    mock_json_dump: MagicMock,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    create_files(tmp_path, {"some_file": "foo"})
    args = MagicMock()
    args.catalog_names = ["catalog1", "catalog2"]
    args.repo_path = str(tmp_path / "repo")
    args.output_file = tmp_path / "output.json"

    mock_setup_argparser.return_value.parse_args.return_value = args

    build_fragment_images.main()

    catalogs_path = args.repo_path + "/catalogs"

    mock_create_fragment_image.assert_has_calls(
        [call(catalogs_path, "catalog1", args), call(catalogs_path, "catalog2", args)]
    )

    expected_output = {
        "catalog1": mock_create_fragment_image.return_value,
        "catalog2": mock_create_fragment_image.return_value,
    }
    mock_json_dump.assert_called_once_with(expected_output, mock.ANY)


def test_setup_argparser() -> None:
    assert build_fragment_images.setup_argparser() is not None
