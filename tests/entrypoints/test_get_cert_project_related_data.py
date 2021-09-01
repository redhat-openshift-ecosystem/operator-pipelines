from unittest.mock import patch, MagicMock

import pytest

from operatorcert.entrypoints.get_cert_project_related_data import (
    get_cert_project_related_data,
)


@patch("operatorcert.entrypoints.get_cert_project_related_data.pyxis.get")
@patch("operatorcert.entrypoints.get_cert_project_related_data.store_results")
def test_get_cert_project_related_data(
    mock_store: MagicMock, mock_get: MagicMock
) -> None:
    # Arrange
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {
        "org_id": 123,
        "container": {
            "isv_pid": "some_pid",
            "repository_name": "some_name",
            "distribution_method": "some_method",
        },
    }
    mock_get.return_value = mock_rsp
    # Act
    get_cert_project_related_data("https://example.com", "id1234")
    # assert
    mock_store.assert_called_with(
        {
            "isv_pid": "some_pid",
            "repo_name": "some_name",
            "dist_method": "some_method",
            "org_id": 123,
        }
    )


@patch("operatorcert.entrypoints.get_cert_project_related_data.pyxis.get")
def test_get_cert_project_related_data_missing_fields(mock_get: MagicMock) -> None:
    # Arrange
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {
        "org_id": 123,
        "container": {
            "fields": "are missing",
        },
    }
    mock_get.return_value = mock_rsp
    # Act & Assert
    with pytest.raises(KeyError):
        get_cert_project_related_data("https://example.com", "id1234")
