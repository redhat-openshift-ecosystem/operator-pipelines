import json
import os
import subprocess
import tempfile
from base64 import b64encode
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from operatorcert.redact import (
    paths_with_leaks,
    scan_and_redact,
    scan,
)

JWT_TOKEN_ENCODED = b64encode(json.dumps({"hello": "world"}).encode("utf-8"))
JWT_TOKEN = b".".join([JWT_TOKEN_ENCODED] * 3)
INPUT_CONTENT = b"curl -H 'Authorization: bearer " + JWT_TOKEN + b" example.com\n"
REDACTED_CONTENT = b"curl -H 'Authorization: bearer ***[REDACTED]*** example.com\n"


def _scan_result_str(path: str, **extra: Any) -> str:
    result: dict[str, Any] = {"location": {"path": path}}
    result.update(extra)
    return json.dumps({"results": [result]})


def _make_run_side_effect(
    redact_returncode: int = 0,
) -> Any:
    def run_side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
        proc = MagicMock()
        proc.returncode = redact_returncode
        if "redact" in cmd:
            stdout = kwargs.get("stdout")
            if stdout:
                stdout.write(REDACTED_CONTENT)
                stdout.flush()
        return proc

    return run_side_effect


@patch("operatorcert.redact.subprocess.check_output")
def test_scan(mock_check_output: MagicMock) -> None:
    """Mock leaktk scan call result, check that the expected result is parsed."""
    input_path = Path("/fake/path/testfile")
    scan_result = _scan_result_str(str(input_path))

    # Blank lines in JSONL output are skipped (leaktk may emit them).
    mock_check_output.return_value = f"\n{scan_result}\n\n"

    results = scan(input_path)

    assert len(results) == 1
    assert len(results[0].results) == 1
    assert results[0].results[0].location.path == input_path

    expected_input = (
        json.dumps(
            {
                "id": "0",
                "kind": "Files",
                "resource": str(input_path.absolute()),
            }
        )
        + "\n"
    )
    mock_check_output.assert_called_once_with(
        ["leaktk", "listen"],
        input=expected_input,
        text=True,
        stderr=subprocess.DEVNULL,
    )


@patch("operatorcert.redact.subprocess.check_output")
def test_scan_ignores_secret_fields(mock_check_output: MagicMock) -> None:
    """Extra LeakTK fields (e.g. secret/match) must not be retained on models."""
    input_path = Path("/fake/path/leaky-file")
    secret = "SUPERSECRET_TOKEN_VALUE"
    mock_check_output.return_value = _scan_result_str(
        str(input_path), secret=secret, match=secret
    )

    results = scan(input_path)

    assert results[0].results[0].location.path == input_path
    dumped = results[0].model_dump_json()
    assert secret not in dumped


@patch("operatorcert.redact.subprocess.check_output")
def test_scan_called_process_error_is_sanitized(mock_check_output: MagicMock) -> None:
    """Non-zero LeakTK exit must not propagate stdout that may contain secrets."""
    secret = "SUPERSECRET_TOKEN_VALUE"
    mock_check_output.side_effect = subprocess.CalledProcessError(
        1,
        ["leaktk", "listen"],
        output=json.dumps({"secret": secret}),
    )

    with pytest.raises(RuntimeError, match="LeakTK scan failed") as exc_info:
        scan(Path("/fake/path/file"))

    assert secret not in str(exc_info.value)
    assert secret not in repr(exc_info.value)


@patch("operatorcert.redact.subprocess.check_output")
def test_scan_invalid_json_is_sanitized(mock_check_output: MagicMock) -> None:
    """Unparseable LeakTK lines raise a generic error without raw payload."""
    secret = "SUPERSECRET_TOKEN_VALUE"
    mock_check_output.return_value = f'{{"results": "not-a-list-{secret}"}}'

    with pytest.raises(RuntimeError, match="could not be parsed safely") as exc_info:
        scan(Path("/fake/path/file"))

    assert secret not in str(exc_info.value)


@patch("operatorcert.redact.subprocess.check_output")
def test_paths_with_leaks(mock_check_output: MagicMock) -> None:
    """paths_with_leaks returns absolute paths reported by the scan."""
    input_path = Path("/fake/path/leaky-file")
    mock_check_output.return_value = _scan_result_str(str(input_path))

    assert paths_with_leaks() == set()

    result = paths_with_leaks(input_path)
    assert result == {input_path.absolute()}


@patch("operatorcert.redact.subprocess.run")
@patch("operatorcert.redact.subprocess.check_output")
def test_scan_and_redact(mock_check_output: MagicMock, mock_run: MagicMock) -> None:
    """Full scan and redaction workflow."""
    input_file = tempfile.NamedTemporaryFile("wb", delete=False)
    input_file_path = Path(input_file.name)
    input_file.write(INPUT_CONTENT)
    input_file.close()

    mock_check_output.return_value = _scan_result_str(str(input_file_path))
    mock_run.side_effect = _make_run_side_effect()

    result = scan_and_redact(input_file_path)

    assert len(result) == 1
    assert input_file_path.absolute() in result
    redacted_path = result[input_file_path.absolute()]
    with open(redacted_path, "rb") as redacted_file:
        assert redacted_file.read() == REDACTED_CONTENT
    os.unlink(input_file_path)
    os.unlink(redacted_path)


@patch("operatorcert.redact.subprocess.run")
@patch("operatorcert.redact.subprocess.check_output")
def test_scan_and_redact_fail(
    mock_check_output: MagicMock, mock_run: MagicMock
) -> None:
    """Redaction raises RuntimeError on non-zero return code."""
    input_file = tempfile.NamedTemporaryFile("wb", delete=False)
    input_file_path = Path(input_file.name)
    input_file.write(INPUT_CONTENT)
    input_file.close()

    mock_check_output.return_value = _scan_result_str(str(input_file_path))
    mock_run.side_effect = _make_run_side_effect(redact_returncode=1)

    with pytest.raises(RuntimeError):
        scan_and_redact(input_file_path)
