"""
Script for adding a comment to a pull request or an issue.
It can take either a filename or a comment as input and can
post the comment back to GitHub accordingly.
"""
import argparse
import logging
import sys
import urllib.parse
from requests import HTTPError

from operatorcert import github
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> argparse.ArgumentParser:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Github cli tool to add comment to PR or an issue."
    )
    parser.add_argument(
        "--github-host-url",
        default="https://api.github.com",
        help="The GitHub host, default: https://api.github.com",
    )
    parser.add_argument(
        "--request-url",
        required=True,
        help="The GitHub issue or pull request URL where we want to add a new comment.",
    )
    parser.add_argument(
        "--comment-file",
        required=True,
        help="File with actual comment to post.",
    )
    parser.add_argument(
        "--comment-tag", help="An invisible tag to be added into the comment."
    )
    parser.add_argument(
        "--replace",
        default="false",
        help="When a tag is specified, and `replace` is `true`, look for a comment with a matching tag and replace it with the new comment.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def github_add_comment(
    github_host_url: str,
    request_url: str,
    comment_file: str,
    commen_tag: str,
    replace: str,
) -> None:
    split_url = urllib.parse.urlparse(request_url).path.split("/")

    # This will convert https://github.com/foo/bar/pull/202 to
    # api url path https://api.github.com/repos/foo/issues/202/comments
    package = "/".join(split_url[1:3])
    id = split_url[-1]
    api_url = f"{github_host_url}/repos/{package}/issues/{id}/comments"

    with open(comment_file, "r") as f:
        comment_param_value = f.read()

    # If a tag was specified, append it to the comment
    if commen_tag != "":
        comment_param_value += f"<!-- {commen_tag} -->"
    data = {"body": comment_param_value}

    # If 'replace' is true, we need to search for comments first
    matching_comment = ""
    if replace == "true":
        if not commen_tag:
            LOGGER.error("replace requested but no comment_tag specified")
            sys.exit(1)
        try:
            comments = github.get(api_url)
        except HTTPError:
            LOGGER.error(
                f"GitHub query failed with {api_url}, check if address is corect."
            )
            sys.exit(1)

        # If more than one comment is found take the last one
        matching_comment = [x for x in comments if commen_tag in x["body"]][-1:]
        if matching_comment:
            matching_comment = matching_comment[0]["url"]

    if matching_comment:
        LOGGER.info("Updating this data on GitHub with PATCH")
        LOGGER.info(data)
        target_url = f"{github_host_url}{urllib.parse.urlparse(matching_comment).path}"
        try:
            github.patch(target_url, data)
        except HTTPError:
            LOGGER.error(f"GitHub query failed with {target_url}.")
            sys.exit(1)
    else:
        LOGGER.info("Sending this data to GitHub with POST")
        LOGGER.info(data)
        try:
            github.post(api_url, data)
        except HTTPError:
            LOGGER.error(f"GitHub query failed with {api_url}.")
            sys.exit(1)

    method_used = "updated" if matching_comment else "added"
    LOGGER.info(f"a GitHub comment has been {method_used} to {request_url}")


def main() -> None:  # pragma: no cover
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    github_add_comment(
        args.github_host_url,
        args.request_url,
        args.comment_file,
        args.comment_tag,
        args.replace,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
