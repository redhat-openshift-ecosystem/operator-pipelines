import pathlib
from typing import List, Optional, Tuple


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


def str_color(color, data):
    # source: https://stackoverflow.com/a/31991678
    colors = {
        "pink": "\033[95m",
        "blue": "\033[94m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "ENDC": "\033[0m",
        "bold": "\033[1m",
        "underline": "\033[4m",
    }
    return colors[color] + str(data) + colors["ENDC"]
