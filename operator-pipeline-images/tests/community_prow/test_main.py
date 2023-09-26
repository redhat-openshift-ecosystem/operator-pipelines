from operatorcert.entrypoints import community_prow
from unittest.mock import patch, MagicMock
from typing import Any


def test_test_prow_logging(monkeypatch: Any) -> None:
    oc_mock = MagicMock()
    oc_mock.get_server_version.return_value = {"version": "1.2.3"}
    monkeypatch.setenv("PULL_REFS", "test_ref")

    with patch("operatorcert.entrypoints.community_prow.oc", oc_mock):
        community_prow.main()
