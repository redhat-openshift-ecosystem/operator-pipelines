import json
import os
import tempfile
from base64 import b64encode
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from operatorcert.redact import (
    scan_and_redact,
    scan,
)

JWT_TOKEN_ENCODED = b64encode(json.dumps({"hello": "world"}).encode("utf-8"))
JWT_TOKEN = b".".join([JWT_TOKEN_ENCODED] * 3)
INPUT_CONTENT = b"curl -H 'Authorization: bearer " + JWT_TOKEN + b" example.com\n"
REDACTED_CONTENT = b"curl -H 'Authorization: bearer ***[REDACTED]*** example.com\n"


def _scan_result_str(path: str) -> str:
    return json.dumps({"results": [{"location": {"path": path}}]})


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

    mock_check_output.return_value = scan_result

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
    )


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
