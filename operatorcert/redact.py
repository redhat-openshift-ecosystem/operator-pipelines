"""
Module for redacting leaked information from output.
Uses LeakTK: https://github.com/leaktk/leaktk

Parses LeakTK output, concatenates its results so no overlaps exist
and then redacts.
"""

import logging
import tempfile
from pathlib import Path
from subprocess import Popen, PIPE
import json

from pydantic import BaseModel

LOGGER = logging.getLogger("operator-cert")


class RedactLocation(BaseModel):
    """
    Class for tracking information about a chunk of data in files.
    """

    path: Path


class ResultModel(BaseModel):
    """
    Model for parsing a single result from scanning.
    """

    location: RedactLocation


class ResultSetModel(BaseModel):
    """
    Model for parsing all results from scanning.
    """

    results: list[ResultModel]


def scan(*input_paths: Path) -> list[ResultSetModel]:
    """
    Scan all input paths and return a list of the results.
    Returns:
        Parsed scan results.
    """
    results = []
    for input_path in input_paths:
        with Popen(
            ["leaktk", "scan", "--kind", "Files", str(input_path.absolute())],
            stdout=PIPE,
        ) as scan_proc:
            result_bytes = scan_proc.stdout.read()  # type: ignore[union-attr]
        loaded_dict = json.loads(result_bytes)
        results.append(ResultSetModel.model_validate(loaded_dict))
    return results


def _redact(
    *input_paths: Path,
) -> dict[Path, Path]:
    """
    Redact the paths yielded by scanning. Creates a new
    temporary file with the redacted contents.
    Args:
        *input_paths: The paths containing leaks.

    Returns:
        The input paths mapped to their redacted versions.
        Both set to absolute paths.
    """
    file_mapping = {}
    for input_path in input_paths:
        tmp_file = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            delete=False
        )
        with open(input_path, "rb") as input_file:
            with Popen(
                ["leaktk", "redact", "--kind", "Stdio"],
                stdin=input_file,
                stdout=tmp_file.file,
                stderr=PIPE,
            ) as redact_proc:
                redact_proc.wait()
                if redact_proc.returncode != 0:
                    raise RuntimeError(
                        f"Redact failed with return code: "
                        f"{redact_proc.returncode}. STDERR: "
                        f"{redact_proc.stderr.read().decode('utf-8')}"  # type: ignore[union-attr]
                    )
                file_mapping[input_path.absolute()] = Path(tmp_file.name).absolute()
        tmp_file.close()
    return file_mapping


def redact_results(*result_sets: ResultSetModel) -> dict[Path, Path]:
    """
    Redact all the paths contained in all the results yielded by scanning.
    Creates a new temporary file with the redacted contents.
    Args:
        *result_sets: The parsed results from scanning.

    Returns:
        The redacted paths mapped to their redacted versions.
        Both set to absolute paths.
    """
    file_locations = set()
    for result_set in result_sets:
        for result in result_set.results:
            # pathlib does not consider relative & absolute paths the same
            # even if they point to the same location
            file_locations.add(Path(result.location.path).absolute())
    if file_locations:
        LOGGER.critical("Found leaks in these files: %s", file_locations)
    return _redact(*file_locations)


def scan_and_redact(*input_paths: Path) -> dict[Path, Path]:
    """
    Checks which files have leaked information and redacts them.
    Creates a new temporary file with the redacted contents.
    Args:
        *input_paths: Any path (directory or file) to scan.
    Returns:
        The redacted paths mapped to their redacted versions.
        Both set to absolute paths.
    """
    scan_results = scan(*input_paths)
    return redact_results(*scan_results)
