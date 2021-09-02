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
        },
    }
    mock_get.return_value = mock_rsp
    # Act
    get_cert_project_related_data("https://example.com", "id1234")
    # assert
    mock_store.assert_called_with(
        {"cert_project": {"org_id": 123, "container": {"isv_pid": "some_pid"}}}
    )
