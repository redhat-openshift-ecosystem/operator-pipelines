from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

from operatorcert.entrypoints.set_cert_project_repository import (
    set_cert_project_repository,
)


@patch("operatorcert.entrypoints.set_cert_project_repository.pyxis.patch")
def test_set_cert_project_repository(
    mock_patch: MagicMock,
) -> None:
    args = MagicMock()
    args.pyxis_url = "https://example.com"
    args.cert_project_id = "id1234"
    args.registry = "registry.example.com"
    args.repository = "namespace/name"
    args.docker_config = StringIO('{"auths":{"registry.example.com":{"auth":"Fake"}}}')

    mock_patch.return_value = {}

    set_cert_project_repository(args)

    mock_patch.assert_called_once_with(
        "https://example.com/v1/projects/certification/id/id1234",
        {
            "container": {
                "registry": "registry.example.com",
                "repository": "namespace/name",
                "docker_config_json": '{"auths":{"registry.example.com":{"auth":"Fake"}}}',
            },
        },
    )
