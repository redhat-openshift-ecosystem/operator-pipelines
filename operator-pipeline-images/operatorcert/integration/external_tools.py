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
from typing import Mapping, Optional, Sequence, TypeAlias

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


class Podman:
    """
    Utility class to interact with Podman.
    """

    def __init__(self, auth: Optional[Mapping[str, tuple[str, str]]] = None):
        """
        Initialize the Podman instance

        Args:
            auth: The authentication credentials for registries
        """
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

    def _run(self, *args: CommandArg) -> None:
        """
        Run a podman subcommand

        Args:
            *args: The podman subcommand and its arguments
        """
        command: list[CommandArg] = ["podman"]
        command.extend(args)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            delete=True,
            delete_on_close=False,
        ) as tmp:
            json.dump(self._auth, tmp)
            tmp.close()
            LOGGER.debug("Using podman auth file: %s", tmp.name)
            run(*command, env={"REGISTRY_AUTH_FILE": tmp.name})

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
        self._run(*command)

    def push(self, image: str) -> None:
        """
        Push an image to a registry.

        Args:
            image: The name of the image to push.
        """
        self._run("push", image)
