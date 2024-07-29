import json
from unittest.mock import patch, MagicMock
import pytest
from typing import Any
import datetime

from operatorcert.entrypoints.update_preflight_versions import (
    synchronize_versions,
    get_versions,
)

PYXIS_URL = "https://pyxis.com"


@patch("operatorcert.entrypoints.update_preflight_versions.pyxis.patch")
@patch("operatorcert.entrypoints.update_preflight_versions.pyxis.get")
@pytest.mark.parametrize(
    "content",
    [
        {
            "data": [
                {
                    "_id": "N-1",
                    "creation_date": "2024-06-27T17:53:39.153000+00:00",
                    "enabled_for_testing": True,
                    "version": "1.9.9",
                },
                {
                    "_id": "N",
                    "creation_date": "2024-07-15T15:26:51.408000+00:00",
                    "enabled_for_testing": True,
                    "version": "1.10.0",
                },
            ],
            "total": 2,
        },
        {
            "data": [
                {
                    "_id": "N-2",
                    "creation_date": "2024-06-27T17:53:39.153000+00:00",
                    "enabled_for_testing": True,
                    "version": "1.9.8",
                },
                {
                    "_id": "N-1",
                    "creation_date": "2024-06-27T17:53:39.153000+00:00",
                    "enabled_for_testing": True,
                    "version": "1.9.9",
                },
                {
                    "_id": "N",
                    "creation_date": "2024-07-15T15:26:51.408000+00:00",
                    "enabled_for_testing": True,
                    "version": "1.10.0",
                },
            ],
            "total": 3,
        },
    ],
    ids=["only-two", "valid-time"],
)
def test_no_change(
    mock_get: MagicMock,
    mock_patch: MagicMock,
    content: dict[str, Any],
) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = json.dumps(content)

    mock_get.return_value = mock_resp

    with patch(
        "operatorcert.entrypoints.update_preflight_versions.datetime"
    ) as mock_date:
        # have to patch fromisoformat as well or the test will break
        mock_date.fromisoformat = datetime.datetime.fromisoformat

        mock_date.now.return_value = datetime.datetime.fromisoformat(
            "2024-07-17T14:44:54.546896+00:00"
        )

        synchronize_versions(pyxis_url=PYXIS_URL, dry_run=False, log_current=False)

    mock_patch.assert_not_called()


@patch("operatorcert.entrypoints.update_preflight_versions.pyxis.patch")
@patch("operatorcert.entrypoints.update_preflight_versions.pyxis.get")
@pytest.mark.parametrize(
    ["content", "expected_patch_urls"],
    [
        (
            {
                "data": [
                    {
                        "_id": "N-2",
                        "creation_date": "2023-06-27T17:53:39.153000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.9.8",
                    },
                    {
                        "_id": "N-1",
                        "creation_date": "2024-06-27T17:53:39.153000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.9.9",
                    },
                    {
                        "_id": "N",
                        "creation_date": "2024-07-15T15:26:51.408000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.10.0",
                    },
                ],
                "total": 3,
            },
            [f"{PYXIS_URL}/v1/tools/id/N-2"],
        ),
        (
            {
                "data": [
                    {
                        "_id": "N-3",
                        "creation_date": "2023-06-27T17:53:39.153000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.9.7",
                    },
                    {
                        "_id": "N-2",
                        "creation_date": "2023-06-27T17:53:39.153000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.9.8",
                    },
                    {
                        "_id": "N-1",
                        "creation_date": "2024-06-27T17:53:39.153000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.9.9",
                    },
                    {
                        "_id": "N",
                        "creation_date": "2024-07-15T15:26:51.408000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.10.0",
                    },
                ],
                "total": 4,
            },
            [f"{PYXIS_URL}/v1/tools/id/N-2", f"{PYXIS_URL}/v1/tools/id/N-3"],
        ),
    ],
    ids=["one-old-release", "two-old-releases"],
)
def test_disable_old(
    mock_get: MagicMock,
    mock_patch: MagicMock,
    content: dict[str, Any],
    expected_patch_urls: list[str],
) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = json.dumps(content)

    mock_get.return_value = mock_resp

    with patch(
        "operatorcert.entrypoints.update_preflight_versions.datetime"
    ) as mock_date:
        # have to patch fromisoformat as well or the test will break
        mock_date.fromisoformat = datetime.datetime.fromisoformat

        mock_date.now.return_value = datetime.datetime.fromisoformat(
            "2024-07-17T14:44:54.546896+00:00"
        )

        synchronize_versions(pyxis_url=PYXIS_URL, dry_run=False, log_current=False)

    for expected_url in expected_patch_urls:
        mock_patch.assert_any_call(expected_url, {"enabled_for_testing": False})

    assert mock_patch.call_count == len(expected_patch_urls)


@patch("operatorcert.entrypoints.update_preflight_versions.get_version_data_page")
def test_get_version_paging(mock_data_page: MagicMock):
    mock_data_page.side_effect = map(
        json.dumps,
        [
            {
                "data": [
                    {
                        "_id": "N-1",
                        "creation_date": "2024-06-27T17:53:39.153000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.9.9",
                    },
                    {
                        "_id": "N",
                        "creation_date": "2024-07-15T15:26:51.408000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.10.0",
                    },
                ],
                "total": 3,
            },
            {
                "data": [
                    {
                        "_id": "N-2",
                        "creation_date": "2024-06-27T17:53:39.153000+00:00",
                        "enabled_for_testing": True,
                        "version": "1.9.9",
                    },
                ],
                "total": 3,
            },
        ],
    )

    versions = get_versions(PYXIS_URL, 2)
    assert len(versions) == 3


@patch("operatorcert.entrypoints.update_preflight_versions.pyxis.get")
def test_pyxis_error(mock_pyxis_get: MagicMock):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_pyxis_get.return_value = mock_resp

    with pytest.raises(RuntimeError):
        synchronize_versions(PYXIS_URL, dry_run=False, log_current=False)
