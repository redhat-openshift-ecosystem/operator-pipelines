from functools import partial
from unittest import mock
from unittest.mock import MagicMock, patch, call

import pytest

from operatorcert.entrypoints import index


@patch("operatorcert.iib.add_builds")
@patch("operatorcert.entrypoints.index.output_index_image_paths")
@patch("operatorcert.entrypoints.index.iib.wait_for_batch_results")
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
        "replaces",
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
    with pytest.raises(RuntimeError):
        index.add_bundle_to_index(
            "redhat-isv/some-pullspec",
            "https://iib.engineering.redhat.com",
            ["registry/index:v4.9", "registry/index:v4.8"],
            "test-image-path.txt",
            "replaces",
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

    mock_open.assert_called_once_with("test-image-path.txt", "w", encoding="utf-8")

    mock_open.return_value.write.assert_called_once_with(
        "registry/index:v4.8+registry.test/test@sha256:1234,"
        "registry/index:v4.9+registry.test/test@sha256:5678"
    )
