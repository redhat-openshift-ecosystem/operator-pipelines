"""Build and fingerprint a stable view of operator/catalog paths on a git tree."""

import hashlib
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

LOGGER = logging.getLogger("operator-cert")

# Reject paths that escape the repository root when interpreted as POSIX paths.
_UNSAFE_PATH = re.compile(r"(^|/)\.\.(/|$)")


def _git_global_args_for_ssh_remote(remote_url: str) -> list[str]:
    """
    Build optional git config args for SSH remotes.

    Adds `git -c ...` options so SSH behavior matches Tekton git-init. This
    keeps host key checking compatible with setups where the ssh-directory
    secret has keys but no `known_hosts` file.

    Args:
        remote_url (str): Git remote URL.

    Returns:
        list[str]: Extra arguments for a git command, or an empty list for
            non-SSH remotes.
    """
    u = remote_url.strip()
    if u.startswith("git@") or u.startswith("ssh://"):
        return [
            "-c",
            "core.sshCommand=ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new",
        ]
    return []


def split_csv(value: str) -> list[str]:
    """
    Split a comma-separated value into normalized segments.

    Args:
        value (str): Comma-separated text.

    Returns:
        list[str]: Non-empty, whitespace-trimmed segments.
    """
    if not value or not value.strip():
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def catalog_operator_segment_to_repo_path(segment: str) -> str:
    """
    Map a detect-changes catalog segment to a repo-relative path.

    `detect-changed-operators` emits `version/operator` values (for example
    `v4.14/foo`) without a `catalogs/` prefix. Inputs already under
    `catalogs/...` are normalized and returned as-is.

    Args:
        segment (str): Catalog operator segment.

    Returns:
        str: Normalized path under `catalogs/`.

    Raises:
        ValueError: If the segment is empty, absolute, unsafe, or malformed.
    """
    s = segment.strip()
    if not s:
        raise ValueError("Empty catalog operator segment")
    if s.startswith("/"):
        raise ValueError(f"Lane path must be relative: {segment!r}")
    if _UNSAFE_PATH.search(s):
        raise ValueError(f"Lane path must not contain '..': {segment!r}")
    norm = s.strip("/")
    if norm.startswith("catalogs/"):
        return norm
    # OCP version directory + operator name (single slash)
    if norm.count("/") != 1:
        raise ValueError(
            "Expected catalog operator path as "
            "'<ocp_version>/<operator_name>' or 'catalogs/...', "
            f"got {segment!r}"
        )
    return f"catalogs/{norm}"


def build_lane_paths(
    operator_path: str, added_or_modified_catalog_operators: str
) -> list[str]:
    """
    Build sorted unique path prefixes for the merge guard lane.

    Combines `operator_path` (`operators/...`) and
    `added_or_modified_catalog_operators` from detect-changes
    (comma-separated `version/operator` or `catalogs/...`).

    Args:
        operator_path (str): Operator path reported by detect-changes.
        added_or_modified_catalog_operators (str): Comma-separated catalog
            operator segments from detect-changes.

    Returns:
        list[str]: Sorted, de-duplicated lane paths.

    Raises:
        ValueError: If any resolved path is unsafe.
    """
    paths: set[str] = set()

    def _add_operator_path(raw: str) -> None:
        op = raw.strip()
        if not op:
            return
        if op.startswith("/"):
            raise ValueError(f"Lane path must be relative: {raw!r}")
        norm = op.strip("/")
        if norm:
            paths.add(norm)

    _add_operator_path(operator_path or "")
    for seg in split_csv(added_or_modified_catalog_operators):
        paths.add(catalog_operator_segment_to_repo_path(seg))
    normalized = sorted(paths)
    out: list[str] = []
    for p in normalized:
        if _UNSAFE_PATH.search(p):
            raise ValueError(f"Lane path must not contain '..': {p!r}")
        out.append(p)
    return out


def git_ls_tree_lines(git_dir: Path, tree_ish: str, paths: Sequence[str]) -> list[str]:
    """
    Return sorted `git ls-tree -r` output lines for selected paths.

    Args:
        git_dir (Path): Repository directory.
        tree_ish (str): Commit, ref, or tree expression to inspect.
        paths (Sequence[str]): Path prefixes to include.

    Returns:
        list[str]: Sorted non-empty `git ls-tree` lines.

    Raises:
        RuntimeError: If `git ls-tree` fails.
    """
    if not paths:
        return []
    cmd = ["git", "-C", str(git_dir), "ls-tree", "-r", tree_ish, "--", *paths]
    LOGGER.debug("Running: %s", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git ls-tree failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
        )
    lines = [line for line in proc.stdout.splitlines() if line]
    lines.sort()
    return lines


def fingerprint_lane(git_dir: Path, tree_ish: str, paths: Sequence[str]) -> str:
    """
    Compute a SHA256 fingerprint for the lane paths at a tree-ish.

    Args:
        git_dir (Path): Repository directory.
        tree_ish (str): Commit, ref, or tree expression to fingerprint.
        paths (Sequence[str]): Path prefixes that define the lane.

    Returns:
        str: Hex-encoded SHA256 digest of canonical `git ls-tree` output.
    """
    lines = git_ls_tree_lines(git_dir, tree_ish, paths)
    blob = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def git_ls_remote_tip(remote_url: str, branch: str) -> str:
    """
    Resolve the current object ID for a remote branch tip.

    Uses `git ls-remote` against `refs/heads/<branch>` in the current process
    environment (`HOME`, `SSH_AUTH_SOCK`, and related settings).

    For SSH remotes, callers must provide credentials equivalent to the clone
    step (for example Tekton `ssh-directory` copied to `$HOME/.ssh`). SSH host
    key handling mirrors Tekton git-init (`StrictHostKeyChecking=accept-new`).

    Args:
        remote_url (str): Git remote URL.
        branch (str): Branch name.

    Returns:
        str: Object ID for `refs/heads/<branch>`.

    Raises:
        RuntimeError: If `git ls-remote` fails or the branch ref is missing.
    """
    ref = f"refs/heads/{branch}"
    cmd = [
        "git",
        *_git_global_args_for_ssh_remote(remote_url),
        "ls-remote",
        remote_url,
        ref,
    ]
    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git ls-remote failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == ref:
            return parts[0]
    raise RuntimeError(f"Could not resolve {ref} from {remote_url}: {proc.stdout!r}")


def git_fetch_branch_tip(
    git_dir: Path, remote_name: str, remote_url: str, branch: str, local_ref: str
) -> None:
    """
    Shallow-fetch a remote branch tip into a local ref.

    This uses the same SSH/HTTPS credential requirements as
    `git_ls_remote_tip()`.

    Args:
        git_dir (Path): Repository directory.
        remote_name (str): Temporary remote name to create.
        remote_url (str): Git remote URL.
        branch (str): Branch name to fetch.
        local_ref (str): Destination local ref.

    Raises:
        RuntimeError: If remote add or fetch fails.
    """
    git_dir.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        ["git", "-C", str(git_dir), "rev-parse", "--git-dir"],
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        init = subprocess.run(
            ["git", "init", str(git_dir)],
            check=False,
            capture_output=True,
            text=True,
        )
        if init.returncode != 0:
            raise RuntimeError(
                f"git init failed ({init.returncode}): "
                f"{init.stderr.strip() or init.stdout.strip()}"
            )
    # remove the local remote if it exists
    subprocess.run(
        ["git", "-C", str(git_dir), "remote", "remove", remote_name],
        check=False,
        capture_output=True,
        text=True,
    )
    # add the remote
    add = subprocess.run(
        ["git", "-C", str(git_dir), "remote", "add", remote_name, remote_url],
        check=False,
        capture_output=True,
        text=True,
    )
    if add.returncode != 0:
        raise RuntimeError(
            f"git remote add failed: {add.stderr.strip() or add.stdout.strip()}"
        )
    # Force-update local ref so repeated invocations in the same clone still work.
    refspec = f"+refs/heads/{branch}:{local_ref}"
    fetch = subprocess.run(
        [
            "git",
            *_git_global_args_for_ssh_remote(remote_url),
            "-C",
            str(git_dir),
            "fetch",
            "--depth",
            "1",
            remote_name,
            refspec,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if fetch.returncode != 0:
        raise RuntimeError(
            f"git fetch failed ({fetch.returncode}): "
            f"{fetch.stderr.strip() or fetch.stdout.strip()}"
        )


def load_snapshot(path: Path) -> Any:
    """
    Load a snapshot JSON file.

    Args:
        path (Path): Snapshot file path.

    Returns:
        Any: Parsed JSON snapshot data.
    """
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_snapshot(path: Path, data: dict[str, Any]) -> None:
    """
    Write snapshot data to a JSON file.

    Args:
        path (Path): Output snapshot path.
        data (dict[str, Any]): Snapshot payload to serialize.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def record_snapshot(
    git_dir: Path,
    tree_ish: str,
    operator_path: str,
    added_or_modified_catalog_operators: str,
    output: Path,
) -> None:
    """
    Record a snapshot of the merge-base lane fingerprint.

    Args:
        git_dir (Path): Repository directory.
        tree_ish (str): Commit or ref used as the base snapshot point.
        operator_path (str): Operator path from detect-changes.
        added_or_modified_catalog_operators (str): Comma-separated catalog
            operator segments from detect-changes.
        output (Path): Snapshot JSON output path.
    """
    paths = build_lane_paths(operator_path, added_or_modified_catalog_operators)
    if not paths:
        write_snapshot(
            output,
            {"enabled": False, "reason": "no_lane_paths"},
        )
        LOGGER.info("Merge base lane guard disabled: no paths to fingerprint")
        return
    lane_fp = fingerprint_lane(git_dir, tree_ish, paths)
    write_snapshot(
        output,
        {
            "enabled": True,
            "base_oid": tree_ish,
            "lane_fp": lane_fp,
            "paths": paths,
        },
    )
    LOGGER.info(
        "Recorded merge base lane snapshot base_oid=%s paths=%s", tree_ish, paths
    )


EXIT_LANE_MISMATCH = 10


def verify_snapshot(
    git_dir: Path,
    remote_url: str,
    branch: str,
    snapshot_file: Path,
) -> int:
    """
    Verify snapshot validity against the current base branch lane.

    Returns 0 if merge is allowed, `EXIT_LANE_MISMATCH` if the lane changed on
    the base branch, and 1 when verification fails.

    If `remote_url` is not reachable from clone-local configuration alone,
    configure git credentials in the process environment as required by
    `git_ls_remote_tip()`.

    Args:
        git_dir (Path): Repository directory.
        remote_url (str): Upstream repository URL.
        branch (str): Base branch name.
        snapshot_file (Path): Snapshot JSON path written during record.

    Returns:
        int: Verification status code.

    Raises:
        ValueError: If snapshot content is structurally invalid.
    """
    try:
        snap = load_snapshot(snapshot_file)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.error("Failed to load or parse snapshot file %s: %s", snapshot_file, exc)
        return 1
    if not snap.get("enabled"):
        LOGGER.info("Merge base lane guard skipped (snapshot disabled)")
        return 0
    try:
        base_oid = str(snap["base_oid"])
        expected_fp = str(snap["lane_fp"])
        paths = list(snap["paths"])
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid merge-base snapshot file: {exc}") from exc
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise ValueError("Invalid merge-base snapshot: paths must be a list of strings")

    tip = git_ls_remote_tip(remote_url, branch)
    if tip == base_oid:
        LOGGER.info(
            "Merge base lane guard: branch tip unchanged (%s), skipping fingerprint",
            tip[:12],
        )
        return 0

    LOGGER.info(
        "Merge base lane guard: branch advanced %s -> %s, recomputing fingerprint",
        base_oid[:12],
        tip[:12],
    )
    # temporary references for the tip of the base branch
    remote = "merge-guard-upstream"
    local_ref = "refs/operator-pipelines/merge-guard-tip"
    git_fetch_branch_tip(git_dir, remote, remote_url, branch, local_ref)
    new_fp = fingerprint_lane(git_dir, local_ref, paths)
    if new_fp == expected_fp:
        LOGGER.info("Merge base lane guard: fingerprint unchanged at new tip")
        return 0

    LOGGER.warning(
        "Merge base lane guard: fingerprint mismatch (lane changed on %s)", branch
    )
    return EXIT_LANE_MISMATCH
