"""Smoke tests for merge_base_lane_fingerprint CLI."""

import argparse
import json
import runpy

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from operatorcert.entrypoints import merge_base_lane_fingerprint


def test_main_record_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "merge-base-lane-fingerprint",
            "record",
            "--git-dir",
            str(tmp_path),
            "--tree-ish",
            "deadbeef",
            "--operator-path",
            "",
            "--added-or-modified-catalog-operators",
            "",
            "--output",
            str(out),
        ],
    )
    merge_base_lane_fingerprint.main()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["enabled"] is False


def test_main_unknown_command_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = merge_base_lane_fingerprint._parser()
    fake_args = argparse.Namespace(command="not-a-command", verbose=False)
    monkeypatch.setattr(parser, "parse_args", lambda: fake_args)
    monkeypatch.setattr(merge_base_lane_fingerprint, "_parser", lambda: parser)
    with pytest.raises(SystemExit) as exc:
        merge_base_lane_fingerprint.main()
    assert exc.value.code == 2


@patch.object(
    merge_base_lane_fingerprint, "record_snapshot", side_effect=ValueError("bad")
)
def test_main_record_error_exits_one(
    _mock_record: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "merge-base-lane-fingerprint",
            "record",
            "--git-dir",
            "/tmp",
            "--tree-ish",
            "abc",
            "--operator-path",
            "",
            "--added-or-modified-catalog-operators",
            "",
            "--output",
            "/tmp/out.json",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        merge_base_lane_fingerprint.main()
    assert exc.value.code == 1


@pytest.mark.filterwarnings("ignore:.*sys\\.modules.*:RuntimeWarning")
def test_run_module_as_main_record_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "merge-base-lane-fingerprint",
            "record",
            "--git-dir",
            str(tmp_path),
            "--tree-ish",
            "deadbeef",
            "--operator-path",
            "",
            "--added-or-modified-catalog-operators",
            "",
            "--output",
            str(out),
        ],
    )
    runpy.run_module(
        "operatorcert.entrypoints.merge_base_lane_fingerprint", run_name="__main__"
    )
    assert json.loads(out.read_text(encoding="utf-8"))["enabled"] is False


@patch.object(merge_base_lane_fingerprint, "verify_snapshot", return_value=10)
def test_main_verify_exit_code(
    _mock_verify: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    snap = Path("/tmp/snap-will-not-be-read")
    monkeypatch.setattr(
        "sys.argv",
        [
            "merge-base-lane-fingerprint",
            "verify",
            "--git-dir",
            "/tmp",
            "--git-repo-url",
            "https://example.com/r.git",
            "--git-base-branch",
            "main",
            "--snapshot-file",
            str(snap),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        merge_base_lane_fingerprint.main()
    assert exc.value.code == 10
