"""
Utility classes to run external tools
"""

import base64
import json
import logging
import subprocess
import tempfile
from os import PathLike
from pathlib import Path
from typing import Mapping, Optional, Sequence, TypeAlias, IO

LOGGER = logging.getLogger("operator-cert")


CommandArg: TypeAlias = str | PathLike[str]


class Secret(str):
    """
    A string with sensitive content that should not be logged
    """


def run(
    *cmd: CommandArg,
    cwd: Optional[CommandArg] = None,
    env: Optional[Mapping[str, str]] = None,
) -> None:
    """
    Execute an external command

    Args:
        *cmd: The command and its arguments
        cwd: Directory to run the command in, by default current working directory
        env: Environment variables, if None the current environment is used

    Raises:
        subprocess.CalledProcessError when the called process exits with a
            non-zero status; the process' stdout and stderr can be obtained
            from the exception object
    """
    LOGGER.debug("Running %s from %s", cmd, cwd or Path.cwd())
    subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        cwd=cwd,
        env=env,
    )


class Ansible:
    """
    Utility class to interact with Ansible
    """

    def __init__(self, path: Optional[Path]) -> None:
        """
        Initialize the Ansible instance

        Args:
            path: The working directory for the ansible commands;
                It must contain an ansible.cfg file
        """
        self.path = (path or Path.cwd()).absolute()
        # Simple sanity check to ensure the directory actually contains
        # a copy of the operator-pipelines project
        ansible_cfg_file = self.path / "ansible.cfg"
        if not ansible_cfg_file.exists():
            raise FileNotFoundError(f"ansible.cfg not found in {self.path}")

    def playbook_path(self, playbook_name: str) -> Path:
        """
        Return the path to the playbook file with the given name; this is specific
        to the operator-pipelines project
        """
        playbook_dir = self.path / "ansible" / "playbooks"
        for ext in ("yml", "yaml"):
            playbook_path = playbook_dir / f"{playbook_name}.{ext}"
            if playbook_path.exists():
                return playbook_path
        raise FileNotFoundError(f"Playbook {playbook_name} not found in {playbook_dir}")

    def run_playbook(
        self, playbook: str, *extra_args: CommandArg, **extra_vars: str | Secret
    ) -> None:
        """
        Run an ansible playbook

        Args:
            playbook: The name of the playbook to execute
            *extra_args: Additional arguments for the ansible playbook
            **extra_vars: Extra variables to pass to the playbook
        """
        command: list[CommandArg] = ["ansible-playbook", self.playbook_path(playbook)]
        command.extend(extra_args)
        secrets = {}
        for k, v in extra_vars.items():
            if isinstance(v, Secret):
                # Avoid adding secrets to the command line
                secrets[k] = str(v)
            else:
                command.extend(["-e", f"{k}={v}"])
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            delete=True,
            delete_on_close=False,
        ) as tmp:
            if secrets:
                json.dump(secrets, tmp)
                command.extend(["-e", f"@{tmp.name}"])
            tmp.close()
            run(*command, cwd=self.path)


class RegistryAuthMixin:
    """
    Mixin class to help running the tools in the podman family (podman, buildah, skopeo)
    with a given set of authentication credentials for the container registries
    """

    def __init__(self, auth: Optional[Mapping[str, tuple[str, str]]] = None):
        self._auth = {
            "auths": {
                registry: {
                    "auth": base64.b64encode(
                        f"{username}:{password}".encode("utf-8")
                    ).decode("ascii")
                }
                for registry, (username, password) in (auth or {}).items()
                if username and password
            }
        }

    def save_auth(self, dest_file: IO[str]) -> None:
        """
        Dump the auth credentials to a json file
        Args:
            dest_file: destination json file
        """
        json.dump(self._auth, dest_file)

    def run(self, *command: CommandArg) -> None:
        """
        Run the given command with the REGISTRY_AUTH_FILE environment variable pointing
        to a temporary file containing a json representation of the credentials in a format
        compatible with podman, buildah and skopeo
        Args:
            *command: command line to execute
        """

        if self._auth["auths"]:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".json",
                delete=True,
                delete_on_close=False,
            ) as tmp:
                self.save_auth(tmp)
                tmp.close()
                LOGGER.debug("Using auth file: %s", tmp.name)
                run(*command, env={"REGISTRY_AUTH_FILE": tmp.name})
        else:
            run(*command)


class Podman(RegistryAuthMixin):
    """
    Utility class to interact with Podman.
    """

    def run(self, *args: CommandArg) -> None:
        """
        Run a podman subcommand

        Args:
            *args: The podman subcommand and its arguments
        """
        super().run("podman", *args)

    def build(
        self,
        context: CommandArg,
        image: str,
        containerfile: Optional[CommandArg] = None,
        extra_args: Optional[Sequence[CommandArg]] = None,
    ) -> None:
        """
        Build an image

        Args:
            context: Directory to build the image from
            image: The name of the image to build
            containerfile: The path to the container configuration file,
                if not specified it will be inferred by podman
            extra_args: Additional arguments for the podman build command
        """
        command: list[CommandArg] = ["build", "-t", image, context]
        if containerfile:
            command.extend(["-f", containerfile])
        if extra_args:
            command.extend(extra_args)
        self.run(*command)

    def push(self, image: str) -> None:
        """
        Push an image to a registry.

        Args:
            image: The name of the image to push.
        """
        self.run("push", image)


class Skopeo(RegistryAuthMixin):
    """
    Utility class to interact with Skopeo.
    """

    def run(self, *args: CommandArg) -> None:
        """
        Run a skopeo subcommand

        Args:
            *args: The skopeo subcommand and its arguments
        """
        super().run("skopeo", *args)

    def copy(
        self,
        from_image: str,
        to_image: str,
        extra_args: Optional[Sequence[CommandArg]] = None,
    ) -> None:
        """
        Copy a container image

        Args:
            from_image: source container image ref
            to_image: destination image ref
            extra_args: optional args to add to the skopeo command line
        """

        command: list[CommandArg] = ["copy", from_image, to_image]
        if extra_args:
            command.extend(extra_args)
        self.run(*command)

    def delete(
        self,
        image: str,
    ) -> None:
        """
        Delete a container image

        Args:
            image: container image ref
        """

        self.run("delete", image)
