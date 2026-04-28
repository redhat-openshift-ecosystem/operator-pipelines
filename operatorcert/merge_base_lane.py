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
    Extra `git -c ...` options so SSH matches Tekton git-clone (git-init) behavior.

    git-init uses StrictHostKeyChecking=accept-new, so clone works when the
    ssh-directory secret has a key but no known_hosts. Plain `git ls-remote` /
    `git fetch` in the pipeline image use OpenSSH defaults and fail with
    "Host key verification failed" in that setup.
    """
    u = remote_url.strip()
    if u.startswith("git@") or u.startswith("ssh://"):
        return [
            "-c",
            "core.sshCommand=ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new",
        ]
    return []


def split_csv(value: str) -> list[str]:
    """Split comma-separated Tekton params into stripped non-empty segments."""
    if not value or not value.strip():
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def catalog_operator_segment_to_repo_path(segment: str) -> str:
    """
    Map detect-changes catalog operator segments to repo-root-relative paths.

    `detect-changed-operators` emits `version/operator` (e.g. `v4.14/foo`)
    without the `catalogs/` prefix. Entries may also already be under
    `catalogs/...` in which case they are normalized as-is.
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
    Union and de-duplicate path prefixes that define the merge guard lane on the base tree.

    Uses `operator_path` (`operators/...`) and `added_or_modified_catalog_operators`
    from detect-changes (comma-separated `version/operator` or `catalogs/...`).
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
    Return sorted lines from `git ls-tree -r` for the given paths (stable fingerprint input).
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
    SHA256 hex digest of canonical ls-tree output for paths at tree_ish.
    """
    lines = git_ls_tree_lines(git_dir, tree_ish, paths)
    blob = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def git_ls_remote_tip(remote_url: str, branch: str) -> str:
    """
    Resolve refs/heads/<branch> OID via `git ls-remote`.

    Uses the current process environment (`HOME`, `SSH_AUTH_SOCK`, etc.).
    For SSH `remote_url` values, callers must install the same credentials as
    `git-clone` (for example Tekton `ssh-directory` copied to `$HOME/.ssh`)
    before invoking the CLI. SSH host-key handling matches Tekton git-init
    (`StrictHostKeyChecking=accept-new`) so missing `known_hosts` in the secret
    does not break verify after a successful clone.
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
    Shallow-fetch branch tip from `remote_url` into `local_ref`.

    Same SSH/HTTPS credential requirements as :func:`git_ls_remote_tip`.
    """
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
    """Load a snapshot from a file."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_snapshot(path: Path, data: dict[str, Any]) -> None:
    """Write a snapshot to a file."""
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
    """Record a snapshot of the merge-base lane fingerprint."""
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
    Returns 0 if merge is allowed, EXIT_LANE_MISMATCH if lane changed on base, 1 on error.

    When `remote_url` is not reachable from the local clone alone, `git ls-remote` /
    `git fetch` run in the process environment; configure git credentials accordingly
    (see :func:`git_ls_remote_tip`).
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
