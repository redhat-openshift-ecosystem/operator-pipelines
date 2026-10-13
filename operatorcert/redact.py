"""
Module for redacting leaked information from output.
Uses LeakTK: https://github.com/leaktk/leaktk

Parses LeakTK output, concatenates its results so no overlaps exist
and then redacts.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
import json

from pydantic import BaseModel, ConfigDict

LOGGER = logging.getLogger("operator-cert")

# Cap logged LeakTK stderr so a noisy failure cannot flood pipeline logs.
_MAX_LOGGED_STDERR_CHARS = 2048


def _safe_stderr_for_log(stderr: str | None) -> str:
    """
    Prepare LeakTK stderr for logging without leaking secret match text.

    Prefer running the text through ``leaktk redact``; if that fails, truncate
    the raw stderr instead. Never use this for stdout (match payloads).
    """
    if not stderr:
        return ""
    text = stderr
    try:
        redact_proc = subprocess.run(
            ["leaktk", "redact", "--kind", "Stdio"],
            input=stderr,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if redact_proc.returncode == 0 and redact_proc.stdout is not None:
            text = redact_proc.stdout
    except OSError:
        # Binary missing or similar; fall back to truncated raw stderr.
        pass
    text = text.strip()
    if len(text) > _MAX_LOGGED_STDERR_CHARS:
        return f"{text[:_MAX_LOGGED_STDERR_CHARS]}...(truncated)"
    return text


class RedactLocation(BaseModel):
    """
    Class for tracking information about a chunk of data in files.
    """

    model_config = ConfigDict(extra="ignore")

    path: Path


class ResultModel(BaseModel):
    """
    Model for parsing a single result from scanning.
    """

    model_config = ConfigDict(extra="ignore")

    location: RedactLocation


class ResultSetModel(BaseModel):
    """
    Model for parsing all results from scanning.
    """

    model_config = ConfigDict(extra="ignore")

    results: list[ResultModel]


def scan(*input_paths: Path) -> list[ResultSetModel]:
    """
    Scan all input paths and return a list of the results.
    Returns:
        Parsed scan results.
    """
    requests = "".join(
        json.dumps(
            {"id": str(i), "kind": "Files", "resource": str(input_path.absolute())}
        )
        + "\n"
        for i, input_path in enumerate(input_paths)
    )
    try:
        results_jsonl = subprocess.check_output(
            ["leaktk", "listen"],
            input=requests,
            text=True,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        # LeakTK stdout may contain secret match text; never log or raise it.
        # Stderr is diagnostic; redact (or truncate) before logging.
        safe_stderr = _safe_stderr_for_log(exc.stderr)
        if safe_stderr:
            LOGGER.error(
                "LeakTK scan failed (exit %s): %s",
                exc.returncode,
                safe_stderr,
            )
        else:
            LOGGER.error(
                "LeakTK scan failed (exit %s) with empty stderr",
                exc.returncode,
            )
        raise RuntimeError(
            f"LeakTK scan failed with exit code {exc.returncode}"
        ) from None

    parsed: list[ResultSetModel] = []
    for line in results_jsonl.splitlines():
        if not line.strip():
            continue
        try:
            parsed.append(ResultSetModel.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValueError):
            raise RuntimeError(
                "LeakTK returned output that could not be parsed safely"
            ) from None
    return parsed


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
            redact_proc = subprocess.run(
                ["leaktk", "redact", "--kind", "Stdio"],
                stdin=input_file,
                stdout=tmp_file.file,
                stderr=subprocess.PIPE,
                check=False,
            )
            if redact_proc.returncode != 0:
                raise RuntimeError(
                    f"Redact failed with return code: "
                    f"{redact_proc.returncode}. STDERR: "
                    f"{redact_proc.stderr.decode('utf-8')}"
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


def paths_with_leaks(*input_paths: Path) -> set[Path]:
    """
    Return absolute paths that LeakTK reported as containing leaks.

    Args:
        *input_paths: Any path (directory or file) to scan.

    Returns:
        Absolute paths of files with detected leaks.
    """
    if not input_paths:
        return set()
    leaky: set[Path] = set()
    for result_set in scan(*input_paths):
        for result in result_set.results:
            leaky.add(Path(result.location.path).absolute())
    return leaky


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
