""" A script to promote catalog to latest/desired version """

import argparse
import logging
import os
import re
import shutil

from datetime import datetime
from git import Repo as GitRepo
from pathlib import Path
from typing import Any, Optional

from operatorcert import github, ocp_version_info
from operator_repo import Repo as OperatorRepo

LOG = logging.getLogger(__name__)

ORGANIZATIONS = {
    "community-test-repo": {
        "gh_repository": "mantomas/community-test-repo",
        "organization": "community-operators",
    },
    "certified-operators": {
        "gh_repository": "redhat-openshift-ecosystem/certified-operators",
        "organization": "certified-operators",
    },
    "redhat-marketplace-operators": {
        "gh_repository": "redhat-openshift-ecosystem/redhat-marketplace-operators",
        "organization": "redhat-marketplace",
    },
    "community-operators-prod": {
        "gh_repository": "redhat-openshift-ecosystem/community-operators-prod",
        "organization": "community-operators",
    },
    "community-operators-pipeline-preprod": {
        "gh_repository": "redhat-openshift-ecosystem/community-operators-pipeline-preprod",
        "organization": "community-operators",
    },
}


def setup_argparser() -> Any:
    """
    Setup a argument parser for the script

    Returns:
        Any: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Promote catalog to the target version, defaults to latest supported. "
        "You need to have GITHUB_TOKEN exported in the environment to create PRs. "
        "Author of the PRs will be the owner of the token."
    )
    parser.add_argument(
        "--local-repo", help="Local repository to be processed (abs path)"
    )
    parser.add_argument("--target-version", help="Version to promote to (eg. 4.16)")
    parser.add_argument(
        "--pyxis-url",
        default="https://catalog.redhat.com/api/containers/",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - branches will be pushed without creating PRs. "
        "Can be used to avoid multiple pipelines starting at once",
        default=False,
    )

    return parser


def copy_files_if_not_exist(
    operator_name: str,
    repo_dir: Path,
    source_version: str,
    target_version: str,
) -> list[str]:
    """
    Copy catalog and template files if they don't exist

    Args:
        operator_name (str): Operator name
        repo_dir (Path): Path to the processed local repository
        source (str): Source catalog directory
        target (str): Target catalog directory

    Returns:
        list[str]: List of relative paths to copied files
        for Git commit
    """
    to_commit = []

    # copy catalog files if they don't exist
    catalog_dir = repo_dir / "catalogs"
    catalog_target_dir = catalog_dir / f"v{target_version}" / operator_name
    catalog_target_dir.mkdir(mode=755, parents=True, exist_ok=True)
    catalog_source_dir = catalog_dir / f"v{source_version}" / operator_name
    for file in os.listdir(catalog_source_dir):
        source_file = catalog_source_dir / file
        target_file = catalog_target_dir / file
        if source_file.is_file() and not target_file.exists():
            LOG.info("Copying catalog %s to %s", source_file, target_file)
            shutil.copyfile(source_file, target_file)
            to_commit.append(target_file)
            to_commit.append(target_file)
    # copy template file if they don't exist
    templates_dir = repo_dir / "operators" / operator_name / "catalog-templates"
    source_template = templates_dir / f"v{source_version}.yaml"
    target_template = templates_dir / f"v{target_version}.yaml"
    if source_template.is_file() and not target_template.exists():
        LOG.info("Copying template %s to %s", source_template, target_template)
        shutil.copyfile(source_template, target_template)
        to_commit.append(target_template)

    return to_commit


def update_makefile(
    operator_name: str,
    repo_dir: Path,
    target_version: str,
) -> Optional[Path]:
    """
    Add target version to the `OCP_VERSIONS` in the Makefile if missing

    Args:
        operator_name (str): Operator name
        repo_dir (Path): Path to the processed local repository
        target_version (str): Target version to add
    """
    makefile_path = repo_dir / "operators" / operator_name / "Makefile"
    makefile_content = makefile_path.read_text().splitlines(keepends=True)

    makefile_out = []
    for line in makefile_content:
        # search for variable assignment
        if bool(re.match(r"^OCP_VERSIONS\s*=", line)):
            # find the group of versions on the line
            # OR any single quoted variants
            versions = re.search(r"(v\d+\.\d+(?:\s+v\d+\.\d+)*)", line)
            if not versions:
                LOG.warning(
                    "No OCP versions found in Makefile or invalid format: %s", line
                )
                return
            ocp_string = versions.group(1)
            # check target version in versions list to avoid false positives
            # from searching just the string
            if target_version not in ocp_string.split():
                split_point = line.rindex(ocp_string) + len(ocp_string)
                # update the line with target version
                updated = f"{line[:split_point]} v{target_version}{line[split_point:]}"
                makefile_out.append(updated)
                to_commit = makefile_path
            else:
                makefile_out.append(line)
        else:
            makefile_out.append(line)

    with open(makefile_path, "w") as makefile:
        makefile.writelines(makefile_out)

    return to_commit


def triage_operators(
    operators: list[str], repository: OperatorRepo
) -> tuple[list[str], list[str], list[str]]:
    """
    Triage operators based on promotion strategy

    Args:
        operators (list[str]): List of operators
    Returns:
        tuple ([list[str], ...): Operators triaged
        into 'never', 'always' and 'review'
    """
    never, always, review = [], [], []
    for operator in operators:
        config = repository.operator(operator).config
        strategy = config.get("fbc", {}).get("version_promotion_strategy")
        if strategy == "never":
            never.append(operator)
        elif strategy == "always":
            always.append(operator)
        elif strategy == "review-needed":
            review.append(operator)
        else:
            LOG.warning(
                "Unknown promotion strategy for operator %s: %s", operator, strategy
            )
            never.append(operator)

    return never, always, review


def commit_and_push(
    git_repo: GitRepo,
    head_branch: str,
    files_to_commit: list[str],
    message: str,
) -> None:
    """
    Commit and push changes to GH

    Args:
        git_repo (GitRepo): Git repository object
        head_branch (str): Source branch for the PR
        files_to_commit (list[str]): List of files to commit
        message (str): Commit message
    """
    git_repo.index.add(files_to_commit)
    LOG.info("Committing and pushing changes to %s", head_branch)
    git_repo.index.commit(message)
    git_repo.remotes.origin.push(head_branch)


def create_pr(
    base: str,
    head: str,
    title: str,
    local_repo: str,
) -> dict[str, Any]:
    """
    Create PR using GitHub API

    Args:
        base (str): Target branch
        head (str): Source branch of the PR
        title (str): PR title
        local_repo (str): Work directory
    """
    gh_repo = ORGANIZATIONS[local_repo]["gh_repository"]
    LOG.info("Creating PR in %s for branch %s", gh_repo, head)
    gh_api_url = f"https://api.github.com/repos/{gh_repo}/pulls"
    data = {"head": head, "base": base, "title": title}
    return github.post(gh_api_url, data)


def promote_catalog(
    repo_dir: Path,
    git_repo: GitRepo,
    valid_versions: list[str],
    target_version: str,
) -> tuple[list[dict[str, Any]], str]:
    """
    Promote catalog to the target version.
    Separate processing based on the promotion strategy

    Args:
        repo_dir (str): Path to the processed local repository
        git_repo (GitRepo): Git repository object
        valid_versions (list[str]): List of valid OCP versions in descending order
        target_version (str): Target version to promote to

    Returns:
        tuple ([list[dict[str, Any]], str]): List of dictionaries with promo branch, PR title
        and reviewers list and string with branch suffix for better branch identification
    """
    # decide source version for promotion
    try:
        source_version = valid_versions[valid_versions.index(target_version) + 1]
    except IndexError:
        LOG.error("No version to promote from")
        return
    LOG.info("Source version for promotion: %s", source_version)

    # get list of operators from the source catalog
    source_catalog = repo_dir / "catalogs" / f"v{source_version}"
    if not source_catalog.exists():
        LOG.error("Source catalog %s not found", source_catalog)
        return
    source_operators = os.listdir(source_catalog)
    operator_repo = OperatorRepo(repo_dir)
    never, always, review = triage_operators(source_operators, operator_repo)

    # prepare common variables
    base_branch = str(git_repo.active_branch)
    branch_suffix = str(int(datetime.now().timestamp()))

    LOG.info("Processing promotion from source branch: %s", base_branch)

    # store branch info for PR creation
    pr_info = []

    # process operators with `fbc.version_promotion_strategy == always`
    # meaning single PR for all operators
    head_branch = f"always-promote-v{target_version}-{branch_suffix}"
    create_or_clear_branch_and_checkout(
        git_repo,
        base_branch=base_branch,
        head_branch=head_branch,
    )
    always_strategy_to_commit = []
    for operator in always:
        to_commit = copy_files_if_not_exist(
            operator, repo_dir, source_version, target_version
        )
        if to_commit:
            always_strategy_to_commit.extend(to_commit)
        to_commit_makefile = update_makefile(operator, repo_dir, target_version)
        if to_commit_makefile:
            always_strategy_to_commit.append(to_commit_makefile)
    if always_strategy_to_commit:
        commit_and_push(
            git_repo,
            head_branch,
            always_strategy_to_commit,
            f"Promote operators with `fbc.version_promotion_strategy == always`"
            f" to catalog version {target_version}",
        )
        pr_info.append(
            {
                "head": head_branch,
                "title": f"Promote all operators with `version_promotion_strategy` 'always' "
                f" to catalog version {target_version}",
            }
        )
    LOG.info(
        "Processed operators with `fbc.version_promotion_strategy == always`: %s",
        always,
    )

    # process operators with `fbc.version_promotion_strategy == review-needed`
    # single PR for each operator for review reasons
    for operator in review:
        head_branch = f"review-promote-v{target_version}-{operator}-{branch_suffix}"
        create_or_clear_branch_and_checkout(
            git_repo,
            base_branch=base_branch,
            head_branch=head_branch,
        )
        to_commit = copy_files_if_not_exist(
            operator, repo_dir, source_version, target_version
        )
        to_commit_makefile = update_makefile(operator, repo_dir, target_version)
        if to_commit_makefile:
            to_commit.append(to_commit_makefile)
        # commit only if there is content
        if to_commit:
            commit_and_push(
                git_repo,
                head_branch,
                to_commit,
                f"Promote operator {operator} to catalog version {target_version}.",
            )
            pr_info.append(
                {
                    "head": head_branch,
                    "title": f"Promote operator {operator} to catalog version {target_version}.",
                }
            )
    LOG.info(
        "Processed operators with `fbc.version_promotion_strategy == review-needed`: %s",
        review,
    )

    LOG.info("Operators excluded from promotion: %s", never)
    return pr_info, branch_suffix


def create_or_clear_branch_and_checkout(
    git_repo: GitRepo,
    base_branch: str = None,
    head_branch: str = None,
) -> None:
    """
    Clear source/active branch and create target branch
    from source branch if provided

    Args:
        git_repo (GitRepo): Git repository object
        base_branch (str): Source branch for the changes
        head_branch (str): Target branch for the changes
    """
    # all new branches will be based on the base branch
    # if not provided, the active branch will be used
    if base_branch:
        git_repo.git.checkout(base_branch)
    # clear the active branch
    git_repo.git.clean("--force", "-d")  # remove untracked files
    git_repo.git.reset("--hard")  # remove uncommited changes
    # create and checkout to the new branch
    if head_branch:
        git_repo.git.checkout("HEAD", b=head_branch)


def repo_status_clean(git_repo: GitRepo) -> bool:
    """
    Check the working branch, uncommited changes and untracked files

    Args:
        git_repo (GitRepo): Git repository object
    """
    branch = str(git_repo.active_branch)
    uncommited_changes = git_repo.is_dirty()
    untracked_files = bool(git_repo.untracked_files)
    if branch not in ["main", "master"] or uncommited_changes or untracked_files:
        return False
    return True


def main() -> None:
    """
    Main function
    """
    parser = setup_argparser()
    args = parser.parse_args()
    LOG.setLevel(logging.INFO)
    if args.verbose:
        LOG.setLevel(logging.DEBUG)
    LOG.addHandler(logging.StreamHandler())

    LOG.info("Starting promotion process")

    local_repo_name = os.path.basename(args.local_repo.strip("/"))
    try:
        organization = ORGANIZATIONS.get(local_repo_name, {})["organization"]
    except KeyError:
        LOG.error("Repository %s not supported", local_repo_name)
        return

    # check repo status
    # all new branches will be based on actual branch
    # all previous changes will be lost
    git_repo = GitRepo(args.local_repo)
    base_branch = str(git_repo.active_branch)
    if not repo_status_clean(git_repo):
        LOG.warning(
            "The repo is either dirty or not on main branch, "
            "please check its status. "
            "If you decide to continue, the uncommited changes "
            "and untracked files will be lost."
        )
        its_ok = input("Do you want to continue? [y/N]: ") or "n"
        if its_ok.lower() != "y":
            LOG.info("Exiting")
            return

    create_or_clear_branch_and_checkout(git_repo)

    # configure repo with the token
    access_token = os.environ.get("GITHUB_TOKEN")
    gh_repository = ORGANIZATIONS[local_repo_name]["gh_repository"]
    remote_url_with_token = f"https://{access_token}@github.com/{gh_repository}.git"
    git_repo.remotes.origin.set_url(remote_url_with_token)

    # gather ocp_version related info
    target_version = args.target_version
    pyxis_url = args.pyxis_url
    ocp_versions = ocp_version_info(None, pyxis_url, organization)
    # `indices` are sorted by version in descending order
    valid_versions = [v.get("ocp_version") for v in ocp_versions["indices"]]
    # check if target version index exists
    if target_version and target_version not in valid_versions:
        LOG.error(
            "Target version %s not in valid versions %s", target_version, valid_versions
        )
        return

    # default to max version index
    if not target_version:
        target_version = ocp_versions["max_version_index"].get("ocp_version")

    # process promotion
    LOG.info("Promotion to version: %s", target_version)
    pr_info, branch_suffix = promote_catalog(
        Path(args.local_repo), git_repo, valid_versions, target_version
    )
    LOG.info("Suffix for all branches created and pushed: %s", branch_suffix)

    # dry run only pushes branches without creating PRs
    # this can be used to prepare PR branches and then create PRs manually
    # to avoid multiple pipelines starting at once
    if pr_info and not args.dry_run:
        for push_data in pr_info:
            create_pr(
                base_branch,
                push_data["head"],
                push_data["title"],
                local_repo_name,
            )

    LOG.info("Promotion process finished")
    # checkout back to the base branch
    git_repo.git.checkout(base_branch)


if __name__ == "__main__":
    main()
