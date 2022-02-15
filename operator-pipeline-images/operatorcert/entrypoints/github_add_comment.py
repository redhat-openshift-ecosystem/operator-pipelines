"""
Script for adding a comment to a pull request or an issue.
It can take either a filename or a comment as input and can
post the comment back to GitHub accordingly.
"""
import argparse
import logging
import json
import os
import http.client
import sys
import urllib.parse

from operatorcert import github, store_results
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
        default="api.github.com",
        help="The GitHub host, default: api.github.com",
    )
    parser.add_argument(
        "--request-url",
        required=True,
        help="The GitHub issue or pull request URL where we want to add a new comment.",
    )
    parser.add_argument(
        "--comment-or-file",
        required=True,
        help="The actual comment to add or the filename containing comment to post.",
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
    comment_or_file: str,
    commen_tag: str,
    replace: str,
) -> None:

    split_url = urllib.parse.urlparse(request_url).path.split("/")

    # This will convert https://github.com/foo/bar/pull/202 to
    # api url path /repos/foo/issues/
    base = ""
    package = "/".join(split_url[1:3])
    id = split_url[-1]
    api_url = f"{base}/repos/{package}/issues/{id}"

    comment_param_value = comment_or_file
    # check if parameter passed is a filename or not
    if os.path.exists(comment_param_value):
        with open(comment_param_value, "r") as f:
            comment_param_value = f.read(comment_param_value)

    # If a tag was specified, append it to the comment
    if commen_tag != "":
        comment_param_value += f"<!-- {commen_tag} -->"
    data = {"body": comment_param_value}

    # This is for our fake github server
    if github_host_url.startswith("http://"):
        conn = http.client.HTTPConnection(github_host_url.replace("http://", ""))
    else:
        conn = http.client.HTTPSConnection(github_host_url)

    # If 'replace' is true, we need to search for comments first
    matching_comment = ""
    if replace == "true":
        if not commen_tag:
            LOGGER.error("replace requested but no comment_tag specified")
            sys.exit(1)

        """ resp2 = github.get(f"http://{github_host_url}{api_url}/comments") """
        r = conn.request(
            "GET",
            api_url + "/comments",
            headers={
                "User-Agent": "TektonCD, the peaceful cat",
                "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
            },
        )
        resp = conn.getresponse()
        if not str(resp.status).startswith("2"):
            LOGGER.error(f"Error: {resp.status}")
            LOGGER.error(resp.read())
            sys.exit(1)
        LOGGER.debug(resp.status)
        comments = json.loads(resp.read())
        LOGGER.debug(comments)

        # If more than one comment is found take the last one
        matching_comment = [x for x in comments if commen_tag in x["body"]][-1:]
        if matching_comment:
            store_results({"old_comment": str(matching_comment[0])})
            matching_comment = matching_comment[0]["url"]

    if matching_comment:
        method = "PATCH"
        target_url = urllib.parse.urlparse(matching_comment).path
    else:
        method = "POST"
        target_url = api_url + "/comments"

    LOGGER.info(f"Sending this data to GitHub with {method}")
    LOGGER.info(data)

    r = conn.request(
        method,
        target_url,
        body=json.dumps(data),
        headers={
            "User-Agent": "TektonCD, the peaceful cat",
            "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        },
    )
    resp = conn.getresponse()
    if not str(resp.status).startswith("2"):
        LOGGER.debug(f"Error: {resp.status}")
        LOGGER.debug(resp.read())
    else:
        store_results({"new_comment": resp.read()})
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
        args.comment_or_file,
        args.comment_tag,
        args.replace,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
