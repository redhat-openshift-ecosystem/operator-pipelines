import json
import os
import tempfile
from base64 import b64encode
from pathlib import Path
from subprocess import PIPE
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


def _scan_result_bytes(path: str) -> bytes:
    return json.dumps({"results": [{"location": {"path": path}}]}).encode()


def _make_popen_side_effect(
    scan_result: bytes,
    redact_returncode: int = 0,
) -> Any:
    def popen_side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
        proc = MagicMock()
        proc.__enter__ = MagicMock(return_value=proc)
        proc.__exit__ = MagicMock(return_value=False)
        proc.returncode = redact_returncode
        if "scan" in cmd:
            proc.stdout.read.return_value = scan_result
        elif "redact" in cmd:
            stdout = kwargs.get("stdout")
            if stdout:
                stdout.write(REDACTED_CONTENT)
                stdout.flush()
        return proc

    return popen_side_effect


@patch("operatorcert.redact.Popen")
def test_scan(mock_popen: MagicMock) -> None:
    """Mock leaktk scan call result, check that the expected result is parsed."""
    input_path = Path("/fake/path/testfile")
    scan_result = _scan_result_bytes(str(input_path))

    proc = MagicMock()
    proc.stdout.read.return_value = scan_result
    mock_popen.return_value.__enter__.return_value = proc

    results = scan(input_path)

    assert len(results) == 1
    assert len(results[0].results) == 1
    assert results[0].results[0].location.path == input_path

    mock_popen.assert_called_once_with(
        ["leaktk", "scan", "--kind", "Files", str(input_path.absolute())],
        stdout=PIPE,
    )


@patch("operatorcert.redact.Popen")
def test_scan_and_redact(mock_popen: MagicMock) -> None:
    """Full scan and redaction workflow."""
    input_file = tempfile.NamedTemporaryFile("wb", delete=False)
    input_file_path = Path(input_file.name)
    input_file.write(INPUT_CONTENT)
    input_file.close()

    scan_result = _scan_result_bytes(str(input_file_path))
    mock_popen.side_effect = _make_popen_side_effect(scan_result)

    result = scan_and_redact(input_file_path)

    assert len(result) == 1
    assert input_file_path in result
    redacted_path = result[input_file_path]
    with open(redacted_path, "rb") as redacted_file:
        assert redacted_file.read() == REDACTED_CONTENT
    os.unlink(input_file_path)
    os.unlink(redacted_path)


@patch("operatorcert.redact.Popen")
def test_scan_and_redact_fail(mock_popen: MagicMock) -> None:
    """Redaction raises RuntimeError on non-zero return code."""
    input_file = tempfile.NamedTemporaryFile("wb", delete=False)
    input_file_path = Path(input_file.name)
    input_file.write(INPUT_CONTENT)
    input_file.close()

    scan_result = _scan_result_bytes(str(input_file_path))
    mock_popen.side_effect = _make_popen_side_effect(scan_result, redact_returncode=1)

    with pytest.raises(RuntimeError):
        scan_and_redact(input_file_path)
