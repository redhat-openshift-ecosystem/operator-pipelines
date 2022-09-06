import json
from datetime import datetime
from unittest import mock
from unittest.mock import patch, MagicMock

from operatorcert.entrypoints.create_container_image import (
    check_if_image_already_exists,
    create_container_image,
    prepare_parsed_data,
    remove_latest_from_previous_image,
    main,
)


@patch("operatorcert.entrypoints.create_container_image.pyxis.get")
def test_check_if_image_already_exists(mock_get: MagicMock):
    # Arrange
    mock_rsp = MagicMock()
    mock_get.return_value = mock_rsp

    args = MagicMock()
    args.pyxis_url = "https://catalog.redhat.com/api/containers/"
    args.isv_pid = "some_isv_pid"
    args.docker_image_digest = "some_digest"

    # Image already exist
    mock_rsp.json.return_value = {"data": [{}]}

    # Act
    exists = check_if_image_already_exists(args)
    # Assert
    assert exists
    mock_get.assert_called_with(
        "https://catalog.redhat.com/api/containers/v1/images?page_size=1&filter=isv_pid%3D%3D%22some_isv_pid%22%3Bdocker_image_digest%3D%3D%22some_digest%22%3Bnot%28deleted%3D%3Dtrue%29"
    )

    # Image doesn't exist
    mock_rsp.json.return_value = {"data": []}

    # Act
    exists = check_if_image_already_exists(args)
    # Assert
    assert not exists


@patch("operatorcert.entrypoints.create_container_image.pyxis.post")
@patch("operatorcert.entrypoints.create_container_image.prepare_parsed_data")
@patch("operatorcert.entrypoints.create_container_image.datetime")
def test_create_container_image(
    mock_datetime: MagicMock, mock_prepare_parsed: MagicMock, mock_post: MagicMock
):
    # Arrange
    mock_post.return_value = "ok"
    mock_prepare_parsed.return_value = {"architecture": "ok"}

    # mock date
    mock_datetime.now = MagicMock(return_value=datetime(1970, 10, 10, 10, 10, 10))

    args = MagicMock()
    args.pyxis_url = "https://catalog.redhat.com/api/containers/"
    args.isv_pid = "some_isv_pid"
    args.connect_registry = "registry.connect.redhat.com"
    args.repository = "some_repo"
    args.docker_image_digest = "some_digest"
    args.bundle_version = "some_version"

    # Act
    rsp = create_container_image(args, {}, [{"Size": 1}])

    # Assert
    assert rsp == "ok"
    mock_post.assert_called_with(
        "https://catalog.redhat.com/api/containers/v1/images",
        {
            "isv_pid": "some_isv_pid",
            "repositories": [
                {
                    "published": True,
                    "registry": "registry.connect.redhat.com",
                    "repository": "some_repo",
                    "push_date": "1970-10-10T10:10:10.000000+00:00",
                    "tags": [
                        {
                            "added_date": "1970-10-10T10:10:10.000000+00:00",
                            "name": "some_version",
                        }
                    ],
                }
            ],
            "certified": True,
            "docker_image_digest": "some_digest",
            "image_id": "some_digest",
            "architecture": "ok",
            "parsed_data": {"architecture": "ok"},
            "sum_layer_size_bytes": 1,
        },
    )


@patch("operatorcert.entrypoints.create_container_image.pyxis.post")
@patch("operatorcert.entrypoints.create_container_image.prepare_parsed_data")
@patch("operatorcert.entrypoints.create_container_image.datetime")
def test_create_container_image_latest(
    mock_datetime: MagicMock, mock_prepare_parsed: MagicMock, mock_post: MagicMock
):
    # Arrange
    mock_post.return_value = "ok"
    mock_prepare_parsed.return_value = {"architecture": "ok"}

    # mock date
    mock_datetime.now = MagicMock(return_value=datetime(1970, 10, 10, 10, 10, 10))

    args = MagicMock()
    args.pyxis_url = "https://catalog.redhat.com/api/containers/"
    args.isv_pid = "some_isv_pid"
    args.connect_registry = "registry.connect.redhat.com"
    args.repository = "some_repo"
    args.docker_image_digest = "some_digest"
    args.bundle_version = "some_version"
    args.is_latest = "true"

    # Act
    rsp = create_container_image(args, {}, [{"Size": 1}])

    # Assert
    assert rsp == "ok"
    mock_post.assert_called_with(
        "https://catalog.redhat.com/api/containers/v1/images",
        {
            "isv_pid": "some_isv_pid",
            "repositories": [
                {
                    "published": True,
                    "registry": "registry.connect.redhat.com",
                    "repository": "some_repo",
                    "push_date": "1970-10-10T10:10:10.000000+00:00",
                    "tags": [
                        {
                            "added_date": "1970-10-10T10:10:10.000000+00:00",
                            "name": "some_version",
                        },
                        {
                            "added_date": "1970-10-10T10:10:10.000000+00:00",
                            "name": "latest",
                        },
                    ],
                }
            ],
            "certified": True,
            "docker_image_digest": "some_digest",
            "image_id": "some_digest",
            "architecture": "ok",
            "parsed_data": {"architecture": "ok"},
            "sum_layer_size_bytes": 1,
        },
    )


def test_prepare_parsed_data():
    # Arrange
    file_content = {
        "DockerVersion": "1",
        "Layers": ["1", "2"],
        "Architecture": "test",
        "Env": ["a=test"],
    }

    # Act
    parsed_data = prepare_parsed_data(file_content)

    # Assert
    assert parsed_data == {
        "architecture": "test",
        "docker_version": "1",
        "env_variables": ["a=test"],
        "layers": ["1", "2"],
    }


@patch("operatorcert.entrypoints.create_container_image.pyxis.get")
@patch("operatorcert.entrypoints.create_container_image.pyxis.put")
def test_remove_latest_from_previous_image(mock_put: MagicMock, mock_get: MagicMock):
    pyxis_url = "some_url.com"
    isv_pid = "some_pid"

    mock_rsp = MagicMock()
    mock_get.return_value = mock_rsp

    mock_rsp.json.return_value = {
        "data": [
            {
                "_id": "1234",
                "repositories": [
                    {"tags": [{"name": "latest"}, {"name": "some_other"}]},
                ],
            }
        ]
    }

    remove_latest_from_previous_image(pyxis_url, isv_pid)

    mock_put.assert_called_with(
        "v1/images/id/1234",
        {
            "_id": "1234",
            "repositories": [{"tags": [{"name": "some_other"}]}],
        },
    )

    # for no query results

    mock_rsp = MagicMock()
    mock_get.return_value = mock_rsp

    mock_rsp.json.return_value = {"data": []}
    remove_latest_from_previous_image(pyxis_url, isv_pid)
