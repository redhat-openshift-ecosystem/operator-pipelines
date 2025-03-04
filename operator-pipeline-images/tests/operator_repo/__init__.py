from pathlib import Path
from typing import Any, Optional, Union

import yaml


def merge(
    dst: dict[Any, Any], src: dict[Any, Any], path: Optional[list[str]] = None
) -> dict[Any, Any]:
    """
    Recursively merge two dictionaries, with values from the second dictionary (src)
    overwriting corresponding values in the first dictionary (dst). This function can
    handle nested dictionaries.

    Args:
        dst (dict): The base dictionary to merge into.
        src (dict): The dictionary with values to merge into the base dictionary.
        path (list of str, optional): A list representing the current path in the recursive merge.
            This argument is used internally for handling nested dictionaries. Users typically
            don't need to provide this argument. Defaults to None.

    Returns:
        dict: The merged dictionary (dst) after incorporating values from the second dictionary (src).

    Example:
        dict_a = {"key1": 42, "key2": {"subkey1": "value1"}}
        dict_b = {"key2": {"subkey2": "value2"}, "key3": "value3"}
        merged_dict = merge(dict_a, dict_b)
        # merged_dict will be:
        # {"key1": 42, "key2": {"subkey1": "value1", "subkey2": "value2"}, "key3": "value3"}
    """
    if path is None:
        path = []
    for key in src:
        if key in dst:
            if isinstance(dst[key], dict) and isinstance(src[key], dict):
                merge(dst[key], src[key], path + [str(key)])
            else:
                dst[key] = src[key]
        else:
            dst[key] = src[key]
    return dst


def create_files(path: Union[str, Path], *contents: dict[str, Any]) -> None:
    """
    Create files and directories at the specified path based on the provided content.

    This function allows you to create files and directories at a specified path.
    The function accepts a variable number of content dictionaries, where each
    dictionary represents a file or directory to be created. The keys in the dictionary
    represent the filenames or directory names, and the values represent the content
    of the files or subdirectories.

    Args:
        path (str): The path where the files and directories should be created.
        *contents (dict): Variable number of dictionaries representing files and directories.
            For files, the dictionary should have a single key-value pair where the key is
            the filename and the value is the content of the file. For directories, the
            dictionary should have a single key with a value of None.
            To create a multi-document yaml file, the content value should be a tuple.
            Each value of the tuple will be a separate document in the resulting yaml file.

    Returns:
        None

    Example:
        create_files(
            "/my_folder",
            {"file1.txt": "Hello, World!"},
            {"subfolder": None},
            {"config.yaml": {"key": "value"}},
            {"catalog.yaml": ({"foo": "bar"}, {"baz": "qux"})}
        )

    In this example, the function will create a file "file1.txt" with content "Hello, World!"
    in the "/my_folder" directory, create an empty subdirectory "subfolder", create
    a file "config.yaml" with the specified YAML content and create a multi-document YAML
    file "catalog.yaml" with two documents.
    """
    root = Path(path)
    for element in contents:
        for file_name, content in element.items():
            full_path = root / file_name
            if content is None:
                full_path.mkdir(parents=True, exist_ok=True)
            else:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, str):
                    full_path.write_text(content)
                elif isinstance(content, bytes):
                    full_path.write_bytes(content)
                elif isinstance(content, tuple):
                    full_path.write_text(yaml.safe_dump_all(content))
                else:
                    full_path.write_text(yaml.safe_dump(content))


def catalog_files(
    catalog_name: str,
    operator: str,
    other_files: Optional[dict[str, Any]] = None,
    content: Optional[tuple[Any, ...]] = None,
) -> dict[str, Any]:
    """
    Create a catalog file as a multi-document yaml file.

    Args:
        catalog_name (str): The name of the catalog.
        operator (str): The name of the operator.
        other_files (dict, optional): Additional files to be created.
            Defaults to None.
        content (tuple, optional): The content of the catalog.yaml file.
            Needs to be a tuple, as the create_files() expects a tuple
            to create multi-document yaml file. Defaults to example catalog
            content.

    Returns:
        dict: A dictionary representing the catalog files, merged with other files.
    """
    default_content = (
        {"defaultChannel": "stable", "name": operator, "schema": "olm.package"},
        {"name": "alpha", "package": operator, "schema": "olm.channel"},
        {
            "name": f"{operator}.v1.0.0",
            "package": operator,
            "image": f"quay.io/org/{operator}@sha256:123",
            "schema": "olm.bundle",
        },
    )
    operator_path = f"catalogs/{catalog_name}/{operator}"
    catalog_content = content or default_content
    return merge(
        {
            f"{operator_path}/catalog.yaml": catalog_content,
        },
        other_files or {},
    )


def bundle_files(
    operator_name: str,
    bundle_version: str,
    annotations: Optional[dict[str, Any]] = None,
    csv: Optional[dict[str, Any]] = None,
    other_files: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Create a bundle of files and metadata for an Operator package.

    This function generates a bundle of files and metadata for an Operator package,
    including annotations, a CSV (ClusterServiceVersion) file, and other additional files.

    Args:
        operator_name (str): The name of the Operator.
        bundle_version (str): The version of the Operator bundle.
        annotations (dict, optional): Additional annotations for the bundle annotations.yaml file.
            Defaults to None.
        csv (dict, optional): Additional content to merge with the base CSV (ClusterServiceVersion)
            file. Defaults to None.
        other_files (dict, optional): Additional files to be included in the bundle.
            Defaults to None.

    Returns:
        dict: A dictionary representing the bundle, including annotations.yaml and CSV files,
        and other additional files.

    Example:
        bundle = bundle_files(
            operator_name="my-operator",
            bundle_version="1.0.0",
            annotations={"custom.annotation": "value"},
            csv={"spec": {"installModes": ["AllNamespaces"]}},
            other_files={"README.md": "# My Operator Documentation"}
        )

    In this example, the function will create a dictionary representing a bundle for the Operator
    "my-operator" with version "1.0.0". The annotations.yaml file will contain the provided custom
    annotation, the CSV file will have additional installation modes, and the README.md file will
    be included as an additional file in the bundle.
    """
    bundle_path = f"operators/{operator_name}/{bundle_version}"
    base_annotations = {
        "operators.operatorframework.io.bundle.mediatype.v1": "registry+v1",
        "operators.operatorframework.io.bundle.manifests.v1": "manifests/",
        "operators.operatorframework.io.bundle.metadata.v1": "metadata/",
        "operators.operatorframework.io.bundle.package.v1": operator_name,
        "operators.operatorframework.io.bundle.channel.default.v1": "beta",
        "operators.operatorframework.io.bundle.channels.v1": "beta",
    }
    base_csv = {
        "metadata": {
            "name": f"{operator_name}.v{bundle_version}",
            "spec": {"version": bundle_version},
        }
    }
    return merge(
        {
            f"{bundle_path}/metadata/annotations.yaml": {
                "annotations": merge(base_annotations, annotations or {})
            },
            f"{bundle_path}/manifests/{operator_name}.clusterserviceversion.yaml": merge(
                base_csv, csv or {}
            ),
        },
        other_files or {},
    )


def make_nested_dict(items: dict[str, Any]) -> dict[str, Any]:
    """
    _make_nested_dict({"foo.bar": "baz"}) -> {"foo": {"bar": "baz"}}
    """
    result: dict[str, Any] = {}
    for path, value in items.items():
        current = result
        keys = path.split(".")
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    return result
