from functools import partial
from unittest import mock
from unittest.mock import MagicMock, patch, call
from typing import Any, List

import pytest

from operatorcert.entrypoints import rm_operator_from_index
from operatorcert.entrypoints.rm_operator_from_index import IndexImage


def test_IndexImage() -> None:
    image = IndexImage("registry/index:v4.15", "iib-pullspec")
    image2 = IndexImage("registry/index:v4.15", "iib-pullspec")
    image3 = IndexImage("registry/index:v4.16", "iib-pullspec")
    assert image.index_image == "registry/index:v4.15"
    assert image.iib_build_image == "iib-pullspec"
    assert image.version == "v4.15"

    assert image.index_pullspec() == "iib-pullspec"
    assert image == image2
    assert image != image3

    assert str(image) == "v4.15 - registry/index:v4.15+iib-pullspec"
    assert repr(image) == "[IndexImage] v4.15 - registry/index:v4.15+iib-pullspec"


@patch("operatorcert.entrypoints.rm_operator_from_index.iib.wait_for_batch_results")
@patch("operatorcert.entrypoints.rm_operator_from_index.iib.add_builds")
def test_rm_operator_from_index(
    mock_iib_add_builds: MagicMock, mock_wait: MagicMock
) -> None:
    index_images = [
        rm_operator_from_index.IndexImage("registry/index:v4.15", "iib-pullspec"),
        rm_operator_from_index.IndexImage("registry/index:v4.16"),
        rm_operator_from_index.IndexImage("registry/index:v4.17"),
    ]
    index_images[0].operators_to_remove = ["op1", "op2"]
    index_images[1].operators_to_remove = ["op3", "op4"]
    mock_iib_add_builds.return_value = [{"batch": "some_batch_id"}]
    mock_wait.return_value = {"items": [{"state": "complete"}, {"state": "complete"}]}
    rm_operator_from_index.rm_operator_from_index(
        index_images, "https://iib.foo.redhat.com"
    )

    mock_iib_add_builds.assert_called_once_with(
        "https://iib.foo.redhat.com",
        {
            "build_requests": [
                {"from_index": "iib-pullspec", "operators": ["op1", "op2"]},
                {"from_index": "registry/index:v4.16", "operators": ["op3", "op4"]},
            ]
        },
    )


@patch("operatorcert.entrypoints.rm_operator_from_index.iib.wait_for_batch_results")
@patch("operatorcert.entrypoints.rm_operator_from_index.iib.add_builds")
def test_rm_operator_from_index_error(
    mock_iib_add_builds: MagicMock, mock_wait: MagicMock
) -> None:
    index_images = [
        rm_operator_from_index.IndexImage("registry/index:v4.15"),
    ]
    index_images[0].operators_to_remove = ["op1", "op2"]
    mock_iib_add_builds.return_value = [{"batch": "some_batch_id"}]
    mock_wait.return_value = {"items": [{"state": "failed"}]}
    with pytest.raises(RuntimeError):
        rm_operator_from_index.rm_operator_from_index(
            index_images, "https://iib.foo.redhat.com"
        )


def test_all_index_images() -> None:

    indices = ["registry/index:v4.15", "registry/index:v4.16", "registry/index:v4.17"]
    fragment_builds = (
        "registry/index:v4.15+iib/index:v4.15,registry/index:v4.16+iib/index:v4.16"
    )

    result = rm_operator_from_index.all_index_images(indices, fragment_builds)

    assert result == [
        IndexImage("registry/index:v4.15", "iib/index:v4.15"),
        IndexImage("registry/index:v4.16", "iib/index:v4.16"),
        IndexImage("registry/index:v4.17"),
    ]


def test_map_operators_to_indices() -> None:
    index_images = [
        IndexImage("registry/index:v4.15", "iib-pullspec"),
        IndexImage("registry/index:v4.16"),
    ]
    operators_to_remove = "v4.15/op1,v4.16/op2,v4.17/op3"
    rm_operator_from_index.map_operators_to_indices(operators_to_remove, index_images)
    assert index_images[0].operators_to_remove == ["op1"]
    assert index_images[1].operators_to_remove == ["op2"]


def test_merge_rm_output_with_fbc_output() -> None:
    index_images = [
        IndexImage("registry/index:v4.15", "iib-pullspec"),
        IndexImage("registry/index:v4.16"),
    ]
    build_response = {
        "items": [
            {"from_index": "iib-pullspec", "index_image_resolved": "foo"},
            {"from_index": "registry/index:v4.16", "index_image_resolved": "bar"},
        ]
    }
    rm_operator_from_index.merge_rm_output_with_fbc_output(index_images, build_response)

    assert index_images[0].iib_build_image == "foo"
    assert index_images[1].iib_build_image == "bar"


def test_save_output_to_file() -> None:
    index_images = [
        IndexImage("registry/index:v4.15", "iib-pullspec"),
        IndexImage("registry/index:v4.16", "iib-pullspec2"),
    ]
    with mock.patch("builtins.open", mock.mock_open()) as mock_open:
        rm_operator_from_index.save_output_to_file(index_images, "test-image-path.txt")

        mock_open.assert_called_once_with("test-image-path.txt", "w", encoding="utf-8")
        mock_open.return_value.write.assert_called_once_with(
            "registry/index:v4.15+iib-pullspec,registry/index:v4.16+iib-pullspec2"
        )


@patch("operatorcert.entrypoints.rm_operator_from_index.save_output_to_file")
@patch(
    "operatorcert.entrypoints.rm_operator_from_index.merge_rm_output_with_fbc_output"
)
@patch("operatorcert.entrypoints.rm_operator_from_index.rm_operator_from_index")
@patch("operatorcert.entrypoints.rm_operator_from_index.map_operators_to_indices")
@patch("operatorcert.entrypoints.rm_operator_from_index.all_index_images")
@patch("operatorcert.entrypoints.rm_operator_from_index.utils.set_client_keytab")
@patch("operatorcert.entrypoints.rm_operator_from_index.setup_logger")
@patch("operatorcert.entrypoints.rm_operator_from_index.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_keytab: MagicMock,
    mock_all_index_images: MagicMock,
    mock_map_operators_to_indices: MagicMock,
    mock_rm_operator_from_index: MagicMock,
    mock_merge_rm_output_with_fbc_output: MagicMock,
    mock_save_output_to_file: MagicMock,
) -> None:
    args = MagicMock()
    args.indices = ["foo:v4.15", "foo:v4.16"]
    args.rm_catalog_operators = ["cat1/op1", "cat2/op2"]
    args.iib_url = "https://iib.foo.redhat.com"
    args.image_output = "test-image-path.txt"

    mock_setup_argparser.return_value.parse_args.return_value = args
    mock_all_index_images.return_value = [MagicMock(), MagicMock()]
    rm_operator_from_index.main()

    mock_rm_operator_from_index.assert_called_once()


def test_setup_argparser() -> None:
    assert rm_operator_from_index.setup_argparser() is not None
