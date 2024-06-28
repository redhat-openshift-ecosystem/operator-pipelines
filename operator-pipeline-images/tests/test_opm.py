from unittest import mock
from unittest.mock import MagicMock, patch

from operatorcert import opm


@patch("operatorcert.opm.os.remove")
@patch("operatorcert.opm.os.path.exists")
@patch("operatorcert.opm.run_command")
def test_create_dockerfile(
    mock_run_command: MagicMock, mock_exists: MagicMock, mock_remove: MagicMock
) -> None:
    mock_exists.return_value = True

    result = opm.create_catalog_dockerfile("catalogs", "catalog1")
    assert result == "catalogs/catalog1.Dockerfile"

    mock_remove.assert_called_once_with("catalogs/catalog1.Dockerfile")
    mock_run_command.assert_called_once_with(
        ["opm", "generate", "dockerfile", "catalogs/catalog1"]
    )


@patch("operatorcert.opm.run_command")
def test_render_template_to_catalog(mock_run_command: MagicMock) -> None:
    mock_open = mock.mock_open()
    with mock.patch("builtins.open", mock_open):
        opm.render_template_to_catalog("template.yaml", "catalog.yaml")
        mock_open.assert_called_once_with("catalog.yaml", "w", encoding="utf-8")

    mock_run_command.assert_called_once_with(
        ["opm", "alpha", "render-template", "basic", "-o", "yaml", "template.yaml"]
    )
