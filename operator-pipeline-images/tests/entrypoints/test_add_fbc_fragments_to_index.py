from functools import partial
from unittest import mock
from unittest.mock import MagicMock, patch, call
from typing import Any, List

import pytest

from operatorcert.entrypoints import add_fbc_fragments_to_index as index


@patch("operatorcert.iib.get_build")
def test_wait_for_results(mock_get_build: MagicMock) -> None:
    wait = partial(
        index.wait_for_results,
        "https://iib.engineering.redhat.com",
        [1, 2],
        delay=0.1,
        timeout=0.1,
    )

    # if the fragment adds are in complete state
    mock_get_build.side_effect = [
        {"state": "complete", "id": 1},
        {"state": "complete", "id": 2},
    ]

    assert wait() == [
        {"state": "complete", "id": 1},
        {"state": "complete", "id": 2},
    ]

    # if the fragment adds are in failed state
    mock_get_build.side_effect = [
        {
            "state": "failed",
            "id": 1,
            "state_reason": "failed due to timeout",
        },
        {
            "state": "failed",
            "id": 2,
            "state_reason": "failed due to timeout",
        },
    ]

    assert wait() == [
        {
            "state": "failed",
            "id": 1,
            "state_reason": "failed due to timeout",
        },
        {
            "state": "failed",
            "id": 2,
            "state_reason": "failed due to timeout",
        },
    ]

    # if not all fragment adds are completed
    mock_get_build.side_effect = [
        {
            "state": "complete",
            "id": 1,
        },
        {
            "state": "failed",
            "id": 2,
            "state_reason": "failed due to timeout",
        },
    ]

    assert wait() == [
        {"state": "complete", "id": 1},
        {"state": "failed", "id": 2, "state_reason": "failed due to timeout"},
    ]

    # if there are no failed fragment adds
    # still all of the builds are not completed
    mock_get_build.side_effect = [
        {"state": "complete", "id": 1},
        {"state": "pending", "id": 2},
    ]

    assert wait() is None


@pytest.mark.parametrize(
    ["indices", "catalogs", "repository", "sha", "expected"],
    [
        pytest.param(
            ["foo:v4.15", "foo:v4.16"],
            ["v4.15", "v4.16"],
            "registry.foo/repo/catalog",
            "sha256:1234",
            [
                ("foo:v4.15", "registry.foo/repo/catalog:v4.15-fragment-sha256:1234"),
                ("foo:v4.16", "registry.foo/repo/catalog:v4.16-fragment-sha256:1234"),
            ],
            id="multiple fragments match to indices",
        ),
        pytest.param(
            ["foo:v4.15", "foo:v4.16"],
            ["v4.13", "v4.16"],
            "registry.foo/repo/catalog",
            "sha256:1234",
            [
                ("foo:v4.16", "registry.foo/repo/catalog:v4.16-fragment-sha256:1234"),
            ],
            id="one fragment match to indices",
        ),
        pytest.param(
            ["foo:v4.15", "foo:v4.16"],
            ["v4.13", "v4.14"],
            "registry.foo/repo/catalog",
            "sha256:1234",
            None,
            id="no fragment match for given indices",
        ),
        pytest.param(
            [],
            [],
            "registry.foo/repo/catalog",
            "sha256:1234",
            None,
            id="no indices or catalogs",
        ),
    ],
)
def test_map_index_to_fragment(
    indices: List[str],
    catalogs: List[str],
    repository: str,
    sha: str,
    expected: Any,
) -> None:
    if not expected:
        with pytest.raises(RuntimeError):
            index.map_index_to_fragment(indices, catalogs, repository, sha)
    else:
        assert (
            index.map_index_to_fragment(indices, catalogs, repository, sha) == expected
        )


@patch("operatorcert.iib.add_fbc_build")
@patch("operatorcert.entrypoints.add_fbc_fragments_to_index.output_index_image_paths")
@patch("operatorcert.entrypoints.add_fbc_fragments_to_index.wait_for_results")
def test_add_fbc_fragment_to_index(
    mock_results: MagicMock,
    mock_image_paths: MagicMock,
    mock_iib_build: MagicMock,
) -> None:
    # happy path
    mock_iib_build.side_effect = [
        {"state": "pending", "id": 1},
        {"state": "pending", "id": 2},
    ]
    mock_results.return_value = [
        {"state": "complete", "id": 1},
        {"state": "complete", "id": 2},
    ]
    index.add_fbc_fragment_to_index(
        "https://iib.engineering.redhat.com",
        [
            (
                "registry/index:v4.15",
                "registry.foo/repo/foo:v4.15-fragment-sha256:1234",
            ),
            (
                "registry/index:v4.16",
                "registry.foo/repo/bar:v4.16-fragment-sha256:1234",
            ),
        ],
        "test-image-path.txt",
    )
    mock_iib_build.assert_has_calls(
        [
            call(
                "https://iib.engineering.redhat.com",
                {
                    "from_index": "registry/index:v4.15",
                    "fbc_fragment": "registry.foo/repo/foo:v4.15-fragment-sha256:1234",
                },
            ),
            call(
                "https://iib.engineering.redhat.com",
                {
                    "from_index": "registry/index:v4.16",
                    "fbc_fragment": "registry.foo/repo/bar:v4.16-fragment-sha256:1234",
                },
            ),
        ]
    )
    mock_image_paths.assert_called_once_with(
        "test-image-path.txt",
        mock_results.return_value,
    )

    # if the IIB build fails
    mock_iib_build.reset_mock()
    mock_iib_build.side_effect = [{"state": "pending", "id": 1}]
    mock_results.return_value = None
    with pytest.raises(RuntimeError):
        index.add_fbc_fragment_to_index(
            "https://iib.engineering.redhat.com",
            [("foo", "bar")],
            "test-image-path.txt",
        )


def test_output_index_image_paths() -> None:
    image_output = "test-image-path.txt"
    responses = [
        {
            "from_index": "registry/index:v4.8",
            "index_image_resolved": "registry.test/test@sha256:1234",
        },
        {
            "from_index": "registry/index:v4.9",
            "index_image_resolved": "registry.test/test@sha256:5678",
        },
    ]
    mock_open = mock.mock_open()

    with mock.patch("builtins.open", mock_open):
        index.output_index_image_paths(image_output, responses)

    mock_open.assert_called_once_with("test-image-path.txt", "w", encoding="utf-8")

    mock_open.return_value.write.assert_called_once_with(
        "registry/index:v4.8+registry.test/test@sha256:1234,"
        "registry/index:v4.9+registry.test/test@sha256:5678"
    )


@patch(
    "operatorcert.entrypoints.add_fbc_fragments_to_index.utils.copy_images_to_destination"
)
@patch("operatorcert.entrypoints.add_fbc_fragments_to_index.add_fbc_fragment_to_index")
@patch("operatorcert.entrypoints.add_fbc_fragments_to_index.map_index_to_fragment")
@patch("operatorcert.entrypoints.add_fbc_fragments_to_index.utils.set_client_keytab")
@patch("operatorcert.entrypoints.add_fbc_fragments_to_index.setup_logger")
@patch("operatorcert.entrypoints.add_fbc_fragments_to_index.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_keytab: MagicMock,
    mock_mapping: MagicMock,
    mock_add_fbc: MagicMock,
    mock_copy_images: MagicMock,
) -> None:
    args = MagicMock()
    args.indices = ["foo:v4.15", "foo:v4.16"]
    args.catalog_names = ["catalog1", "catalog2"]
    args.image_repository = "registry.foo/repo/catalog"
    args.commit_sha = "sha256:1234"
    args.iib_url = "https://iib.engineering.redhat.com"
    args.image_output = "test-image-path.txt"
    args.hosted = True

    mock_setup_argparser.return_value.parse_args.return_value = args
    mock_mapping.return_value = [("foo", "bar")]
    mock_add_fbc.return_value = [{"foo": "bar"}]

    index.main()

    mock_mapping.assert_called_once_with(
        args.indices,
        args.catalog_names,
        args.image_repository,
        args.commit_sha,
    )
    mock_add_fbc.assert_called_once_with(
        args.iib_url,
        mock_mapping.return_value,
        args.image_output,
    )
    mock_copy_images.assert_called_once_with(
        mock_add_fbc.return_value,
        args.image_repository,
        args.commit_sha,
        args.authfile,
    )


def test_setup_argparser() -> None:
    assert index.setup_argparser() is not None
