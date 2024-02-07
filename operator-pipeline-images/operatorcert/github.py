"""
Github API client - should be replaced by github library
"""

import logging
import os
import urllib.parse
from typing import Any, Dict, List, Optional

import requests
from github import Github, Label, PaginatedList, PullRequest
from operatorcert.utils import add_session_retries

LOGGER = logging.getLogger("operator-cert")


def _get_session(auth_required: bool = False) -> requests.Session:
    """
    Create a Github http session with auth based on env variables.

    Auth is set to use OAuth token if auth is required.

    Args:
        auth_required (bool): Whether authentication should be required for the session

    Raises:
        Exception: Exception is raised when auth ENV variables are missing.

    Returns:
        requests.Session: Github session
    """
    session = requests.Session()
    add_session_retries(session)

    if auth_required:
        token = os.environ.get("GITHUB_TOKEN")

        if not token:
            raise ValueError(
                "No auth details provided for Github. Define GITHUB_TOKEN."
            )

        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

    return session


def get(
    url: str, params: Optional[Dict[str, str]] = None, auth_required: bool = True
) -> Any:
    """
    Issue a GET request to the GitHub API

    Args:
        url (str): Github API URL
        params (dict): Additional query parameters
        auth_required (bool): Whether authentication should be required for the session

    Returns:
       Any: GitHub response
    """
    session = _get_session(auth_required=auth_required)
    LOGGER.debug("GET GitHub request url: %s", url)
    LOGGER.debug("GET GitHub request params: %s", params)
    resp = session.get(url, params=params)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "GitHub GET query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise

    return resp.json()


def post(url: str, body: Dict[str, Any]) -> Any:
    """
    POST Github API request to given URL with given payload

    Args:
        url (str): Github API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Any: Github response
    """
    session = _get_session(auth_required=True)

    LOGGER.debug("POST Github request: %s", url)
    resp = session.post(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "GitHub POST query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def patch(url: str, body: Dict[str, Any]) -> Any:
    """
    PATCH GitHub API request to given URL with given payload

    Args:
        url (str): Github API URL
        body (Dict[str, Any]): Request payload

    Returns:
        Any: Github response
    """
    session = _get_session(auth_required=True)

    LOGGER.debug("PATCH Github request: %s", url)
    resp = session.patch(url, json=body)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        LOGGER.exception(
            "GitHub PATCH query failed with %s - %s - %s",
            url,
            resp.status_code,
            resp.text,
        )
        raise
    return resp.json()


def add_labels_to_pull_request(
    pull_request: PullRequest.PullRequest, label_names: List[str]
) -> None:
    """
    Add labels to a pull request.

    Args:
        pull_request (PullRequest.PullRequest): Github Pull Request object
        label_names (List[str]): List of label names to add
    """
    for label in label_names:
        LOGGER.info("Adding label %s", label)
        pull_request.add_to_labels(label)


def remove_labels_from_pull_request(
    pull_request: PullRequest.PullRequest, label_names: List[str]
) -> None:
    """
    Remove labels from a pull request.

    Args:
        pull_request (PullRequest.PullRequest): Github Pull Request object
        label_names (List[str]):List of label names to remove
    """
    for label in label_names:
        LOGGER.info("Removing label %s", label)
        pull_request.remove_from_labels(label)


def detect_namespace_labels(
    current_labels: PaginatedList.PaginatedList[Label.Label],
    label_namespaces: List[str],
) -> List[str]:
    """
    Return a list of current labels that match the given namespaces.

    Args:
        current_labels (List[Label.Label]): List of current labels
        label_namespaces (List[str]): List of label namespaces

    Returns:
        List[str]: List of current labels that match the given namespaces
    """
    namespace_labels = []
    for label in current_labels:
        for label_namespace in label_namespaces:
            if label.name.startswith(label_namespace) and "/" in label.name:
                namespace_labels.append(label.name)
    return namespace_labels


def parse_github_issue_url(github_issue_url: str) -> tuple[str, int]:
    """
    Parse github issue url and return repository and issue id.

    Args:
        github_issue_url (str): Github issue url

    Returns:
        str: Repository name
        int: Issue id
    """
    split_url = urllib.parse.urlparse(github_issue_url).path.split("/")
    repository = "/".join(split_url[1:3])
    issue_id = int(split_url[-1])
    return repository, issue_id


def add_or_remove_labels(  # pylint: disable=too-many-locals
    github_client: Github,
    github_issue_url: str,
    add_labels: List[str],
    remove_labels: List[str],
    remove_matching_namespace_labels: bool,
) -> None:
    """
    Edit labels on a pull request based on input arguments.

    Args:
        github_client (Github): Github api client
        github_issue_url (str): Github issue url
        add_labels (List[str]): List of labels to add
        remove_labels (List[str]): List of labels to remove
        remove_matching_namespace_labels (bool): A flag that enables
            removal of existing labels within a namespace given
            by add_labels argument
    """
    repository_name, pr_id = parse_github_issue_url(github_issue_url)

    LOGGER.info("Adding labels %s to %s", add_labels, repository_name)
    repository = github_client.get_repo(repository_name)
    pull_request = repository.get_pull(pr_id)
    current_labels = pull_request.get_labels()

    labels_to_add = []
    labels_to_remove = []

    current_labels_name = [label.name for label in current_labels]

    for label in add_labels:
        if label not in current_labels_name:
            labels_to_add.append(label)

    for label in remove_labels:
        if label in current_labels_name:
            labels_to_remove.append(label)

    if remove_matching_namespace_labels:
        # Check if labels that will be added contains a namespace and
        # remove existing labels with matching namespace
        namespaces = []
        for label in add_labels:
            if "/" in label:
                # Parse namespace from the "add" label list
                namespaces.append(label.split("/")[0])

        # Find out which labels to remove based on the namespace
        namespace_labels = detect_namespace_labels(current_labels, namespaces)

        # Exclude labels that are already in the "add" list
        labels_to_remove_in_namespace = list(set(namespace_labels) - set(add_labels))
        LOGGER.info("Labels to remove in namespace: %s", labels_to_remove_in_namespace)
        labels_to_remove.extend(labels_to_remove_in_namespace)

    LOGGER.info("Current labels: %s", current_labels)
    LOGGER.info("Labels to add: %s", labels_to_add)
    LOGGER.info("Labels to remove: %s", labels_to_remove)

    add_labels_to_pull_request(pull_request, labels_to_add)
    remove_labels_from_pull_request(pull_request, labels_to_remove)
