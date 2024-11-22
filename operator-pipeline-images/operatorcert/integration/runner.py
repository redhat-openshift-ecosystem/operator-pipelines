"""
Core module for the integration test framework
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional

import openshift_client as oc

from operatorcert.integration.config import Config
from operatorcert.integration.external_tools import Ansible, Podman, Secret

LOGGER = logging.getLogger("operator-cert")


def _build_and_push_image(
    project_dir: Path, image: str, auth: Optional[Mapping[str, tuple[str, str]]] = None
) -> None:
    """
    Build the operator-pipelines container image and push it to the registry

    Args:
        project_dir: base directory of the operator-pipeline project
        image: tagged reference to the image on the destination container registry
        auth: registry authentication information
    """
    podman = Podman(auth)
    LOGGER.info("Building image %s", image)
    podman.build(
        project_dir,
        image,
        project_dir / "operator-pipeline-images" / "Dockerfile",
        # enforce a two days lifetime on the image pushed to quay
        ["--label", "quay.expires-after=48h"],
    )
    LOGGER.info("Pushing image %s", image)
    podman.push(image)


def _deploy_pipelines(project_dir: Path, namespace: str, image: str) -> None:
    """
    Deploy the operator-pipelines tekton components to the given namespace on
    an openshift cluster; the current user must be already authenticated to the
    openshift cluster

    Args:
        project_dir: base directory of the operator-pipeline project
        namespace: namespace to deploy to
        image: reference to the operator-pipelines container image to use
    """
    ansible = Ansible(project_dir)
    LOGGER.info("Deploying pipelines to namespace %s", namespace)
    ansible.run_playbook(
        "deploy",
        "-vv",
        "--skip-tags",
        "ci,import-index-images",
        "--vault-password-file",
        "ansible/vault-password",
        oc_namespace=namespace,
        operator_pipeline_image_pull_spec=image,
        suffix="inttest",
        ocp_token=Secret(oc.get_auth_token()),
        env="stage",
        branch=namespace,
    )


def run_integration_tests(
    project_dir: Path, config_path: Path, image: Optional[str] = None
) -> int:
    """
    Run the integration tests

    Args:
        project_dir: base directory of the operator-pipeline project
        config_path: path to yaml config file containing the integration tests parameters
        image: tagged reference to the image on the destination container registry

    Returns:
        0 on success, 1 on failure
    """
    if not config_path.exists():
        LOGGER.fatal("Config file %s does not exist", config_path)
        return 1
    if not project_dir.exists():
        LOGGER.fatal("Directory %s does not exist", config_path)
        return 1
    oc_context = oc.get_config_context()
    if oc_context is None:
        LOGGER.fatal(
            "A valid connection to an OpenShift cluster is required: "
            "please log into the cluster using the `oc login` command"
        )
        return 1
    LOGGER.debug("Connected to %s", oc_context.strip())
    cfg = Config.from_yaml(config_path)
    test_id = datetime.now().strftime("%Y%m%d%H%M%S")
    namespace = f"inttest-{test_id}"
    try:
        if image:
            tagged_image_name = image
        else:
            image_name = f"{cfg.test_registry.base_ref}/operator-pipeline-images"
            tagged_image_name = f"{image_name}:{test_id}"
            auth = (
                {image_name: (cfg.test_registry.username, cfg.test_registry.password)}
                if cfg.test_registry.username and cfg.test_registry.password
                else None
            )
            _build_and_push_image(
                project_dir,
                tagged_image_name,
                auth=auth,
            )
        _deploy_pipelines(project_dir, namespace, tagged_image_name)
    except subprocess.CalledProcessError as e:
        LOGGER.error("Command %s failed:", e.cmd)
        for line in e.stdout.decode("utf-8").splitlines():
            LOGGER.error("%s", line.rstrip())
        return 1
    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("%s", e)
        return 1
    finally:
        LOGGER.debug("Cleaning up namespace %s", namespace)
        oc.delete_project(namespace, ignore_not_found=True)
    LOGGER.info("Integration tests completed successfully")
    return 0
