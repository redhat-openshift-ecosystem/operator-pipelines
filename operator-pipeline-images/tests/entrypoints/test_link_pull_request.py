from unittest.mock import MagicMock, patch
import pytest
from typing import Any

from operatorcert.entrypoints import link_pull_request


@patch("operatorcert.entrypoints.reserve_operator_name.pyxis.patch")
def test_link_pr_to_test_results(mock_patch: MagicMock) -> None:
    with pytest.raises(ValueError):
        link_pull_request.link_pr_to_test_results(
            "https://foo.com", "0123", "https://github.com/repo/pull/qwe", "open"
        )

    link_pull_request.link_pr_to_test_results(
        "https://foo.com", "0123", "https://github.com/repo/pull/1", "open"
    )

    mock_patch.assert_called_once_with(
        "https://foo.com/v1/projects/certification/test-results/id/0123",
        {
            "pull_request": {
                "id": 1,
                "url": "https://github.com/repo/pull/1",
                "status": "open",
            }
        },
    )
