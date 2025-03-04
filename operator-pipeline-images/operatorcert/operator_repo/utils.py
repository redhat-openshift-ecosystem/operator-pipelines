"""
Utility functions to load yaml files
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from yaml.composer import ComposerError
from yaml.parser import ParserError

from .exceptions import OperatorRepoException

log = logging.getLogger(__name__)


def _find_yaml(path: Path) -> Path:
    """
    Find a YAML file by looking for files with alternate extensions.

    This function searches for a YAML file by trying multiple extensions (.yaml and .yml)
    and checking if the file exists. It is used to locate YAML files with different possible
    extensions in order to provide flexibility when specifying file paths.

    Args:
        path (Path): The path to the file with or without a YAML extension.

    Returns:
        Path: The path to the found YAML file.

    Raises:
        FileNotFoundError: If a YAML file with any of the tried extensions cannot be found.

    Example:
        file_path = Path("my_file.json")
        yaml_path = _find_yaml(file_path)
        # If "my_file.yaml" or "my_file.yml" exists, yaml_path will point to the found YAML file.
        # Otherwise, a FileNotFoundError will be raised.
    """
    if path.is_file():
        return path
    tries = [path]
    for alt_extension in [".yaml", ".yml"]:
        if alt_extension == path.suffix:
            continue
        new_path = path.with_suffix(alt_extension)
        if new_path.is_file():
            return new_path
        tries.append(new_path)
    tries_str = ", ".join([str(x) for x in tries])
    raise FileNotFoundError(f"Can't find yaml file. Tried: {tries_str}")


def _load_yaml_strict(path: Path) -> Any:
    """
    Load and parse the contents of a YAML file at the given path.

    This function reads the contents of the specified YAML file and attempts to parse it
    using the `yaml.safe_load` method. If the YAML document contains multiple documents or
    if it's not a valid YAML document, exceptions are raised accordingly.

    Args:
        path (Path): The path to the YAML file to be loaded.

    Returns:
        Any: The parsed contents of the YAML file.

    Raises:
        OperatorRepoException: If the YAML file contains multiple documents.
        OperatorRepoException: If the YAML file is not a valid YAML document.

    Example:
        yaml_path = Path("my_file.yaml")
        yaml_content = _load_yaml_strict(yaml_path)
        # The parsed contents of the YAML file will be stored in the `yaml_content` variable.
    """
    log.debug("Loading %s", path)
    with path.open("r") as yaml_file:
        try:
            return yaml.safe_load(yaml_file)
        except ComposerError as exc:
            raise OperatorRepoException(
                f"{path} contains multiple yaml documents"
            ) from exc
        except ParserError as exc:
            raise OperatorRepoException(f"{path} is not a valid yaml document") from exc


def load_yaml(path: Path) -> Any:
    """
    Load and parse the contents of a YAML file at the given path with alternate extensions.

    Args:
        path (Path): The path to the file with or without a YAML extension.

    Returns:
        Any: The parsed contents of the YAML file.

    Raises:
        OperatorRepoException: If the YAML file contains multiple documents.
        OperatorRepoException: If the YAML file is not a valid YAML document.

    Example:
        file_path = Path("my_file.json")
        yaml_content = load_yaml(file_path)
        # If "my_file.yaml" or "my_file.yml" exists, the parsed contents of the YAML file
        # will be stored in the `yaml_content` variable.
    """
    return _load_yaml_strict(_find_yaml(path))


def _load_multidoc_yaml_strict(path: Path) -> list[Any]:
    """
    Load and parse the content of a multi-doc YAML file at the given path.

    This function reads the contents of the specified YAML file and attempts to parse it
    using the `yaml.safe_load_all` method. If the YAML document is not a valid
    YAML document, exceptions is raised.

    Args:
        path (Path): The path to the YAML file to be loaded.

    Returns:
        list[Any]: The parsed contents of the multi-doc YAML file.

    Raises:
        OperatorRepoException: If the YAML file is not a valid YAML document.

    Example:
        yaml_path = Path("my_file.yaml")
        yaml_content = _load_multidoc_yaml_strict(yaml_path)
        # The parsed contents of the YAML file will be stored in the `yaml_content` variable.
    """
    log.debug("Loading %s", path)
    with path.open("r") as yaml_file:
        try:
            return list(yaml.safe_load_all(yaml_file))
        except ParserError as exc:
            raise OperatorRepoException(f"{path} is not a valid yaml document") from exc


def load_multidoc_yaml(path: Path) -> list[dict[str, Any]]:
    """
    Load and parse the contents of a YAML file at the given path.

    Args:
        path (Path): The path to the file with or without a YAML extension.

    Returns:
        list[Any]: The parsed contents of the YAML file. Each element in the list
            represents a document in the multi-doc YAML file. Be aware that the
            elements are not guaranteed to be specific types. They can be any valid
            YAML document - a dictionary, a list, a string, etc.

    Raises:
        OperatorRepoException: If the YAML file is not a valid YAML document.

    Example:
        file_path = Path("my_file.json")
        yaml_content = load_yaml(file_path)
        # If "my_file.yaml" or "my_file.yml" exists, the parsed contents of the YAML file
        # will be stored in the `yaml_content` variable.
    """
    return _load_multidoc_yaml_strict(_find_yaml(path))


def lookup_dict(
    data: dict[str, Any], path: str, default: Any = None, separator: str = "."
) -> Any:
    """
    Retrieve a value from a nested dictionary using a specific path of keys.

    This function allows you to access a value in a nested dictionary by providing a
    dot-separated path of keys. If the path exists in the dictionary, the corresponding
    value is returned. If the path does not exist, the specified default value is returned.

    Args:
        data (dict): The nested dictionary from which to retrieve the value.
        path (str): A dot-separated string representing the path to the desired value.
        default (Any, optional): The value to return if the path does not exist. Defaults to None.
        separator (str, optional): The separator used to split the path into keys. Defaults to ".".

    Returns:
        Any: The value at the specified path if found, otherwise the default value.

    Example:
        data = {
            "a": {
                "b": {
                    "c": 42
                }
            }
        }
        value = lookup_dict(data, "a.b.c")
        # value will be 42
    """
    keys = path.split(separator)
    subtree = data
    for key in keys:
        if key not in subtree:
            return default
        subtree = subtree[key]
    return subtree
