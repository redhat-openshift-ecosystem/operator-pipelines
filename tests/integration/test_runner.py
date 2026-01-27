import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from operatorcert.integration.runner import (
    _build_and_push_image,
    _deploy_pipelines,
    run_integration_tests,
)


@patch("operatorcert.integration.external_tools.Podman.build")
@patch("operatorcert.integration.external_tools.Podman.push")
def test__build_and_push_image(mock_push: MagicMock, mock_build: MagicMock) -> None:
    _build_and_push_image(
        Path("/foo"),
        "quay.io/foo/bar:latest",
        auth={"quay.io/foo": ("username", "password")},
    )
    mock_build.assert_called_once()
    mock_push.assert_called_once()


@patch("operatorcert.integration.external_tools.Ansible.run_playbook")
@patch("openshift_client.get_auth_token")
def test__deploy_pipelines(
    mock_get_auth_token: MagicMock,
    mock_run_playbook: MagicMock,
    operator_pipelines_path: Path,
) -> None:
    mock_get_auth_token.return_value = "secret"
    _deploy_pipelines(operator_pipelines_path, "namespace", "quay.io/foo/bar:latest")
    mock_run_playbook.assert_called_once()
    mock_get_auth_token.assert_called_once()


@patch("operatorcert.integration.runner._build_and_push_image")
@patch("operatorcert.integration.runner._deploy_pipelines")
@patch("openshift_client.delete_project")
@patch("openshift_client.get_config_context")
@patch("operatorcert.integration.runner.datetime")
@patch("operatorcert.integration.runner.run_tests")
def test_run_integration_tests(
    mock_run_tests: MagicMock,
    mock_datetime: MagicMock,
    mock_get_config_context: MagicMock,
    mock_delete_project: MagicMock,
    mock_deploy_pipelines: MagicMock,
    mock_build_and_push_image: MagicMock,
    operator_pipelines_path: Path,
    integration_tests_config_file: Path,
) -> None:
    mock_run_tests.return_value = 0
    mock_datetime.now.return_value = datetime(2024, 11, 25, 12, 34, 56)
    mock_get_config_context.return_value = (
        "default/api-my-openshift-cluster:6443/user\n"
    )

    # Non-existent directory: fail
    assert (
        run_integration_tests(Path("/doesnotexist"), integration_tests_config_file) == 1
    )
    mock_build_and_push_image.assert_not_called()
    mock_deploy_pipelines.assert_not_called()
    mock_build_and_push_image.reset_mock()
    mock_deploy_pipelines.reset_mock()

    # Non-existent config file: fail
    assert run_integration_tests(operator_pipelines_path, Path("/doesnotexist")) == 1
    mock_build_and_push_image.assert_not_called()
    mock_deploy_pipelines.assert_not_called()
    mock_build_and_push_image.reset_mock()
    mock_deploy_pipelines.reset_mock()

    # Regular run - no image specified
    assert (
        run_integration_tests(operator_pipelines_path, integration_tests_config_file)
        == 0
    )
    mock_build_and_push_image.assert_called_once_with(
        operator_pipelines_path,
        "quay.io/user2/operator-pipeline-images:20241125123456",
        auth={"quay.io/user2/operator-pipeline-images": ("user2", "secret2")},
    )
    mock_deploy_pipelines.assert_called_once_with(
        operator_pipelines_path,
        "inttest-20241125123456",
        "quay.io/user2/operator-pipeline-images:20241125123456",
    )
    mock_build_and_push_image.reset_mock()
    mock_deploy_pipelines.reset_mock()

    # Regular run - custom image specified
    assert (
        run_integration_tests(
            operator_pipelines_path,
            integration_tests_config_file,
            "quay.io/foo/bar:latest",
        )
        == 0
    )
    mock_build_and_push_image.assert_not_called()
    mock_deploy_pipelines.assert_called_once_with(
        operator_pipelines_path,
        "inttest-20241125123456",
        "quay.io/foo/bar:latest",
    )
    mock_build_and_push_image.reset_mock()
    mock_deploy_pipelines.reset_mock()

    # Ansible playbook failure - fail
    mock_deploy_pipelines.side_effect = subprocess.CalledProcessError(
        1, ["ansible-playbook"], output=b"failed", stderr=b""
    )
    assert (
        run_integration_tests(operator_pipelines_path, integration_tests_config_file)
        == 1
    )
    mock_build_and_push_image.reset_mock()
    mock_deploy_pipelines.reset_mock()
    mock_build_and_push_image.reset_mock()
    mock_deploy_pipelines.reset_mock()

    # Other unexpected failures - fail
    mock_deploy_pipelines.side_effect = Exception()
    assert (
        run_integration_tests(operator_pipelines_path, integration_tests_config_file)
        == 1
    )
    mock_build_and_push_image.reset_mock()
    mock_deploy_pipelines.reset_mock()

    # Not logged into openshift - fail
    mock_get_config_context.return_value = None
    assert (
        run_integration_tests(operator_pipelines_path, integration_tests_config_file)
        == 1
    )
    mock_build_and_push_image.assert_not_called()
    mock_deploy_pipelines.assert_not_called()
