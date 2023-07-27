"""
The CLI interface for uploading files to Github gists.
"""

import argparse
import json
import logging
import os
import urllib
from typing import Any

from github import Auth, Gist, Github, InputFileContent, IssueComment
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Upload file to Github gists.")

    parser.add_argument(
        "--input-file",
        help="The file that will be used to create github gist",
        required=True,
    )
    parser.add_argument(
        "--output-file",
        help="The output json file with the gist URL",
    )
    parser.add_argument(
        "--pull-request-url",
        help="The pull request URL where we want to add a new comment with the gist link.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def create_github_gist(github_api: Github, input_file: str) -> Gist.Gist:
    """
    Create a Github gist from a file

    Args:
        github_api (Github): Github API object
        input_file (str): Path to the file that will be used to create the gist

    Returns:
        Gist.Gist: Github gist object
    """
    github_auth_user = github_api.get_user()

    with open(input_file, "r") as f:
        file_content = f.read()

    LOGGER.info("Creating gist from %s", input_file)
    gist = github_auth_user.create_gist(
        True,
        {os.path.basename(input_file): InputFileContent(file_content)},
    )
    LOGGER.info("Gist created: %s", gist.html_url)
    return gist


def share_github_gist(
    github_api: Github, github_repo: str, github_pr_id: int, gist: Gist.Gist
) -> IssueComment.IssueComment:
    """
    Add a comment to the PR with a link to the gist

    Args:
        github_api (Github): Github API object
        github_repo (str): Github repository name
        github_pr_id (int): Github pull request ID
        gist (Gist.Gist): Github gist object

    Returns:
        IssueComment.IssueComment: Github issue comment object
    """
    repo = github_api.get_repo(github_repo)
    pull_request = repo.get_pull(github_pr_id)

    LOGGER.info("Adding gist link to PR %s (%s)", github_repo, github_pr_id)

    return pull_request.create_issue_comment(f"Pipeline logs: {gist.html_url}")


def main():
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN"))
    github = Github(auth=github_auth)
    gist = create_github_gist(github, args.input_file)

    if args.pull_request_url:
        # If pull request URL is available, we will add a comment to the PR

        # This will convert https://github.com/foo/bar/pull/202 to repository name and issue ID
        split_url = urllib.parse.urlparse(args.pull_request_url).path.split("/")
        repository = "/".join(split_url[1:3])
        pr_id = int(split_url[-1])
        share_github_gist(github, repository, pr_id, gist)

    if args.output_file:
        with open(args.output_file, "w") as f:
            json.dump({"gist_url": gist.html_url}, f)


if __name__ == "__main__":  # pragma: no cover
    main()
