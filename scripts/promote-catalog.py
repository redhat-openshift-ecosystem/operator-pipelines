""" A script to promote catalog to latest/desired version """

import argparse
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from ruamel.yaml import YAML
from git import Repo as GitRepo
from operatorcert import github, ocp_version_info
from operatorcert.operator_repo import Repo as OperatorRepo

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


def copy_catalog_file_if_not_exist(
    operator_name: str,
    repo_dir: Path,
    source_version: str,
    target_version: str,
) -> str:
    """
    Copy catalog file if they don't exist yet

    Args:
        operator_name (str): Operator name
        repo_dir (Path): Path to the processed local repository
        source (str): Source catalog directory
        target (str): Target catalog directory

    Returns:
        str: A path to the copied catalog file
    """

    # copy catalog files if they don't exist
    catalog_dir = repo_dir / "catalogs"
    catalog_target_dir = catalog_dir / f"v{target_version}" / operator_name
    catalog_target_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    catalog_source_dir = catalog_dir / f"v{source_version}" / operator_name
    for file in os.listdir(catalog_source_dir):
        source_file = catalog_source_dir / file
        target_file = catalog_target_dir / file
        if source_file.is_file() and not target_file.exists():
            LOG.info("Copying catalog %s to %s", source_file, target_file)
            shutil.copyfile(source_file, target_file)
            return target_file


def add_catalog_to_ci_mapping(
    operator_name: str,
    repo_dir: Path,
    source_version: str,
    target_version: str,
) -> Optional[Path]:
    """
    Add target version to the catalog mapping in the CI file.
    The catalog is added to the same template as the source version.

    Args:
        operator_name (str): A name of the operator for which the catalog is added
        repo_dir (Path): Git repository path
        source_version (str): A version of the catalog to be promoted
        target_version (str): A version of the catalog to be added

    Returns:
        Optional[Path]: A path to the updated CI file
    """
    operator_ci_path = repo_dir / "operators" / operator_name / "ci.yaml"
    with open(operator_ci_path, "r") as ci_file:
        yaml = YAML()
        yaml.preserve_quotes = True

        ci_content = yaml.load(ci_file)

    # Append target version to the catalog mapping for
    # a same template as used for the source version
    mapping = ci_content.get("fbc", {}).get("catalog_mapping", {})
    all_catalog_from_mapping = [
        catalog for template in mapping for catalog in template.get("catalog_names", [])
    ]
    if f"v{target_version}" in all_catalog_from_mapping:
        LOG.info(
            "Catalog %s already exists in the mapping for operator %s",
            target_version,
            operator_name,
        )
        return None
    for template in mapping:
        if f"v{source_version}" in template.get("catalog_names", []):
            template["catalog_names"].append(f"v{target_version}")
            break
    else:
        LOG.warning(
            "Source version %s not found in catalog mapping for operator %s",
            source_version,
            operator_name,
        )
        return None

    with open(operator_ci_path, "w") as ci_file:
        yaml = YAML()
        yaml.explicit_start = True
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.dump(ci_content, ci_file)
    return operator_ci_path


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
        strategy = config.get("fbc", {}).get(
            "version_promotion_strategy", "review-needed"
        )
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

    # Construct the Signed-off-by line
    name = git_repo.config_reader().get_value("user", "name")
    email = git_repo.config_reader().get_value("user", "email")

    signed_off_by = f"Signed-off-by: {name} <{email}>"
    full_message = f"{message}\n\n{signed_off_by}"

    git_repo.index.commit(full_message)
    git_repo.remotes.upstream.push(head_branch)


def create_pr(
    base: str,
    head: str,
    title: str,
    body: str,
    local_repo: str,
) -> dict[str, Any]:
    """
    Create PR using GitHub API

    Args:
        base (str): Target branch
        head (str): Source branch of the PR
        title (str): PR title
        body (str): PR body text
        local_repo (str): Work directory
    """
    gh_repo = ORGANIZATIONS[local_repo]["gh_repository"]
    LOG.info("Creating PR in %s for branch %s to %s", gh_repo, head, base)
    gh_api_url = f"https://api.github.com/repos/{gh_repo}/pulls"
    data = {"head": head, "base": base, "title": title, "body": body}
    return github.post(gh_api_url, data)


def add_pr_labels(
    pr_id: int,
    labels: list[str],
    local_repo: str,
) -> dict[str, Any]:
    """
    Add labels to PR using GitHub API

    Args:
        pr_id (int): A PR where the labels are added
        labels (list[str]): List of labels to be added
        local_repo (str): Work directory
    """
    gh_repo = ORGANIZATIONS[local_repo]["gh_repository"]
    LOG.info("Adding PR labels %s for: %s", labels, pr_id)
    gh_api_url = f"https://api.github.com/repos/{gh_repo}/issues/{pr_id}/labels"
    data = {"labels": labels}
    return github.post(gh_api_url, data)


def always_promotion(
    repo_dir: Path,
    git_repo: GitRepo,
    operators: list[str],
    source_version: str,
    target_version: str,
    base_branch: str,
    branch_suffix: str,
) -> list[Any]:
    """
    Process operators with `fbc.version_promotion_strategy == always` and create
    a single PR for all operators.

    Args:
        repo_dir (Path): A path to git repository
        git_repo (GitRepo): Git repository object
        operators (list[str]): A list of operators to be promoted with `always` strategy
        source_version (str): A source version of the catalog to be promoted
        target_version (str): A target version of the catalog to be promoted
        base_branch (str): A git branch where the changes are based
        branch_suffix (str): A suffix for the branch name to be created

    Returns:
        list[Any]: A list of PR details
    """
    # process operators with `fbc.version_promotion_strategy == always`
    # meaning single PR for all operators
    pr_info = []
    head_branch = f"always-promote-v{target_version}-{branch_suffix}"
    create_or_clear_branch_and_checkout(
        git_repo,
        base_branch=base_branch,
        head_branch=head_branch,
    )
    LOG.debug("Processing operators with `fbc.version_promotion_strategy == always`")
    LOG.debug(operators)
    to_commit = []
    for operator in operators:
        LOG.debug("Processing operator %s", operator)
        catalog_file = copy_catalog_file_if_not_exist(
            operator, repo_dir, source_version, target_version
        )
        if catalog_file:
            to_commit.append(catalog_file)
        ci_file = add_catalog_to_ci_mapping(
            operator, repo_dir, source_version, target_version
        )
        if ci_file:
            to_commit.append(ci_file)

    if to_commit:
        commit_and_push(
            git_repo,
            head_branch,
            to_commit,
            f"Promote operators with `fbc.version_promotion_strategy == always`"
            f" to catalog version {target_version}",
        )
        pr_info.append(
            {
                "head": head_branch,
                "title": f"Promote all operators with `version_promotion_strategy` 'always' "
                f" to catalog version {target_version}",
                "labels": ["catalog-promotion/always"],
            }
        )
    return pr_info


def review_needed_promotion(
    repo_dir: Path,
    git_repo: GitRepo,
    operators: list[str],
    source_version: str,
    target_version: str,
    base_branch: str,
    branch_suffix: str,
) -> list[Any]:
    """
    Process operators with `fbc.version_promotion_strategy == review-needed` and create
    a single PR for each operator.

    Args:
        repo_dir (Path): A path to git repository
        git_repo (GitRepo): A git repository object
        operators (list[str]): A list of operators to be promoted with `review-needed` strategy
        source_version (str): A source version of the catalog to be promoted
        target_version (str): A target version of the catalog to be promoted
        base_branch (str): A git branch where the changes are based
        branch_suffix (str): A suffix for the branch name to be created

    Returns:
        list[Any]: A list of PR details
    """
    # process operators with `fbc.version_promotion_strategy == review-needed`
    # single PR for each operator for review reasons
    pr_info = []
    LOG.debug(
        "Processing operators with `fbc.version_promotion_strategy == review-needed`"
    )
    LOG.debug(operators)
    for operator in operators:
        files_to_commit = []
        head_branch = f"review-promote-v{target_version}-{operator}-{branch_suffix}"
        create_or_clear_branch_and_checkout(
            git_repo,
            base_branch=base_branch,
            head_branch=head_branch,
        )
        catalog_file_to_commit = copy_catalog_file_if_not_exist(
            operator, repo_dir, source_version, target_version
        )
        if catalog_file_to_commit:
            files_to_commit.append(catalog_file_to_commit)
        ci_file = add_catalog_to_ci_mapping(
            operator, repo_dir, source_version, target_version
        )
        if ci_file:
            files_to_commit.append(ci_file)

        # commit only if there is content
        if files_to_commit:
            commit_and_push(
                git_repo,
                head_branch,
                files_to_commit,
                f"Promote operator {operator} to catalog version {target_version}.",
            )
            pr_info.append(
                {
                    "head": head_branch,
                    "title": f"Promote operator {operator} to catalog version {target_version}.",
                    "labels": ["catalog-promotion/review-needed"],
                }
            )

    return pr_info


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

    always_prs = always_promotion(
        repo_dir,
        git_repo,
        always,
        source_version,
        target_version,
        base_branch,
        branch_suffix,
    )
    review_prs = review_needed_promotion(
        repo_dir,
        git_repo,
        review,
        source_version,
        target_version,
        base_branch,
        branch_suffix,
    )
    pr_info.extend(always_prs)
    pr_info.extend(review_prs)

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
    if (
        branch not in ["main", "master", "stage", "qa", "dev"]
        or uncommited_changes
        or untracked_files
    ):
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
    pr_body_text = f"""
## 📢 New OpenShift Version Support Added!

TL;DR: This automated PR promotes the operator catalog to support a newly released OpenShift version `v{target_version}`.
It ensures your operator remains available for installation on the latest OpenShift clusters.

### Purpose of this Pull Request

This PR has been automatically generated to promote the operator catalog for a newly released OpenShift version.

### What This PR Does

Adds support for OpenShift version `v{target_version}` in the catalog

Updates operator catalogs and metadata accordingly by promoting operators from `N-1` to `N` version.

### Why This PR Was Created

To maintain compatibility and improve user experience, we promote operator catalogs to support new OpenShift
versions shortly after their release. Keeping the catalog up to date ensures that cluster administrators can
deploy your operator without delay on the latest OpenShift versions.

If you want to controll how your operator is promoted to the new OpenShift version,
please check the `fbc.version_promotion_strategy` in the operator config file. Related
documentation can be found
[here](https://redhat-openshift-ecosystem.github.io/operator-pipelines/users/operator-ci-yaml/#fbcversion_promotion_strategy)
"""
    if pr_info and not args.dry_run:
        for push_data in pr_info:
            pr_response = create_pr(
                base_branch,
                push_data["head"],
                push_data["title"],
                pr_body_text,
                local_repo_name,
            )
            add_pr_labels(
                pr_response["number"],
                push_data["labels"],
                local_repo_name,
            )

    LOG.info("Promotion process finished")
    # checkout back to the base branch
    git_repo.git.checkout(base_branch)


if __name__ == "__main__":
    main()
