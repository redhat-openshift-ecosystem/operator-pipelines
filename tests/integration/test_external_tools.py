import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from operatorcert.integration.external_tools import Ansible, Podman, Secret, Skopeo, run


def test_Secret() -> None:
    secret = Secret("password")
    assert secret == "password"
    assert type(secret) != str


@patch("subprocess.run")
def test_run(mock_run: MagicMock) -> None:
    cmd = ("find", Path("/"), "-type", "f", "-empty")
    run(*cmd, cwd=Path("/foo"), env={"FOO": "bar"})
    mock_run.assert_called_once_with(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        cwd=Path("/foo"),
        env={"FOO": "bar"},
    )


def test_Ansible___init__(operator_pipelines_path: Path) -> None:
    ansible = Ansible(operator_pipelines_path)
    assert ansible.path.resolve(strict=True) == operator_pipelines_path.resolve(
        strict=True
    )


def test_Ansible___init___fail(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _ = Ansible(tmp_path)


def test_Ansible_playbook_dir(operator_pipelines_path: Path) -> None:
    ansible = Ansible(operator_pipelines_path)
    assert (
        ansible.playbook_path("site")
        == operator_pipelines_path / "ansible" / "playbooks" / "site.yml"
    )
    with pytest.raises(FileNotFoundError):
        _ = ansible.playbook_path("nonexistent")


@patch("operatorcert.integration.external_tools.run")
def test_Ansible_run_playbook(
    mock_run: MagicMock, operator_pipelines_path: Path
) -> None:
    ansible = Ansible(operator_pipelines_path)
    ansible.run_playbook("site", "-vv", var1="foo", var2=Secret("bar"))
    mock_run.assert_called_once()
    assert len(mock_run.mock_calls[0].args) == 7
    assert mock_run.mock_calls[0].args[:6] == (
        "ansible-playbook",
        operator_pipelines_path / "ansible" / "playbooks" / "site.yml",
        "-vv",
        "-e",
        "var1=foo",
        "-e",
    )
    assert mock_run.mock_calls[0].args[6].startswith("@")
    assert mock_run.mock_calls[0].kwargs == {"cwd": operator_pipelines_path}


@patch("operatorcert.integration.external_tools.run")
def test_Podman_build(mock_run: MagicMock) -> None:
    podman = Podman()
    podman.build(Path("/foo"), "quay.io/foo/bar", Path("/foo/Dockerfile"), ["-q"])
    mock_run.assert_called_once_with(
        "podman",
        "build",
        "-t",
        "quay.io/foo/bar",
        Path("/foo"),
        "-f",
        Path("/foo/Dockerfile"),
        "-q",
    )


@patch("operatorcert.integration.external_tools.run")
def test_Podman_push(mock_run: MagicMock) -> None:
    podman = Podman(auth={"quay.io/foo": ("username", "password")})
    podman.push("quay.io/foo/bar")
    mock_run.assert_called_once()
    assert mock_run.mock_calls[0].args == ("podman", "push", "quay.io/foo/bar")
    assert "REGISTRY_AUTH_FILE" in mock_run.mock_calls[0].kwargs["env"]


@patch("operatorcert.integration.external_tools.run")
def test_Skopeo_copy(mock_run: MagicMock) -> None:
    skopeo = Skopeo()
    skopeo.copy(
        "docker://quay.io/foo/bar:abc", "docker://quay.io/foo/baz:latest", ["-q"]
    )
    mock_run.assert_called_once_with(
        "skopeo",
        "copy",
        "docker://quay.io/foo/bar:abc",
        "docker://quay.io/foo/baz:latest",
        "-q",
    )


@patch("operatorcert.integration.external_tools.run")
def test_Skopeo_delete(mock_run: MagicMock) -> None:
    skopeo = Skopeo()
    skopeo.delete("docker://quay.io/foo/bar:abc")
    mock_run.assert_called_once_with(
        "skopeo",
        "delete",
        "docker://quay.io/foo/bar:abc",
    )
