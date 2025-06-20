from pathlib import Path
from typing import Any
from unittest import mock
from unittest.mock import MagicMock, patch

import operatorcert.entrypoints.build_scratch_catalog as build_scratch_catalog


def test_setup_argparser() -> None:
    assert build_scratch_catalog.setup_argparser() is not None


@patch("operatorcert.entrypoints.build_scratch_catalog.yaml.safe_dump")
def test_generate_and_save_basic_template(mock_yaml_dump: MagicMock) -> None:
    with patch(
        "operatorcert.entrypoints.build_scratch_catalog.open", mock.mock_open()
    ) as mock_open:
        build_scratch_catalog.generate_and_save_basic_template(
            "template.yaml",
            "package",
            "default_channel",
            ["channel_name", "another_channel"],
            "csv_name",
            "bundle_pullspec",
        )

    package_obj = {
        "schema": "olm.package",
        "name": "package",
        "defaultChannel": "default_channel",
    }
    channels = [
        {
            "schema": "olm.channel",
            "package": "package",
            "name": channel_name,
            "entries": [{"name": "csv_name"}],
        }
        for channel_name in ["channel_name", "another_channel"]
    ]

    bundles = {"schema": "olm.bundle", "image": "bundle_pullspec"}
    template = {
        "schema": "olm.template.basic",
        "entries": [package_obj, bundles] + channels,
    }

    mock_open.assert_called_once_with("template.yaml", "w", encoding="utf-8")
    mock_yaml_dump.assert_called_once_with(
        template,
        mock_open.return_value,
        explicit_start=True,
        indent=2,
    )


@patch("operatorcert.entrypoints.build_scratch_catalog.buildah.push_image")
@patch("operatorcert.entrypoints.build_scratch_catalog.buildah.build_image")
@patch("operatorcert.entrypoints.build_scratch_catalog.opm.create_catalog_dockerfile")
@patch("operatorcert.entrypoints.build_scratch_catalog.opm.render_template_to_catalog")
@patch(
    "operatorcert.entrypoints.build_scratch_catalog.generate_and_save_basic_template"
)
@patch("operatorcert.entrypoints.build_scratch_catalog.tempfile.TemporaryDirectory")
def test_build_and_push_catalog_image(
    mock_tmp: MagicMock,
    mock_template: MagicMock,
    mock_render: MagicMock,
    mock_dockerfile: MagicMock,
    mock_build: MagicMock,
    mock_push: MagicMock,
) -> None:

    mock_tmp.return_value.__enter__.return_value = "/tmp"
    bundle = MagicMock()
    bundle.channels = set(["channel", "another_channel"])
    build_scratch_catalog.build_and_push_catalog_image(
        bundle, "bundle_pullspec", "repository_destination", "authfile"
    )
    mock_template.assert_called_once_with(
        template_path="/tmp/template.yaml",
        package=bundle.metadata_operator_name,
        default_channel=bundle.default_channel,
        channel_names=list(bundle.channels),
        csv_name=bundle.csv["metadata"]["name"],
        bundle_pullspec="bundle_pullspec",
    )
    mock_render.assert_called_once_with(
        "/tmp/template.yaml", f"/tmp/{bundle.metadata_operator_name}/catalog.yaml"
    )
    mock_dockerfile.assert_called_once_with("/tmp", bundle.metadata_operator_name)
    mock_build.assert_called_once_with(
        mock_dockerfile.return_value, "/tmp", "repository_destination"
    )
    mock_push.assert_called_once_with("repository_destination", "authfile")


@patch("operatorcert.entrypoints.build_scratch_catalog.build_and_push_catalog_image")
@patch("operatorcert.entrypoints.build_scratch_catalog.Repo")
@patch("operatorcert.entrypoints.build_scratch_catalog.setup_logger")
@patch("operatorcert.entrypoints.build_scratch_catalog.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_repo: MagicMock,
    mock_build_and_push_catalog_image: MagicMock,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    args = MagicMock()

    mock_setup_argparser.return_value.parse_args.return_value = args

    build_scratch_catalog.main()

    mock_repo.assert_called_once_with(args.repo_path)

    mock_build_and_push_catalog_image.assert_called_once_with(
        mock_repo.return_value.operator.return_value.bundle.return_value,
        args.bundle_pullspec,
        args.repository_destination,
        args.authfile,
    )
