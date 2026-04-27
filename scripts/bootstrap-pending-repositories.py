"""A script to bootstrap pending repositories with index images from public mirrors"""

import argparse
import logging
import os
import subprocess
import tempfile
from subprocess import CalledProcessError
from typing import Any, List, Optional, Tuple

from operatorcert import ocp_version_info
from operatorcert.operator_repo import Repo

LOGGER = logging.getLogger(__name__)

PYXIS_URL = "https://catalog.redhat.com/api/containers/"
ENV_CONFIG = {
    "stage": {
        "git_repositories": [
            "https://github.com/redhat-openshift-ecosystem/certified-operators-preprod.git",
            "https://github.com/redhat-openshift-ecosystem/community-operators-pipeline-preprod.git",
            "https://github.com/redhat-openshift-ecosystem/redhat-marketplace-operators-preprod.git",
        ],
    },
    "prod": {
        "git_repositories": [
            "https://github.com/redhat-openshift-ecosystem/certified-operators.git",
            "https://github.com/redhat-openshift-ecosystem/community-operators-prod.git",
            "https://github.com/redhat-openshift-ecosystem/redhat-marketplace-operators.git",
        ],
    },
}


def run_command(
    cmd: List[str], check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    """
    Run a shell command and return its output.

    Args:
        cmd (List[str]): Command to run
        check (bool): Whether to raise an exception on non-zero exit code

    Returns:
        CompletedProcess: Command output
    """
    LOGGER.debug(f"Running command: {cmd}")
    try:
        output = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )
    except CalledProcessError as e:
        LOGGER.error(f"Error running command: \nstdout: {e.stdout}\nstderr: {e.stderr}")
        raise e
    LOGGER.debug(f"Command output: {output.stdout.decode('utf-8')}")
    return output


def copy_index(
    src: str,
    dest: str,
    src_authfile: Optional[str] = None,
    dest_authfile: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """
    Copy an index image from source to destination

    Args:
        src (str): Source image with version (e.g., quay.io/redhat/redhat----certified-operator-index:v4.20)
        dest (str): Destination image with version
        src_authfile (str): Path to source authentication file
        dest_authfile (str): Path to destination authentication file
        dry_run (bool): If True, only log what would be done without executing

    Returns:
        bool: True if copy succeeded, False otherwise
    """
    LOGGER.info(f"{'[DRY RUN] ' if dry_run else ''}Copying {src} -> {dest}")

    if dry_run:
        return True

    cmd = [
        "skopeo",
        "copy",
        "--retry-times",
        "5",
        "--format",
        "v2s2",
        "--all",
    ]

    if src_authfile:
        cmd.extend(["--src-authfile", src_authfile])

    if dest_authfile:
        cmd.extend(["--dest-authfile", dest_authfile])

    cmd.extend([f"docker://{src}", f"docker://{dest}"])

    try:
        run_command(cmd)
    except CalledProcessError:
        LOGGER.error(f"Failed to copy {src} -> {dest}")
        return False
    return True


def validate_image_access(image: str, authfile: Optional[str]) -> bool:
    """
    Validate read access to an image

    Args:
        image (str): Image to test access with
        authfile (str): Path to authentication file

    Returns:
        bool: True if access validation succeeded, False otherwise
    """
    LOGGER.info(f"Validating read access with: {image}")

    cmd = ["skopeo", "inspect", f"docker://{image}"]
    if authfile:
        cmd.extend(["--authfile", authfile])

    try:
        run_command(cmd)
        LOGGER.info("Access validation successful")
    except CalledProcessError:
        LOGGER.error("Access validation failed")
        LOGGER.error("Make sure that skopeo authfile is setup correctly")
        return False
    return True


def clone_repository(git_url: str, temp_dir: str) -> str:
    """
    Clone a git repository to a temporary directory

    Args:
        git_url (str): Git repository URL
        temp_dir (str): Temporary directory path

    Returns:
        str: Path to cloned repository
    """
    repo_name = git_url.rstrip("/").split("/")[-1].replace(".git", "")
    clone_path = os.path.join(temp_dir, repo_name)

    LOGGER.info(f"Cloning {git_url}")

    cmd = ["git", "clone", "--depth", "1", git_url, clone_path]
    run_command(cmd)

    return clone_path


def collect_copy_pairs(
    git_repositories: List[str], pyxis_url: str
) -> List[Tuple[str, str]]:
    """
    Collect all copy pairs from git repositories

    Args:
        git_repositories (List[str]): List of git repository URLs
        pyxis_url (str): Pyxis URL to query for supported OCP versions

    Returns:
        List[Tuple[str, str]]: List of (source, destination) tuples
    """
    all_copy_pairs = []

    with tempfile.TemporaryDirectory() as temp_dir:
        for git_repo_url in git_repositories:
            # clone repos to get config.yaml files used by ocp_version_info()
            local_repo_path = clone_repository(git_repo_url, temp_dir)
            repo = Repo(local_repo_path)

            version_info = ocp_version_info(
                bundle_path=None, pyxis_url=pyxis_url, repo=repo
            )

            indices = version_info.get("indices", [])

            LOGGER.info(f"Found {len(indices)} supported versions for {git_repo_url}")

            sources = [idx["repository_with_version"] for idx in indices]
            destinations = [idx["pending_repository_with_version"] for idx in indices]

            for src, dest in zip(sources, destinations):
                all_copy_pairs.append((src, dest))

    return all_copy_pairs


def perform_copies(
    copy_pairs: List[Tuple[str, str]],
    src_authfile: Optional[str],
    dest_authfile: Optional[str],
    dry_run: bool,
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """
    Perform all copy operations

    Args:
        copy_pairs (List[Tuple[str, str]]): List of (source, destination) tuples
        src_authfile (str): Path to source authentication file
        dest_authfile (str): Path to destination authentication file
        dry_run (bool): If True, only simulate copying

    Returns:
        Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]: (successful_copies, failed_copies) lists
    """
    successful_copies = []
    failed_copies = []

    for src, dest in copy_pairs:
        success = copy_index(
            src=src,
            dest=dest,
            src_authfile=src_authfile,
            dest_authfile=dest_authfile,
            dry_run=dry_run,
        )
        if success:
            successful_copies.append((src, dest))
        else:
            failed_copies.append((src, dest))

    return successful_copies, failed_copies


def print_summary(
    successful_copies: List[Tuple[str, str]], failed_copies: List[Tuple[str, str]]
) -> None:
    """
    Print summary of copy operations

    Args:
        successful_copies (List[Tuple[str, str]]): List of successful (source, destination) tuples
        failed_copies (List[Tuple[str, str]]): List of failed (source, destination) tuples
    """
    LOGGER.info("Summary:")
    LOGGER.info(
        f"Total copies attempted: {len(successful_copies) + len(failed_copies)}"
    )
    LOGGER.info(f"Successful: {len(successful_copies)}")
    LOGGER.info(f"Failed: {len(failed_copies)}")

    if successful_copies:
        LOGGER.info("")
        LOGGER.info("Successful copies:")
        for src, dest in successful_copies:
            LOGGER.info(f"  {src} -> {dest}")

    if failed_copies:
        LOGGER.info("")
        LOGGER.info("Failed copies:")
        for src, dest in failed_copies:
            LOGGER.info(f"  {src} -> {dest}")


def setup_argparser() -> Any:
    """
    Setup argument parser for the script

    Returns:
        Any: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Bootstrap pending repositories by copying index images from public repository mirrors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--env",
        choices=["stage", "prod"],
        required=True,
        help="Environment to bootstrap (stage or prod)",
    )
    parser.add_argument(
        "--pyxis-url",
        help="Pyxis URL to query for supported OCP versions (defaults to environment-specific URL)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without actually copying",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--skip-confirmation",
        action="store_true",
        help="Skip confirmation prompt before copying",
    )
    parser.add_argument(
        "--src-authfile",
        help="Path to source authentication file (Docker config.json format)",
    )
    parser.add_argument(
        "--dest-authfile",
        help="Path to destination authentication file (Docker config.json format)",
    )
    return parser


def main() -> None:
    """
    Main function
    """
    parser = setup_argparser()
    args = parser.parse_args()

    LOGGER.setLevel(logging.INFO)
    if args.verbose:
        LOGGER.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)

    if args.dry_run:
        LOGGER.info("[DRY RUN] No actual copying will occur")

    config = ENV_CONFIG[args.env]
    pyxis_url = args.pyxis_url or PYXIS_URL
    git_repositories = config["git_repositories"]

    LOGGER.info(f"Using env: {args.env}, Pyxis URL: {pyxis_url}")

    all_copy_pairs = collect_copy_pairs(git_repositories, pyxis_url)
    if not all_copy_pairs:
        LOGGER.info("No copies to perform. No source + destination pairs found.")
        return

    LOGGER.info(f"The following {len(all_copy_pairs)} copies will be performed:")
    for src, dest in all_copy_pairs:
        LOGGER.info(f"  {src} -> {dest}")

    # try skopeo inspect on one source to ensure script has read access
    if not validate_image_access(all_copy_pairs[0][0], args.src_authfile):
        return

    # ask user for explicit confirmation before performing the copy commands
    if not args.dry_run and not args.skip_confirmation:
        LOGGER.warning(
            "If you proceed, writing operations to destination repositories will be performed."
        )
        response = input("Proceed? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            LOGGER.info("Aborted by user")
            return

    successful_copies, failed_copies = perform_copies(
        all_copy_pairs, args.src_authfile, args.dest_authfile, args.dry_run
    )

    print_summary(successful_copies, failed_copies)


if __name__ == "__main__":
    main()
