from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from operatorcert.entrypoints import add_bundle_to_fbc


@pytest.fixture
def basic_catalog_template() -> add_bundle_to_fbc.BasicTemplate:
    operator = MagicMock()
    return add_bundle_to_fbc.BasicTemplate(
        operator=operator,
        template_type="fake-type",
        template_name="fake-template.yaml",
        catalog_names=["v4.12-fake"],
    )


@pytest.fixture
def semver_template() -> add_bundle_to_fbc.SemverTemplate:
    operator = MagicMock()
    return add_bundle_to_fbc.SemverTemplate(
        operator=operator,
        template_type="fake-type",
        template_name="fake-template.yaml",
        catalog_names=["v4.12-fake"],
    )


@patch("operatorcert.entrypoints.add_bundle_to_fbc.os.path.exists")
def test_BasicCatalogTemplate(
    mock_exists: MagicMock,
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:
    mock_exists.return_value = False
    assert basic_catalog_template.operator
    assert basic_catalog_template.template_type == "basic"
    assert basic_catalog_template.template_name == "fake-template.yaml"
    assert basic_catalog_template.catalog_names == ["v4.12-fake"]

    assert basic_catalog_template.exists() is False


@patch("operatorcert.entrypoints.add_bundle_to_fbc.YAML")
def test_BasicCatalogTemplate_template(
    mock_yaml: MagicMock,
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:
    mock_open = mock.mock_open()
    mock_yaml.return_value.load.return_value = {"foo": "bar"}
    with patch("builtins.open", mock_open):
        template = basic_catalog_template.template
        assert template == {"foo": "bar"}


@patch("operatorcert.entrypoints.add_bundle_to_fbc.YAML")
def test_BasicCatalogTemplate_save(
    mock_yaml: MagicMock,
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:
    mock_open = mock.mock_open()
    with patch("builtins.open", mock_open):
        basic_catalog_template.save()
        mock_yaml.return_value.dump.assert_called_once()


def test_BasicCatalogTemplate_create(
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:
    release_config = {
        "channels": ["alpha"],
        "replaces": "fake-replaces",
        "skipRange": "fake-range",
        "skips": "fake-skips",
    }
    bundle = MagicMock()
    basic_catalog_template.operator.operator_name = "fake-operator"
    bundle.csv = {"metadata": {"name": "fake-bundle"}}
    basic_catalog_template.create(release_config, "quay.io/fake-bundle:1", bundle)

    expected_template = {
        "entries": [
            {
                "defaultChannel": "alpha",
                "name": "fake-operator",
                "schema": "olm.package",
            },
            {
                "entries": [
                    {
                        "name": "fake-bundle",
                        "replaces": "fake-replaces",
                        "skipRange": "fake-range",
                        "skips": "fake-skips",
                    },
                ],
                "name": "alpha",
                "package": "fake-operator",
                "schema": "olm.channel",
            },
            {
                "image": "quay.io/fake-bundle:1",
                "schema": "olm.bundle",
            },
        ],
        "schema": "olm.template.basic",
    }
    assert basic_catalog_template.template == expected_template


def test_BasicCatalogTemplate_amend(
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:
    release_config = {
        "channels": ["alpha", "beta"],
        "replaces": "fake-replaces",
        "skipRange": "fake-range",
        "skips": "fake-skips",
    }
    basic_catalog_template._template = {
        "entries": [
            {
                "defaultChannel": "alpha",
                "name": "fake-operator",
                "schema": "olm.package",
            },
            {
                "entries": [
                    {
                        "name": "fake-bundle",
                    },
                ],
                "name": "alpha",
                "package": "fake-operator",
                "schema": "olm.channel",
            },
            {
                "image": "quay.io/fake-bundle:1",
                "schema": "olm.bundle",
            },
        ],
        "schema": "olm.template.basic",
    }
    bundle = MagicMock()
    basic_catalog_template.operator.operator_name = "fake-operator"
    bundle.csv = {"metadata": {"name": "fake-bundle-2"}}
    basic_catalog_template.amend(release_config, "quay.io/fake-bundle:2", bundle)

    expected_template = {
        "entries": [
            {
                "defaultChannel": "alpha",
                "name": "fake-operator",
                "schema": "olm.package",
            },
            {
                "entries": [
                    {
                        "name": "fake-bundle",
                    },
                    {
                        "name": "fake-bundle-2",
                        "replaces": "fake-replaces",
                        "skipRange": "fake-range",
                        "skips": "fake-skips",
                    },
                ],
                "name": "alpha",
                "package": "fake-operator",
                "schema": "olm.channel",
            },
            {
                "image": "quay.io/fake-bundle:1",
                "schema": "olm.bundle",
            },
            {
                "entries": [
                    {
                        "name": "fake-bundle-2",
                        # Values below don't make sense
                        # in the context of the catalog graph but it covers the
                        # usecase of adding a bundle to new channel
                        "replaces": "fake-replaces",
                        "skipRange": "fake-range",
                        "skips": "fake-skips",
                    },
                ],
                "name": "beta",
                "package": "fake-operator",
                "schema": "olm.channel",
            },
            {
                "image": "quay.io/fake-bundle:2",
                "schema": "olm.bundle",
            },
        ],
        "schema": "olm.template.basic",
    }
    assert basic_catalog_template.template == expected_template

    # Do it again to test that the bundle is not added twice
    basic_catalog_template.amend(release_config, "quay.io/fake-bundle:2", bundle)
    assert basic_catalog_template.template == expected_template


@patch("operatorcert.entrypoints.add_bundle_to_fbc.os.makedirs")
@patch(
    "operatorcert.entrypoints.add_bundle_to_fbc.BasicTemplate._render_template_extra_args"
)
@patch("operatorcert.entrypoints.add_bundle_to_fbc.BasicTemplate.run_cmd_with_cache")
def test_BasicCatalogTemplate_render(
    mock_run_command: MagicMock,
    mock_extra_args: MagicMock,
    mock_mkdir: MagicMock,
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:
    mock_open = mock.mock_open()
    basic_catalog_template.operator.operator_name = "fake-operator"
    basic_catalog_template.operator.repo.root = Path("./")  # type: ignore
    basic_catalog_template.template_path = Path(
        "operators/fake-operator/catalog-templates/fake-template.yaml"
    )

    with patch("builtins.open", mock_open):
        basic_catalog_template.render()

    mock_mkdir.assert_called_once_with(
        Path("./") / "catalogs/v4.12-fake/fake-operator", exist_ok=True
    )
    mock_open.assert_called_once_with(
        Path("./") / "catalogs/v4.12-fake/fake-operator/catalog.yaml",
        "w",
        encoding="utf8",
    )
    mock_run_command.assert_called_once_with(
        [
            "opm",
            "alpha",
            "render-template",
            "basic",
            "-o",
            "yaml",
            "operators/fake-operator/catalog-templates/fake-template.yaml",
        ]
        + mock_extra_args.return_value,
    )
    mock_extra_args.assert_called_once_with("v4.12-fake")


@patch("operatorcert.entrypoints.add_bundle_to_fbc.BasicTemplate.amend")
@patch("operatorcert.entrypoints.add_bundle_to_fbc.BasicTemplate.create")
@patch("operatorcert.entrypoints.add_bundle_to_fbc.BasicTemplate.exists")
def test_BasicCatalogTemplate_add_new_bundle(
    mock_exists: MagicMock,
    mock_create: MagicMock,
    mock_amend: MagicMock,
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:

    mock_exists.return_value = False
    bundle = MagicMock()
    basic_catalog_template.add_new_bundle({}, "fake-image", bundle)
    mock_create.assert_called_once_with({}, "fake-image", bundle)
    mock_amend.assert_not_called()

    mock_exists.return_value = True
    mock_create.reset_mock()

    basic_catalog_template.add_new_bundle({}, "fake-image", bundle)
    mock_create.assert_not_called()
    mock_amend.assert_called_once_with({}, "fake-image", bundle)


@patch("operatorcert.entrypoints.add_bundle_to_fbc.utils.run_command")
def test_BasicCatalogTemplate__run_cmd_with_cache(
    mock_cmd: MagicMock, basic_catalog_template: add_bundle_to_fbc.BasicTemplate
) -> None:
    result = basic_catalog_template.run_cmd_with_cache(["foo", "bar"])
    assert result == mock_cmd.return_value
    assert basic_catalog_template._cmd_cache == {"foo bar": result}
    mock_cmd.assert_called_once_with(["foo", "bar"])
    mock_cmd.reset_mock()

    result = basic_catalog_template.run_cmd_with_cache(["foo", "bar"])
    assert result == mock_cmd.return_value
    mock_cmd.assert_not_called()

    result = basic_catalog_template.run_cmd_with_cache(["foo", "baz"])
    assert result == mock_cmd.return_value
    assert basic_catalog_template._cmd_cache == {"foo bar": result, "foo baz": result}
    mock_cmd.assert_called_once_with(["foo", "baz"])


@patch(
    "operatorcert.entrypoints.add_bundle_to_fbc.BasicTemplate._bundle_object_to_csv_metada"
)
def test_BasicCatalogTemplate__render_template_extra_args(
    mock_bundle_to_csv: MagicMock,
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:
    mock_bundle_to_csv.return_value = ["--foo", "bar"]
    result = basic_catalog_template._render_template_extra_args("v4.12-fake")

    assert result == ["--foo", "bar"]


@patch("operatorcert.entrypoints.add_bundle_to_fbc.utils.is_catalog_v4_17_plus")
def test_BasicCatalogTemplate__bundle_object_to_csv_metada(
    mock_is_catalog_v4_17_plus: MagicMock,
    basic_catalog_template: add_bundle_to_fbc.BasicTemplate,
) -> None:
    mock_is_catalog_v4_17_plus.side_effect = [False, True, False]

    result = basic_catalog_template._bundle_object_to_csv_metada("v4.12")
    assert result == []

    result = basic_catalog_template._bundle_object_to_csv_metada("v4.17")
    assert result == ["--migrate-level", "bundle-object-to-csv-metadata"]


def test_SemverTemplate(
    semver_template: add_bundle_to_fbc.SemverTemplate,
) -> None:
    assert semver_template.template_type == "semver"


def test_SemverTemplate_create(
    semver_template: add_bundle_to_fbc.SemverTemplate,
) -> None:
    release_config = {
        "channels": ["Fast", "Candidate"],
    }
    bundle = MagicMock()
    semver_template.create(release_config, "quay.io/fake-bundle:1", bundle)

    expected_template = {
        "GenerateMajorChannels": True,
        "GenerateMinorChannels": True,
        "Schema": "olm.semver",
        "Fast": {"Bundles": [{"Image": "quay.io/fake-bundle:1"}]},
        "Candidate": {"Bundles": [{"Image": "quay.io/fake-bundle:1"}]},
    }
    assert semver_template.template == expected_template


def test_SemverTemplate_amend(
    semver_template: add_bundle_to_fbc.SemverTemplate,
) -> None:
    release_config = {
        "channels": ["Fast", "Candidate"],
    }
    semver_template._template = {
        "GenerateMajorChannels": True,
        "GenerateMinorChannels": True,
        "Schema": "olm.semver",
        "Candidate": {"Bundles": [{"Image": "quay.io/fake-bundle:1"}]},
    }
    bundle = MagicMock()
    semver_template.amend(release_config, "quay.io/fake-bundle:2", bundle)

    expected_template = {
        "GenerateMajorChannels": True,
        "GenerateMinorChannels": True,
        "Schema": "olm.semver",
        "Fast": {"Bundles": [{"Image": "quay.io/fake-bundle:2"}]},
        "Candidate": {
            "Bundles": [
                {"Image": "quay.io/fake-bundle:1"},
                {"Image": "quay.io/fake-bundle:2"},
            ],
        },
    }
    assert semver_template.template == expected_template

    # Do it again to test that the bundle is not added twice
    semver_template.amend(release_config, "quay.io/fake-bundle:2", bundle)
    assert semver_template.template == expected_template


def test_get_catalog_mapping() -> None:
    ci_file = {
        "fbc": {
            "catalog_mapping": [
                {
                    "template_name": "fake-template.yaml",
                    "catalog_names": ["v4.12-fake"],
                },
            ]
        }
    }
    result = add_bundle_to_fbc.get_catalog_mapping(ci_file, "unknown")
    assert result is None

    result = add_bundle_to_fbc.get_catalog_mapping(ci_file, "fake-template.yaml")
    assert result == {
        "template_name": "fake-template.yaml",
        "catalog_names": ["v4.12-fake"],
    }


@patch("operatorcert.entrypoints.add_bundle_to_fbc.SemverTemplate")
@patch("operatorcert.entrypoints.add_bundle_to_fbc.BasicTemplate")
@patch("operatorcert.entrypoints.add_bundle_to_fbc.get_catalog_mapping")
def test_release_bundle_to_fbc(
    mock_catalog_mapping: MagicMock, mock_basic: MagicMock, mock_semver: MagicMock
) -> None:
    bundle = MagicMock()
    args = MagicMock()

    bundle.release_config = None
    with pytest.raises(ValueError):
        # release config is missing
        add_bundle_to_fbc.release_bundle_to_fbc(args, bundle)

    bundle.release_config = {
        "catalog_templates": [{"template_name": "fake-template.yaml"}]
    }
    mock_catalog_mapping.return_value = None
    with pytest.raises(ValueError):
        # A catalog mapping is missing
        add_bundle_to_fbc.release_bundle_to_fbc(args, bundle)

    mock_catalog_mapping.return_value = {
        "template_name": "fake-template.yaml",
        "catalog_names": ["v4.12-fake"],
        "type": "unknown",
    }
    with pytest.raises(ValueError):
        # Unknown template type
        add_bundle_to_fbc.release_bundle_to_fbc(args, bundle)

    bundle.release_config = {
        "catalog_templates": [
            {"template_name": "fake-basic.yaml"},
            {"template_name": "fake-semver.yaml"},
        ]
    }
    mock_catalog_mapping.side_effect = [
        {
            "template_name": "fake-basic.yaml",
            "catalog_names": ["v4.12-fake"],
            "type": "olm.template.basic",
        },
        {
            "template_name": "fake-semver.yaml",
            "catalog_names": ["v4.13-fake"],
            "type": "olm.semver",
        },
    ]
    add_bundle_to_fbc.release_bundle_to_fbc(args, bundle)

    mock_basic.assert_called_once()
    mock_semver.assert_called_once()

    mock_basic.return_value.add_new_bundle.assert_called_once()
    mock_semver.return_value.add_new_bundle.assert_called_once()

    mock_basic.return_value.save.assert_called_once()
    mock_semver.return_value.save.assert_called_once()

    mock_basic.return_value.render.assert_called_once()
    mock_semver.return_value.render.assert_called_once()


def test_setup_argparser() -> None:
    parser = add_bundle_to_fbc.setup_argparser()

    assert parser


@patch("operatorcert.entrypoints.add_bundle_to_fbc.release_bundle_to_fbc")
@patch("operatorcert.entrypoints.add_bundle_to_fbc.Repo")
@patch("operatorcert.entrypoints.add_bundle_to_fbc.setup_argparser")
def test_main(
    mock_arg_parser: MagicMock, mock_repo: MagicMock, mock_release_bundle: MagicMock
) -> None:
    add_bundle_to_fbc.main()

    mock_arg_parser.assert_called_once()
    mock_repo.assert_called_once()
    mock_release_bundle.assert_called_once()
