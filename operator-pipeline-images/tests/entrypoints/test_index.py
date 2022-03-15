from functools import partial
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from operatorcert.entrypoints import index


def test_parse_indices() -> None:
    indices = ["registry/index:v4.9", "registry/index:v4.8"]
    rsp = index.parse_indices(indices)
    rsp == ["v4.9", "v4.8"]

    # if there is no version
    with pytest.raises(Exception):
        index.parse_indices(["registry/index"])


@patch("operatorcert.iib.get_builds")
def test_wait_for_results(mock_get_builds: MagicMock) -> None:
    wait = partial(
        index.wait_for_results,
        "https://iib.engineering.redhat.com",
        "some_batch_id",
        delay=0.1,
        timeout=0.5,
    )

    # if the builds are in complete state
    mock_get_builds.return_value = {
        "items": [{"state": "complete", "batch": "some_batch_id"}]
    }

    assert wait()["items"] == [{"state": "complete", "batch": "some_batch_id"}]

    # if the builds are in failed state without state history
    mock_get_builds.return_value = {
        "items": [{"state": "failed", "id": 1, "batch": "some_batch_id"}]
    }

    assert wait()["items"] == [{"state": "failed", "id": 1, "batch": "some_batch_id"}]

    # if the builds are in failed state with state history
    mock_get_builds.return_value = {
        "items": [
            {
                "state": "failed",
                "id": 1,
                "batch": "some_batch_id",
                "state_history": [{"state_reason": "failed due to timeout"}],
            }
        ]
    }

    assert wait()["items"] == [
        {
            "state": "failed",
            "id": 1,
            "batch": "some_batch_id",
            "state_history": [{"state_reason": "failed due to timeout"}],
        }
    ]

    # if not all the builds are completed
    mock_get_builds.return_value = {
        "items": [
            {"state": "failed", "id": 2, "batch": "some_batch_id"},
            {"state": "complete", "id": 1, "batch": "some_batch_id"},
        ]
    }

    assert wait()["items"] == [
        {"state": "failed", "id": 2, "batch": "some_batch_id"},
        {"state": "complete", "id": 1, "batch": "some_batch_id"},
    ]

    # if there are no build failed, still all of the builds are not completed
    mock_get_builds.return_value = {
        "items": [
            {"state": "pending", "id": 2, "batch": "some_batch_id"},
            {"state": "complete", "id": 1, "batch": "some_batch_id"},
        ]
    }

    assert wait() is None


@patch("operatorcert.iib.add_builds")
@patch("operatorcert.entrypoints.index.extract_manifest_digests")
@patch("operatorcert.entrypoints.index.wait_for_results")
def test_publish_bundle(
    mock_results: MagicMock, mock_manifests: MagicMock, mock_iib_builds: MagicMock
) -> None:
    mock_iib_builds.return_value = [{"state": "complete", "batch": "some_batch_id"}]
    mock_results.return_value = {
        "items": [{"state": "complete", "batch": "some_batch_id"}]
    }
    index.publish_bundle(
        "registry/index",
        "redhat-isv/some-pullspec",
        "https://iib.engineering.redhat.com",
        ["v4.9", "v4.8"],
        "test.txt",
    )
    mock_manifests.assert_called_once_with(
        ["v4.9", "v4.8"], "test.txt", mock_results.return_value
    )

    mock_iib_builds.return_value = [{"state": "failed", "batch": "some_batch_id"}]
    mock_results.return_value = {
        "items": [{"state": "failed", "batch": "some_batch_id"}]
    }
    # if there is no version
    with pytest.raises(Exception):
        index.publish_bundle(
            "registry/index",
            "redhat-isv/some-pullspec",
            "https://iib.engineering.redhat.com",
            ["v4.9", "v4.8"],
            "test.txt",
        )


def test_extract_manifest_digests() -> None:
    index_versions = ["v4.9", "v4.8"]
    output = "test.txt"
    response = {
        "items": [
            {
                "index_image": "registry.test/test:v4.8",
                "index_image_resolved": "registry.test/test@sha256:1234",
            },
            {
                "index_image": "registry.test/test:v4.9",
                "index_image_resolved": "registry.test/test@sha256:5678",
            },
        ]
    }
    mock_open = mock.mock_open()

    with mock.patch("builtins.open", mock_open):
        index.extract_manifest_digests(index_versions, output, response)

    mock_open.assert_called_once_with("test.txt", "w")
    mock_open.return_value.write.assert_called_once_with("sha256:5678,sha256:1234")
