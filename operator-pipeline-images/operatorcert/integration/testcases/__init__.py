"""
Import all submodules, so that all testcases are available.
"""

import importlib
import pkgutil
from types import ModuleType


def import_submodules(
    package: str | ModuleType, recursive: bool = True
) -> dict[str, ModuleType]:
    """Import all submodules of a module, recursively, including subpackages.

    This function dynamically imports all submodules found within a given package,
    optionally including subpackages if recursive mode is enabled. It's useful for
    automatically loading all modules in a package without explicitly importing each one.

    Args:
        package (str | ModuleType): The package to import submodules from. Can be either:
            - A string representing the module name (e.g., 'mypackage.subpackage')
            - A ModuleType object representing an already imported module
        recursive (bool, optional): Whether to recursively import submodules of
            subpackages. Defaults to True. If False, only direct submodules of the
            given package are imported.

    Returns:
        dict[str, ModuleType]: A dictionary mapping module names to their corresponding
            imported module objects. Keys are fully qualified module names (strings)
            and values are the imported ModuleType objects. If a module fails to import
            due to ModuleNotFoundError, it is silently skipped and not included in the
            returned dictionary.
    """
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + "." + name
        try:
            results[full_name] = importlib.import_module(full_name)
        except ModuleNotFoundError:
            continue
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results


def import_testcases() -> None:
    """Import all testcases in this module"""
    import_submodules(__name__)
