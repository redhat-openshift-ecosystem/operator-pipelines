"""
The CLI interface for uploading files to Github gists.
"""

import argparse
import json
import logging
import os
import urllib
from pathlib import Path
from typing import Any, List, Iterator

from github import Auth, Gist, Github, InputFileContent, IssueComment
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Upload files to GitHub gists.")

    parser.add_argument(
        "input_path",
        type=Path,
        help="The file or directory that will be used to create github gist",
        nargs="+",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="The output json file with the gist URL",
    )
    parser.add_argument(
        "--pull-request-url",
        help="The pull request URL where we want to add a new comment with the gist link.",
    )
    parser.add_argument(
        "--comment-prefix",
        help="The prefix that will be added to the comment with the gist link.",
        default="",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def files_in_dir(root_dir: Path) -> Iterator[Path]:
    """Yield all regular files (not directories or special files) in a directory tree"""
    for item in root_dir.iterdir():
        if item.is_dir():
            yield from files_in_dir(item)
        elif item.is_file():
            yield item


def create_github_gist(github_api: Github, input_path: List[Path]) -> Gist.Gist:
    """
    Create a GitHub gist from a file

    Args:
        github_api (Github): Github API object
        input_path (Path): Path to the files or directories that will be used
            to create the gist

    Returns:
        Gist.Gist: GitHub gist object
    """
    github_auth_user = github_api.get_user()

    gist_content = {}

    for input_item in input_path:
        if input_item.is_dir():
            for file_path in files_in_dir(input_item):
                gist_content[str(file_path.relative_to(input_item))] = InputFileContent(
                    file_path.read_text(encoding="utf-8")
                )
        elif input_item.is_file():
            gist_content[input_item.name] = InputFileContent(
                input_item.read_text(encoding="utf-8")
            )
        else:
            LOGGER.warning("Skipping %s, not a file or directory", input_item)

    LOGGER.info("Creating gist from %s", gist_content.keys())
    gist = github_auth_user.create_gist(
        True,
        gist_content,
    )
    LOGGER.info("Gist created: %s", gist.html_url)
    return gist


def share_github_gist(
    github_api: Github,
    github_repo: str,
    github_pr_id: int,
    gist: Gist.Gist,
    comment_prefix: str = "",
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

    return pull_request.create_issue_comment(f"{comment_prefix}{gist.html_url}")


def main() -> None:
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    github_auth = Auth.Token(os.environ.get("GITHUB_TOKEN") or "")
    github = Github(auth=github_auth)
    gist = create_github_gist(github, args.input_path)

    if args.pull_request_url:
        # If pull request URL is available, we will add a comment to the PR

        # This will convert https://github.com/foo/bar/pull/202 to repository name and issue ID
        split_url = urllib.parse.urlparse(args.pull_request_url).path.split("/")
        repository = "/".join(split_url[1:3])
        pr_id = int(split_url[-1])
        share_github_gist(github, repository, pr_id, gist, args.comment_prefix)

    if args.output_file:
        with args.output_file.open("w", encoding="utf-8") as output_file_handler:
            json.dump({"gist_url": gist.html_url}, output_file_handler)


if __name__ == "__main__":  # pragma: no cover
    main()
