from pathlib import Path
from typing import Any
from unittest import mock
from unittest.mock import MagicMock, call, patch

import operatorcert.entrypoints.build_fragment_images as build_fragment_images
from tests.utils import create_files


def test_select_operator_for_catalog(
    tmp_path: Path,
) -> None:
    create_files(
        tmp_path,
        {
            "v4.15/op1/catalog.yaml": {},
            "v4.15/op2/catalog.yaml": {},
            "v4.15/op3/catalog.yaml": {},
            "v4.16/op3/catalog.yaml": {},
            "v4.15_dest": None,
            "v4.16_dest": None,
        },
    )
    result = build_fragment_images.select_operator_for_catalog(
        tmp_path, "v4.15", ["op1", "op3"], tmp_path / "v4.15_dest"
    )
    assert result == tmp_path / "v4.15_dest/v4.15"
    assert (tmp_path / "v4.15_dest/v4.15").exists()
    assert (tmp_path / "v4.15_dest/v4.15/op1/catalog.yaml").exists()
    assert (tmp_path / "v4.15_dest/v4.15/op3/catalog.yaml").exists()


@patch("operatorcert.entrypoints.build_fragment_images.buildah.push_image")
@patch("operatorcert.entrypoints.build_fragment_images.buildah.build_image")
@patch("operatorcert.entrypoints.build_fragment_images.opm.create_catalog_dockerfile")
@patch("operatorcert.entrypoints.build_fragment_images.select_operator_for_catalog")
@patch("operatorcert.entrypoints.build_scratch_catalog.tempfile.TemporaryDirectory")
def test_create_fragment_image(
    mock_tempdir: MagicMock,
    mock_select_operator: MagicMock,
    mock_create_catalog_dockerfile: MagicMock,
    mock_build: MagicMock,
    mock_push: MagicMock,
) -> None:
    args = MagicMock()
    args.tag_suffix = "foo"
    args.repository_destination = "bar"
    mock_tempdir.return_value.__enter__.return_value = "/tmp"
    result = build_fragment_images.create_fragment_image(
        Path("catalogs"), "catalog1", ["op1", "op2"], args
    )

    assert result == "bar:catalog1-foo"
    mock_create_catalog_dockerfile.assert_called_once_with(Path("/tmp"), "catalog1")
    mock_build.assert_called_once_with(
        mock_create_catalog_dockerfile.return_value.as_posix(),
        "/tmp",
        "bar:catalog1-foo",
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
    args.catalog_operators = ["catalog1/foo", "catalog1/bar", "catalog2/foo"]
    args.repo_path = tmp_path / "repo"
    args.output_file = tmp_path / "output.json"

    mock_setup_argparser.return_value.parse_args.return_value = args

    build_fragment_images.main()

    catalogs_path = args.repo_path / "catalogs"

    mock_create_fragment_image.assert_has_calls(
        [
            call(catalogs_path, "catalog1", ["foo", "bar"], args),
            call(catalogs_path, "catalog2", ["foo"], args),
        ]
    )

    expected_output = {
        "catalog1": mock_create_fragment_image.return_value,
        "catalog2": mock_create_fragment_image.return_value,
    }
    mock_json_dump.assert_called_once_with(expected_output, mock.ANY)


def test_setup_argparser() -> None:
    assert build_fragment_images.setup_argparser() is not None
