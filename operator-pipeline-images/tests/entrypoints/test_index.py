from functools import partial
from unittest import mock
from unittest.mock import MagicMock, patch, call

import pytest

from operatorcert.entrypoints import index


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

    # if the builds are in failed state
    mock_get_builds.return_value = {
        "items": [
            {
                "state": "failed",
                "id": 1,
                "batch": "some_batch_id",
                "state_reason": "failed due to timeout",
            }
        ]
    }

    assert wait()["items"] == [
        {
            "state": "failed",
            "id": 1,
            "batch": "some_batch_id",
            "state_reason": "failed due to timeout",
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
@patch("operatorcert.entrypoints.index.output_index_image_paths")
@patch("operatorcert.entrypoints.index.wait_for_results")
def test_add_bundle_to_index(
    mock_results: MagicMock,
    mock_image_paths: MagicMock,
    mock_iib_builds: MagicMock,
) -> None:
    mock_iib_builds.return_value = [{"state": "complete", "batch": "some_batch_id"}]
    mock_results.return_value = {
        "items": [{"state": "complete", "batch": "some_batch_id"}]
    }
    index.add_bundle_to_index(
        "redhat-isv/some-pullspec",
        "https://iib.engineering.redhat.com",
        ["registry/index:v4.9", "registry/index:v4.8"],
        "test-image-path.txt",
    )
    mock_image_paths.assert_called_once_with(
        "test-image-path.txt",
        mock_results.return_value,
    )

    mock_iib_builds.return_value = [{"state": "failed", "batch": "some_batch_id"}]
    mock_results.return_value = {
        "items": [{"state": "failed", "batch": "some_batch_id"}]
    }
    # if there is no version
    with pytest.raises(Exception):
        index.add_bundle_to_index(
            "redhat-isv/some-pullspec",
            "https://iib.engineering.redhat.com",
            ["registry/index:v4.9", "registry/index:v4.8"],
            "test-image-path.txt",
        )


def test_output_index_image_paths() -> None:
    image_output = "test-image-path.txt"
    response = {
        "items": [
            {
                "from_index": "registry/index:v4.8",
                "index_image_resolved": "registry.test/test@sha256:1234",
            },
            {
                "from_index": "registry/index:v4.9",
                "index_image_resolved": "registry.test/test@sha256:5678",
            },
        ]
    }
    mock_open = mock.mock_open()

    with mock.patch("builtins.open", mock_open):
        index.output_index_image_paths(image_output, response)

    mock_open.assert_called_once_with("test-image-path.txt", "w")

    mock_open.return_value.write.assert_called_once_with(
        "registry/index:v4.8+registry.test/test@sha256:1234,"
        "registry/index:v4.9+registry.test/test@sha256:5678"
    )
