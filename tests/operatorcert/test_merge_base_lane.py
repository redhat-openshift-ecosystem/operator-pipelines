"""Tests for merge_base_lane path building and fingerprinting."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from operatorcert.merge_base_lane import (
    build_lane_paths,
    catalog_operator_segment_to_repo_path,
    fingerprint_lane,
    git_fetch_branch_tip,
    git_ls_remote_tip,
    git_ls_tree_lines,
    record_snapshot,
    split_csv,
    verify_snapshot,
)


def test_split_csv() -> None:
    assert split_csv("") == []
    assert split_csv("  ") == []
    assert split_csv("a,b") == ["a", "b"]
    assert split_csv(" a , b ") == ["a", "b"]


@pytest.mark.parametrize(
    "operator_path,catalog_ops_csv,expected",
    [
        ("operators/foo", "", ["operators/foo"]),
        (
            "operators/foo",
            "v4.14/bar",
            ["catalogs/v4.14/bar", "operators/foo"],
        ),
        (
            "",
            "v4.15/x,v4.16/y",
            ["catalogs/v4.15/x", "catalogs/v4.16/y"],
        ),
        (
            "operators/foo",
            "catalogs/v4.14/foo",
            ["catalogs/v4.14/foo", "operators/foo"],
        ),
    ],
)
def test_build_lane_paths(
    operator_path: str, catalog_ops_csv: str, expected: list[str]
) -> None:
    assert build_lane_paths(operator_path, catalog_ops_csv) == expected


def test_catalog_operator_segment_to_repo_path() -> None:
    assert catalog_operator_segment_to_repo_path("v4.14/isovalent-networking") == (
        "catalogs/v4.14/isovalent-networking"
    )
    assert catalog_operator_segment_to_repo_path("  catalogs/v4.14/foo  ") == (
        "catalogs/v4.14/foo"
    )


def test_catalog_operator_segment_invalid_slash_count() -> None:
    with pytest.raises(ValueError, match="Expected catalog operator path"):
        catalog_operator_segment_to_repo_path("onlyonepart")


@pytest.mark.parametrize(
    "segment,match",
    [
        ("", "Empty catalog operator segment"),
        ("   ", "Empty catalog operator segment"),
        ("/v4.14/foo", "relative"),
        ("v4.14/../evil", r"\.\."),
        ("../v4.14/foo", r"\.\."),
    ],
)
def test_catalog_operator_segment_rejected(segment: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        catalog_operator_segment_to_repo_path(segment)


def test_build_lane_paths_rejects_parent_dir() -> None:
    with pytest.raises(ValueError, match=r"\.\."):
        build_lane_paths("operators/../etc", "")


def test_build_lane_paths_rejects_absolute() -> None:
    with pytest.raises(ValueError, match="relative"):
        build_lane_paths("/operators/foo", "")


def test_fingerprint_lane_deterministic(tmp_path: Path) -> None:
    git_dir = tmp_path / "repo"
    git_dir.mkdir()
    subprocess.run(["git", "init"], cwd=git_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@e.st"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    d = git_dir / "operators" / "o1"
    d.mkdir(parents=True)
    (d / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=git_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "m"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=git_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    fp1 = fingerprint_lane(git_dir, head, ["operators/o1"])
    fp2 = fingerprint_lane(git_dir, head, ["operators/o1"])
    assert fp1 == fp2
    assert len(fp1) == 64


def test_git_ls_tree_lines_empty_paths(tmp_path: Path) -> None:
    assert git_ls_tree_lines(tmp_path, "HEAD", []) == []


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_ls_tree_lines_git_fails(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=128, stderr="fatal", stdout="")
    with pytest.raises(RuntimeError, match="git ls-tree"):
        git_ls_tree_lines(tmp_path, "nope", ["x"])


def test_git_ls_tree_lines_happy_path_filters_and_sorts(tmp_path: Path) -> None:
    git_dir = tmp_path / "repo"
    git_dir.mkdir()
    subprocess.run(["git", "init"], cwd=git_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@e.st"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    lane_dir = git_dir / "operators" / "o1"
    lane_dir.mkdir(parents=True)
    (lane_dir / "z.txt").write_text("z", encoding="utf-8")
    (lane_dir / "a.txt").write_text("a", encoding="utf-8")
    # file outside selected lane path; should be excluded by path filtering
    (git_dir / "operators" / "o2").mkdir(parents=True)
    (git_dir / "operators" / "o2" / "x.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=git_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "m"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=git_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    lines = git_ls_tree_lines(git_dir, head, ["operators/o1"])
    assert lines == sorted(lines)
    assert lines
    assert len(lines) == 2
    assert lines[0].endswith("\toperators/o1/a.txt")
    assert lines[1].endswith("\toperators/o1/z.txt")


def test_record_snapshot_disabled_no_paths(tmp_path: Path) -> None:
    out = tmp_path / "snap.json"
    record_snapshot(tmp_path, "abc", "", "", out)
    data = out.read_text(encoding="utf-8")
    assert '"enabled": false' in data


def test_record_snapshot_enabled(tmp_path: Path) -> None:
    git_dir = tmp_path / "repo"
    git_dir.mkdir()
    subprocess.run(["git", "init"], cwd=git_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@e.st"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    d = git_dir / "operators" / "o1"
    d.mkdir(parents=True)
    (d / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=git_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "m"],
        cwd=git_dir,
        check=True,
        capture_output=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=git_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    out = tmp_path / "snap.json"
    record_snapshot(
        git_dir,
        head,
        "operators/o1",
        "",
        out,
    )
    data = out.read_text(encoding="utf-8")
    assert '"enabled": true' in data
    assert head in data


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_ls_remote_tip_does_not_pass_env_so_credentials_inherit(
    mock_run: MagicMock,
) -> None:
    """Tekton merge-pr copies ssh-directory into HOME; subprocess must not replace os.environ."""
    oid = "a" * 40
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=f"{oid}\trefs/heads/main\n",
        stderr="",
    )
    assert git_ls_remote_tip("git@example.com:org/r.git", "main") == oid
    cmd, kwargs = mock_run.call_args[0][0], mock_run.call_args[1]
    assert kwargs.get("env") is None
    assert "-c" in cmd
    c_idx = cmd.index("-c")
    assert "core.sshCommand=" in cmd[c_idx + 1]
    assert "StrictHostKeyChecking=accept-new" in cmd[c_idx + 1]


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_ls_remote_tip_success(mock_run: MagicMock) -> None:
    oid = "a" * 40
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=f"{oid}\trefs/heads/main\n",
        stderr="",
    )
    url = "https://example.com/r.git"
    assert git_ls_remote_tip(url, "main") == oid
    cmd = mock_run.call_args[0][0]
    assert cmd == ["git", "ls-remote", url, "refs/heads/main"]


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_ls_remote_tip_fails(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="no route")
    with pytest.raises(RuntimeError, match="git ls-remote failed"):
        git_ls_remote_tip("https://example.invalid/x.git", "main")


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_ls_remote_tip_no_matching_ref(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="deadbeef\trefs/heads/other\n",
        stderr="",
    )
    with pytest.raises(RuntimeError, match="Could not resolve refs/heads/main"):
        git_ls_remote_tip("https://example.invalid/x.git", "main")


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_fetch_branch_tip_success(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
    git_fetch_branch_tip(
        tmp_path, "up", "https://example.com/r.git", "main", "refs/local/tip"
    )
    assert mock_run.call_count == 4
    commands = [call.args[0] for call in mock_run.call_args_list]
    assert commands[0][:5] == ["git", "-C", str(tmp_path), "rev-parse", "--git-dir"]
    assert all(cmd[:2] != ["git", "init"] for cmd in commands)


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_fetch_branch_tip_initializes_repo_when_missing(
    mock_run: MagicMock, tmp_path: Path
) -> None:
    def _side_effect(cmd: list[str], **_k: object) -> MagicMock:
        if cmd[:5] == ["git", "-C", str(tmp_path), "rev-parse", "--git-dir"]:
            return MagicMock(returncode=1, stderr="not a git repository", stdout="")
        return MagicMock(returncode=0, stderr="", stdout="")

    mock_run.side_effect = _side_effect
    git_fetch_branch_tip(
        tmp_path, "up", "https://example.com/r.git", "main", "refs/local/tip"
    )
    commands = [call.args[0] for call in mock_run.call_args_list]
    assert ["git", "init", str(tmp_path)] in commands


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_fetch_branch_tip_init_fails(mock_run: MagicMock, tmp_path: Path) -> None:
    def _side_effect(cmd: list[str], **_k: object) -> MagicMock:
        if cmd[:5] == ["git", "-C", str(tmp_path), "rev-parse", "--git-dir"]:
            return MagicMock(returncode=1, stderr="not a git repository", stdout="")
        if cmd[:2] == ["git", "init"]:
            return MagicMock(returncode=1, stderr="init failed", stdout="")
        return MagicMock(returncode=0, stderr="", stdout="")

    mock_run.side_effect = _side_effect
    with pytest.raises(RuntimeError, match="git init failed"):
        git_fetch_branch_tip(
            tmp_path, "up", "https://example.com/r.git", "main", "refs/local/tip"
        )


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_fetch_branch_tip_remote_add_fails(
    mock_run: MagicMock, tmp_path: Path
) -> None:
    def _fail_add(cmd: list[str], **_k: object) -> MagicMock:
        if "remote" in cmd and "add" in cmd:
            return MagicMock(returncode=1, stderr="exists", stdout="")
        return MagicMock(returncode=0, stderr="", stdout="")

    mock_run.side_effect = _fail_add
    with pytest.raises(RuntimeError, match="git remote add failed"):
        git_fetch_branch_tip(
            tmp_path, "up", "https://example.com/r.git", "main", "refs/local/tip"
        )


@patch("operatorcert.merge_base_lane.subprocess.run")
def test_git_fetch_branch_tip_fetch_fails(mock_run: MagicMock, tmp_path: Path) -> None:
    def _side_effect(cmd: list[str], **_k: object) -> MagicMock:
        if "fetch" in cmd:
            return MagicMock(returncode=1, stderr="fetch failed", stdout="")
        return MagicMock(returncode=0, stderr="", stdout="")

    mock_run.side_effect = _side_effect
    with pytest.raises(RuntimeError, match="git fetch failed"):
        git_fetch_branch_tip(
            tmp_path, "up", "https://example.com/r.git", "main", "refs/local/tip"
        )


def test_verify_snapshot_load_error_returns_one(tmp_path: Path) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text("{not json", encoding="utf-8")
    rc = verify_snapshot(tmp_path, "https://example.invalid/repo.git", "main", snap)
    assert rc == 1


def test_verify_snapshot_disabled_returns_zero(tmp_path: Path) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text('{"enabled": false}', encoding="utf-8")
    rc = verify_snapshot(tmp_path, "https://example.invalid/repo.git", "main", snap)
    assert rc == 0


def test_verify_snapshot_paths_not_strings_raises(tmp_path: Path) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text(
        '{"enabled": true, "base_oid": "a", "lane_fp": "f", "paths": [1, 2]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="paths must be a list of strings"):
        verify_snapshot(tmp_path, "https://example.invalid/repo.git", "main", snap)


@patch("operatorcert.merge_base_lane.git_fetch_branch_tip")
@patch("operatorcert.merge_base_lane.git_ls_remote_tip")
@patch("operatorcert.merge_base_lane.fingerprint_lane")
def test_verify_snapshot_fingerprint_unchanged_after_tip_moves(
    mock_fp: MagicMock,
    mock_ls_remote: MagicMock,
    mock_fetch: MagicMock,
    tmp_path: Path,
) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text(
        '{"enabled": true, "base_oid": "aaa", "lane_fp": "samefp", "paths": ["p"]}',
        encoding="utf-8",
    )
    mock_ls_remote.return_value = "bbb"
    mock_fp.return_value = "samefp"
    rc = verify_snapshot(tmp_path, "https://example.invalid/repo.git", "main", snap)
    assert rc == 0
    mock_fetch.assert_called_once()
    mock_fp.assert_called_once()


@patch("operatorcert.merge_base_lane.git_fetch_branch_tip")
@patch("operatorcert.merge_base_lane.git_ls_remote_tip")
@patch("operatorcert.merge_base_lane.fingerprint_lane")
def test_verify_snapshot_fast_path_same_oid(
    mock_fp: MagicMock,
    mock_ls_remote: MagicMock,
    mock_fetch: MagicMock,
    tmp_path: Path,
) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text(
        '{"enabled": true, "base_oid": "abc123", "lane_fp": "dead", "paths": ["p"]}',
        encoding="utf-8",
    )
    mock_ls_remote.return_value = "abc123"
    rc = verify_snapshot(tmp_path, "https://example.invalid/repo.git", "main", snap)
    assert rc == 0
    mock_fetch.assert_not_called()
    mock_fp.assert_not_called()


def test_verify_invalid_snapshot_raises(tmp_path: Path) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text('{"enabled": true}', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid merge-base snapshot"):
        verify_snapshot(tmp_path, "https://example.invalid/repo.git", "main", snap)


@patch("operatorcert.merge_base_lane.git_fetch_branch_tip")
@patch("operatorcert.merge_base_lane.git_ls_remote_tip")
@patch("operatorcert.merge_base_lane.fingerprint_lane")
def test_verify_snapshot_mismatch_returns_10(
    mock_fp: MagicMock,
    mock_ls_remote: MagicMock,
    mock_fetch: MagicMock,
    tmp_path: Path,
) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text(
        '{"enabled": true, "base_oid": "aaa", "lane_fp": "expect", "paths": ["p"]}',
        encoding="utf-8",
    )
    mock_ls_remote.return_value = "bbb"
    mock_fp.return_value = "different"
    rc = verify_snapshot(tmp_path, "https://example.invalid/repo.git", "main", snap)
    assert rc == 10
    mock_fetch.assert_called_once()
