import os
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from operatorcert.entrypoints import fbc_onboarding


def test_setup_argparser() -> None:
    parser = fbc_onboarding.setup_argparser()
    assert parser is not None


@patch("operatorcert.entrypoints.fbc_onboarding.requests.get")
def test_get_supported_catalogs(mock_requests: MagicMock) -> None:
    mock_requests.return_value.json.return_value = {
        "data": [
            {
                "id": "1",
                "path": "registry.redhat.io/redhat/certified-operator-index:v1",
            },
            {
                "id": "2",
                "path": "registry.redhat.io/redhat/certified-operator-index:v2",
            },
        ]
    }
    catalogs = fbc_onboarding.get_supported_catalogs("org", False)
    assert catalogs == [
        {"id": "1", "path": "registry.redhat.io/redhat/certified-operator-index:v1"},
        {"id": "2", "path": "registry.redhat.io/redhat/certified-operator-index:v2"},
    ]


@patch("operatorcert.entrypoints.fbc_onboarding.requests.get")
def test_get_supported_catalogs_stage(mock_requests: MagicMock) -> None:
    mock_requests.return_value.json.return_value = {
        "data": [
            {
                "id": "1",
                "path": "registry.redhat.io/redhat/certified-operator-index:v1",
            },
            {
                "id": "2",
                "path": "registry.redhat.io/redhat/certified-operator-index:v2",
            },
        ]
    }
    catalogs = fbc_onboarding.get_supported_catalogs("org", True)
    assert catalogs == [
        {
            "id": "1",
            "path": "registry.stage.redhat.io/redhat/certified-operator-index:v1",
        },
        {
            "id": "2",
            "path": "registry.stage.redhat.io/redhat/certified-operator-index:v2",
        },
    ]


@patch("operatorcert.entrypoints.fbc_onboarding.run_command")
def test_opm_cache(mock_command: MagicMock) -> None:
    resp = fbc_onboarding.opm_cache("image")
    mock_command.assert_called_once_with(["opm", "render", "-o", "yaml", "image"])
    assert resp == mock_command.return_value.stdout


@patch("operatorcert.entrypoints.fbc_onboarding.opm_cache")
@patch("operatorcert.entrypoints.fbc_onboarding.os.makedirs")
@patch("operatorcert.entrypoints.fbc_onboarding.os.path.exists")
def test_build_cache(
    mock_exists: MagicMock,
    mock_makedir: MagicMock,
    mock_cache: MagicMock,
) -> None:
    mock_open = mock.mock_open()
    mock_exists.side_effect = [False, True, False, False]
    fbc_onboarding.build_cache("v1", "img", "/tmp")
    mock_cache.assert_not_called()

    mock_exists.reset_mock()
    mock_makedir.reset_mock()
    with mock.patch("builtins.open", mock_open):
        fbc_onboarding.build_cache("v1", "img", "/tmp")

    assert mock_exists.call_count == 2
    mock_makedir.assert_called_once_with("/tmp")
    mock_cache.assert_called_once_with("img")
    mock_open.assert_called_once_with("/tmp/v1.yaml", "wb")


def test_get_base_template_from_catalog() -> None:
    catalog = [
        {"name": "pkg1", "schema": "olm.bundle", "image": "img1", "xyz": "abc"},
        {"name": "pkg2", "schema": "olm.bundle", "image": "img2", "xyz": "abc"},
        {"package": "pkg1", "schema": "olm.channel"},
        {"package": "pkg2", "schema": "olm.channel"},
    ]

    result = fbc_onboarding.get_base_template_from_catalog("pkg1", catalog)

    assert result == [
        {"package": "pkg1", "schema": "olm.channel"},
        {"schema": "olm.bundle", "image": "img1"},
    ]


@patch("builtins.input")
@patch("operatorcert.entrypoints.fbc_onboarding.os.makedirs")
@patch("operatorcert.entrypoints.fbc_onboarding.os.path.exists")
def test_create_catalog_template_dir_if_not_exists(
    mock_exists: MagicMock,
    mock_makedir: MagicMock,
    mock_input: MagicMock,
) -> None:
    mock_exists.return_value = False
    operator = MagicMock()
    operator.root = "/tmp"
    fbc_onboarding.create_catalog_template_dir_if_not_exists(operator)
    mock_makedir.assert_called_once_with("/tmp/catalog-templates")

    mock_makedir.reset_mock()
    mock_exists.return_value = True
    mock_input.return_value = "n"
    with pytest.raises(SystemExit):
        fbc_onboarding.create_catalog_template_dir_if_not_exists(operator)


@patch("operatorcert.entrypoints.fbc_onboarding.get_base_template_from_catalog")
@patch("operatorcert.entrypoints.fbc_onboarding.yaml.safe_dump_all")
@patch("operatorcert.entrypoints.fbc_onboarding.yaml.safe_load_all")
def test_generate_and_save_base_templates(
    mock_yaml_load: MagicMock, mock_yaml_dump: MagicMock, mock_template: MagicMock
) -> None:
    mock_yaml_load.return_value = []
    mock_template.return_value = []

    with mock.patch("builtins.open", mock.mock_open()) as mock_open:
        fbc_onboarding.generate_and_save_base_templates("v1", "img", "/tmp", "/tmp")

        mock_yaml_dump.assert_called_once()


@patch("operatorcert.entrypoints.fbc_onboarding.yaml.safe_dump")
def test_update_operator_config(mock_yaml_dump: MagicMock) -> None:
    operator = MagicMock()
    operator.config = {"updateGraph": "semver-mode"}
    with mock.patch("builtins.open", mock.mock_open()) as mock_open:
        fbc_onboarding.update_operator_config(operator)

    expected_config = {"fbc": {"enabled": True}}
    mock_yaml_dump.assert_called_once_with(
        expected_config, mock.ANY, explicit_start=True
    )


@patch("operatorcert.entrypoints.fbc_onboarding.yaml.safe_dump_all")
@patch("operatorcert.entrypoints.fbc_onboarding.yaml.safe_load_all")
@patch("operatorcert.entrypoints.fbc_onboarding.os.makedirs")
@patch("operatorcert.entrypoints.fbc_onboarding.os.path.exists")
@patch("operatorcert.entrypoints.fbc_onboarding.run_command")
def test_render_fbc_from_template(
    mock_run_command: MagicMock,
    mock_path_exists: MagicMock,
    mock_makedir: MagicMock,
    mock_safe_load_all: MagicMock,
    mock_safe_dump_all: MagicMock,
) -> None:
    operator = MagicMock()
    mock_path_exists.return_value = False
    mock_safe_load_all.return_value = []

    with mock.patch("builtins.open", mock.mock_open()) as mock_open:
        fbc_onboarding.render_fbc_from_template(operator, "4.15")

        mock_run_command.assert_called_once_with(
            [
                "opm",
                "alpha",
                "render-template",
                "basic",
                "-o",
                "yaml",
                os.path.join(
                    operator.root, fbc_onboarding.CATALOG_TEMPLATES_DIR, "v4.15.yaml"
                ),
            ],
            cwd=operator.root,
        )
        mock_makedir.assert_called_once()
        mock_safe_dump_all.assert_called_once()


@patch("operatorcert.entrypoints.fbc_onboarding.update_operator_config")
@patch("operatorcert.entrypoints.fbc_onboarding.render_fbc_from_template")
@patch("operatorcert.entrypoints.fbc_onboarding.generate_and_save_base_templates")
@patch("operatorcert.entrypoints.fbc_onboarding.build_cache")
@patch(
    "operatorcert.entrypoints.fbc_onboarding.create_catalog_template_dir_if_not_exists"
)
@patch("operatorcert.entrypoints.fbc_onboarding.get_supported_catalogs")
def test_onboard_operator_to_fbc(
    mock_catalogs: MagicMock,
    mock_template_dir: MagicMock,
    mock_cache: MagicMock,
    mock_base_template: MagicMock,
    mock_render: MagicMock,
    mock_config: MagicMock,
) -> None:
    repo = MagicMock()
    repo.config = {"organization": "org"}
    operator = MagicMock()
    repo.operator.return_value = operator
    mock_catalogs.return_value = [
        {"ocp_version": "1", "path": "registry.com/foo"},
        {"ocp_version": "2", "path": "registry.com/foo"},
    ]
    fbc_onboarding.onboard_operator_to_fbc("op1", repo, "/tmp", False)
    mock_catalogs.assert_called_once_with("org", False)
    mock_template_dir.assert_called_once_with(operator)

    assert mock_cache.call_count == 2
    assert mock_base_template.call_count == 2

    mock_render.assert_has_calls([mock.call(operator, "1"), mock.call(operator, "2")])

    mock_config.assert_called_once_with(operator)
