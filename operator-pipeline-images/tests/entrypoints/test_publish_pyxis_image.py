import json
from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch

import operatorcert.entrypoints.publish_pyxis_image as publish_pyxis_image


def test_setup_argparser() -> None:
    parser = publish_pyxis_image.setup_argparser()

    assert parser


@patch("operatorcert.entrypoints.publish_pyxis_image.pyxis.wait_for_image_request")
@patch("operatorcert.entrypoints.publish_pyxis_image.pyxis.post_image_request")
def test_submit_image_request(
    mock_post_image_request: MagicMock, mock_wait_for_image_request: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "https://catalog.redhat.com/api/containers/"
    args.cert_project_id = "project_id"
    args.image_identifier = "image_id"

    mock_post_image_request.return_value = {"_id": "123"}
    mock_wait_for_image_request.return_value = {"status": "completed", "_id": "123"}

    result = publish_pyxis_image.submit_image_request(args)

    assert result == mock_wait_for_image_request.return_value

    mock_post_image_request.assert_called_with(
        "https://catalog.redhat.com/api/containers/",
        "project_id",
        "image_id",
        "publish",
    )

    mock_wait_for_image_request.assert_called_with(
        "https://catalog.redhat.com/api/containers/",
        mock_post_image_request.return_value["_id"],
    )


@patch("operatorcert.entrypoints.publish_pyxis_image.pyxis.wait_for_image_request")
@patch("operatorcert.entrypoints.publish_pyxis_image.pyxis.post_image_request")
def test_submit_image_request_error(
    mock_post_image_request: MagicMock, mock_wait_for_image_request: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "https://catalog.redhat.com/api/containers/"
    args.cert_project_id = "project_id"
    args.image_identifier = "image_id"

    mock_post_image_request.return_value = {"_id": "123"}
    mock_wait_for_image_request.return_value = {
        "status": "failed",
        "_id": "123",
        "status_message": "message  ",
    }

    with pytest.raises(SystemExit):
        publish_pyxis_image.submit_image_request(args)


@pytest.mark.parametrize(
    "pyxis_url, expected",
    [
        pytest.param("https:/pyxis.engineering.redhat.com", True, id="prod"),
        pytest.param("https:/pyxis.stage.engineering.redhat.com", True, id="stage"),
        pytest.param("https:/pyxis.dev.engineering.redhat.com", True, id="dev"),
        pytest.param("https:/pyxis.qa.engineering.redhat.com", False, id="qa"),
        pytest.param("https:/pyxis.uat.engineering.redhat.com", False, id="uat"),
    ],
)
def test_is_clair_enabled(pyxis_url: str, expected: bool) -> None:
    assert publish_pyxis_image.is_clair_enabled(pyxis_url) == expected


@patch("operatorcert.entrypoints.publish_pyxis_image.is_clair_enabled")
@patch("operatorcert.entrypoints.publish_pyxis_image.pyxis.wait_for_container_grades")
@patch("operatorcert.entrypoints.publish_pyxis_image.submit_image_request")
@patch("operatorcert.entrypoints.publish_pyxis_image.setup_logger")
@patch("operatorcert.entrypoints.publish_pyxis_image.setup_argparser")
def test_main(
    mock_setup_argparser: MagicMock,
    mock_setup_logger: MagicMock,
    mock_submit_image_request: MagicMock,
    mock_wait_for_grades: MagicMock,
    mock_is_clair_enabled: MagicMock,
) -> None:
    mock_is_clair_enabled.return_value = True
    mock_setup_argparser.return_value.parse_args.return_value = MagicMock(
        pyxis_url="https://catalog.redhat.com/api/containers/",
        cert_project_id="project_id",
        image_identifier="image_id",
        wait_for_grades=True,
        verbose=True,
    )
    publish_pyxis_image.main()

    mock_setup_argparser.assert_called_once()
    mock_setup_logger.assert_called_once()
    mock_submit_image_request.assert_called_once()
