import logging
import pathlib
from typing import List, Optional, Tuple, Dict


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
            result_file.write(result_value)
