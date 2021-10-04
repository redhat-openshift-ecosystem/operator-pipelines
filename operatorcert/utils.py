import json
import logging
import os
import pathlib
from typing import Dict, List, Optional, Tuple

LOGGER = logging.getLogger("operator-cert")


def find_file(
    base_path: pathlib.Path, relative_paths: List[Tuple[str, ...]]
) -> Optional[pathlib.Path]:
    """
    Finds the first file that exists in a list of relative paths.

    Args:
        base_path (Path): A root path to start from
        relative_paths (List[Tuple[str]]): An ordered list of relative paths
            (in tuples) to look for.

    Returns:
        A Path object for the first file found; None otherwise.
    """
    for path in relative_paths:
        new_path = base_path.joinpath(*path)
        if new_path.exists() and new_path.is_file():
            return new_path
    return None


def store_results(results: Dict[str, str]):
    """
    Store the given results into files in given directory.

    Args:
        results (Dict): Dictionary, where key is a result name (name of file to store value),
        and value is result value (to be stored in file).
    """
    for result_name, result_value in results.items():
        if result_value is None:
            result_value = ""
            logging.error(f"Result {result_name} is empty")
        logging.debug(f"Storing {result_name}")
        with open(result_name, "w") as result_file:
            if type(result_value) is dict:
                json.dump(result_value, result_file)
            else:
                result_file.write(str(result_value))


def get_registry_for_env(environment: str) -> str:
    """
    Mapping of container registry based on current environment

    Args:
        environment (str): Environment name

    Returns:
        str: Connect registry for current
    """
    env_to_registry = {
        "production": "registry.connect.redhat.com",
        "stage": "registry.connect.stage.redhat.com",
        "qa": "registry.connect.qa.redhat.com",
        "dev": "registry.connect.dev.redhat.com",
    }

    return env_to_registry[environment]


def set_client_keytab(keytab_file: str):
    """
    Set env variable with default client keytab.
    Args:
        keytab_file (path): path to keytab file (default /etc/krb5.krb)
    """
    if not keytab_file:
        return
    if not os.path.isfile(keytab_file):
        raise IOError("Keytab file %s does not exist", keytab_file)
    os.environ["KRB5_CLIENT_KTNAME"] = "FILE:{}".format(keytab_file)
    LOGGER.debug(
        "Set KRB5_CLIENT_KTNAME env variable: %s", os.environ["KRB5_CLIENT_KTNAME"]
    )
