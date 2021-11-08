from unittest.mock import patch, MagicMock

import pytest

from operatorcert.entrypoints.get_vendor_related_data import get_vendor_related_data


@patch("operatorcert.entrypoints.get_vendor_related_data.pyxis.get")
@patch("operatorcert.entrypoints.get_vendor_related_data.store_results")
def test_get_vendor_related_data(mock_store: MagicMock, mock_get: MagicMock) -> None:
    # Arrange
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {
        "label": "some_label",
    }
    mock_get.return_value = mock_rsp
    # Act
    get_vendor_related_data("https://example.com", "id1234")
    # assert
    mock_store.assert_called_with({"vendor": {"label": "some_label"}})
