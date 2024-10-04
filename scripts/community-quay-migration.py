"""A script to migrate repositories from one Quay namespace to another"""

import argparse
import json
import logging
import os
import subprocess
from multiprocessing.pool import ThreadPool
from typing import Any, List

import requests

QUAY_HOST = "quay.io"
QUAY_HOST_HTTPS = f"https://{QUAY_HOST}"

LOGGER = logging.getLogger(__name__)


def get_paginated_results(api_token: str, url: str, response_key: str) -> Any:
    """
    Get paginated results from a Quay API endpoint

    Args:
        api_token (str): API token
        url (str): A full API URL
        response_key (str): The key in the response JSON that contains the results

    Returns:
        Any: API response
    """
    headers = {
        "Authorization": f"Bearer {api_token}",
    }
    results = []
    next_page = ""
    next_url = url
    while True:
        if next_page is not None:
            next_url = f"{url}&next_page={next_page}"
        response = requests.get(next_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        results.extend(data[response_key])
        next_page = data.get("next_page")
        if not next_page:
            break
    return results


def get_paginated_results_by_page_number(
    api_token: str, url: str, response_key: str
) -> Any:
    """
    Get paginated results from a Quay API endpoint using page numbers

    Args:
        api_token (str): API token
        url (str): Full API URL
        response_key (str): A key in the response JSON that contains the results

    Returns:
        Any: API response
    """
    page = 1
    headers = {
        "Authorization": f"Bearer {api_token}",
    }
    results = []
    while True:
        next_url = f"{url}?page={page}"
        response = requests.get(next_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not data.get(response_key):
            break
        results.extend(data[response_key])
        page += 1
    return results


def list_repositories(api_token: str, namespace: str) -> Any:
    """
    List repositories in a namespace

    Args:
        api_token (str): API token
        namespace (str): Quay namespace

    Returns:
        Any: List of repositories within the namespace
    """
    url = f"{QUAY_HOST_HTTPS}/api/v1/repository?namespace={namespace}"
    return get_paginated_results(api_token, url, "repositories")


def list_tags(api_token: str, namespace: str, repo_name: str) -> Any:
    """
    List tags for a repository

    Args:
        api_token (str): API token
        namespace (str): Quay namespace
        repo_name (str): A repository name within the namespace

    Returns:
        Any: List of tags for the repository
    """
    url = f"{QUAY_HOST_HTTPS}/api/v1/repository/{namespace}/{repo_name}/tag/"
    return get_paginated_results_by_page_number(api_token, url, "tags")


def get_repository(api_token: str, namespace: str, repo_name: str) -> Any:
    """
    Get repository details from Quay

    Args:
        api_token (str): API token
        namespace (str): Quay namespace
        repo_name (str): Repository name

    Returns:
        Any: A repository object if exists, None otherwise
    """
    url = f"{QUAY_HOST_HTTPS}/api/v1/repository/{namespace}/{repo_name}"
    headers = {
        "Authorization": f"Bearer {api_token}",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    return data


def create_repo(api_token: str, namespace: str, repo_name: str) -> Any:
    """
    Create a repository in Quay namespace

    Args:
        api_token (str): API token
        namespace (str): Quay namespace where the repository will be created
        repo_name (str): A name for the new repository

    Returns:
        Any: A repository object
    """
    url = f"{QUAY_HOST_HTTPS}/api/v1/repository"
    body = {
        "namespace": namespace,
        "repository": repo_name,
        "visibility": "public",
        "description": "Migrated from openshift-community-operators",
    }
    headers = {
        "Authorization": f"Bearer {api_token}",
    }
    response = requests.post(url, headers=headers, json=body)

    response.raise_for_status()
    data = response.json()
    return data


def migrate_repo(
    repo_name: str,
    source_namespace: str,
    destination_namespace: str,
    source_api_token: str,
    destination_api_token: str,
) -> None:
    """
    Migrate a repository from one namespace to another including all tags
    If a repository doesn't exist in the destination namespace, it will be
    created

    Args:
        repo_name (str): A repository name
        source_namespace (str): A namespace where the repository is located
        destination_namespace (str): A namespace where the repository will be migrated
        source_api_token (str): API token for the source namespace
        destination_api_token (str): API token for the destination namespace
    """
    tags = list_tags(source_api_token, source_namespace, repo_name)
    src_tag_names = [tag["name"] for tag in tags]

    dest_repo = get_repository(destination_api_token, destination_namespace, repo_name)
    if not dest_repo:
        LOGGER.info(f"Creating repository {repo_name} in {destination_namespace}")
        create_repo(destination_api_token, destination_namespace, repo_name)

    tags = list_tags(destination_api_token, destination_namespace, repo_name)
    dest_tag_names = [tag["name"] for tag in tags]

    # Tags that are in the source but not in the destination
    tag_diff = set(src_tag_names) - set(dest_tag_names)

    LOGGER.info(f"Source tags: ({len(src_tag_names)})")
    LOGGER.info(f"Destination tags: ({len(dest_tag_names)})")
    LOGGER.info(f"Tags to be migrated: ({len(tag_diff)})")

    results = []
    with ThreadPool(10) as pool:
        for index, tag in enumerate(tag_diff):
            LOGGER.info(f"Migrating tag ({index}/{len(tag_diff)}) {tag}")
            if "--202" in tag:
                # Tags with format v0.31.3--20220630T175815 are temporary and
                # should not be migrated
                LOGGER.info(f"Skipping tag {tag}")
                continue
            result = pool.apply_async(
                copy_tag,
                (
                    source_namespace,
                    repo_name,
                    tag,
                    destination_namespace,
                    repo_name,
                    tag,
                ),
            )
            results.append(result)
        for index, result in enumerate(results):
            LOGGER.info(f"Waiting for copy command ({index}/{len(results)})")
            result.get()


def run_command(
    cmd: List[str], check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    """
    Run a shell command and return its output.

    Args:
        cmd (List[str]): Command to run

    Returns:
        CompletedProcess: Command output
    """
    LOGGER.debug("Running command: %s", cmd)
    try:
        output = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )
    except subprocess.CalledProcessError as e:
        LOGGER.error(
            "Error running command: \nstdout: %s\nstderr: %s",
            e.stdout,
            e.stderr,
        )
        raise e
    LOGGER.debug("Command output: %s", output.stdout.decode("utf-8"))
    return output


def copy_tag(
    src_namespace: str,
    src_repo: str,
    src_tag: str,
    dest_namespace: str,
    dest_repo: str,
    dest_tag: str,
) -> None:
    """
    Copy a tag from one repository to another

    Args:
        src_namespace (str): Source namespace
        src_repo (str): Source repository name
        src_tag (str): Source tag
        dest_namespace (str): Destination namespace
        dest_repo (str): Destination repository name
        dest_tag (str): Destination tag
    """
    cmd = [
        "skopeo",
        "copy",
        "--retry-times",
        "5",
        f"docker://{QUAY_HOST}/{src_namespace}/{src_repo}:{src_tag}",
        f"docker://{QUAY_HOST}/{dest_namespace}/{dest_repo}:{dest_tag}",
        "--all",
    ]
    run_command(cmd)


def setup_argparser() -> Any:
    """
    Setup a argument parser for the script

    Returns:
        Any: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Migrate repositories from one namespace to another"
    )
    parser.add_argument("--cache-file", help="Path to a file to store the cache")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
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

    LOGGER.addHandler(logging.StreamHandler())

    LOGGER.info("Starting migration")
    source_namespace = "openshift-community-operators"
    destination_namespace = "community-operator-pipeline-prod"

    source_api_token = os.environ.get("QUAY_API_TOKEN_SRC")
    destination_api_token = os.environ.get("QUAY_API_TOKEN_DEST")
    # Set the request parameters
    src_repositories = list_repositories(source_api_token, source_namespace)
    src_repo_names = [repo["name"] for repo in src_repositories]
    if os.path.exists(args.cache_file):
        with open(args.cache_file, "r") as f:
            cache = json.load(f)
    else:
        cache = []
    for index, repo in enumerate(src_repo_names):
        LOGGER.info("-" * 80)
        LOGGER.info(f"Repository: ({index}/{len(src_repo_names)}) {repo}")
        if repo in cache:
            LOGGER.info(f"Skipping repository {repo}")
            continue
        migrate_repo(
            repo,
            source_namespace,
            destination_namespace,
            source_api_token,
            destination_api_token,
        )
        cache.append(repo)
        with open(args.cache_file, "w") as f:
            json.dump(cache, f, indent=2)


if __name__ == "__main__":
    main()
