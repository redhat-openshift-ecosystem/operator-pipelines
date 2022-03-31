import argparse
import base64
import json
import logging
import os
from typing import Any, Dict, List
from urllib.parse import urljoin

import magic
from operatorcert import pyxis
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Bundle dockerfile generator.")

    parser.add_argument(
        "--pyxis-url",
        default="https://catalog.redhat.com/api/containers/",
        help="Base URL for Pyxis container metadata API",
    )
    parser.add_argument(
        "--cert-project-id", help="Certification project ID", required=True
    )
    parser.add_argument(
        "--certification-hash", help="Certification bundle hash", required=True
    )
    parser.add_argument(
        "--operator-package-name", help="Operator package name", required=True
    )
    parser.add_argument("--operator-version", help="Operator version", required=True)
    parser.add_argument("--path", help="Path to artifact", required=True)
    parser.add_argument(
        "--pull-request-url",
        help="URL to the pull request associated with the cert project.",
    )
    parser.add_argument(
        "--type",
        choices=[
            "preflight-logs",
            "preflight-artifacts",
            "preflight-results",
            "pipeline-logs",
        ],
        help="Type of artifact",
        required=True,
    )
    parser.add_argument(
        "--output",
        default="output.json",
        help="Location of output file",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def get_artifacts(artifacts_dir: str) -> List[str]:
    """
    Get test artifacts files from artifacts directory

    Args:
        artifacts_dir (str): Path to artifact directory

    Returns:
        List[str]: List of artifacts files
    """
    artifact_paths = []
    if not os.path.isdir(artifacts_dir):
        LOGGER.warning(f"{artifacts_dir} is not directory")
        return artifact_paths
    files = os.listdir(artifacts_dir)
    LOGGER.debug(f"Found following artifacts: {files}")
    for artifact in files:
        if os.path.isfile(os.path.join(artifacts_dir, artifact)):
            artifact_paths.append(artifact)
    return artifact_paths


def upload_artifact(args: Any, file_path: str, org_id: Any = None) -> Dict[str, Any]:
    """
    Upload artifact using Pyxis API

    Args:
        args (Any): CLI arguments
        file_path (str): Path to a artifact file
        org_id (Any): organization ID - optional

    Returns:
        Dict[str, Any]: Pyxis response
    """
    upload_url = urljoin(
        args.pyxis_url, f"v1/projects/certification/id/{args.cert_project_id}/artifacts"
    )
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as artifact:
        content = artifact.read()
    base64_content = base64.b64encode(content).decode("utf8")

    mime = magic.from_file(file_path, mime=True)
    artifact_payload = {
        "content": base64_content,
        "certification_hash": args.certification_hash,
        "content_type": mime,
        "filename": file_name,
        "file_size": file_size,
        "operator_package_name": args.operator_package_name,
        "version": args.operator_version,
    }
    if org_id:
        artifact_payload["org_id"] = org_id
    if args.pull_request_url:
        artifact_payload["pull_request_url"] = args.pull_request_url
    return pyxis.post(upload_url, artifact_payload)


def upload_artifacts(args: Any, org_id: Any = None) -> List[Dict[str, Any]]:
    """
    Upload all test artifacts using Pyxis API

    Args:
        args (Any): CLI arguments
        org_id (Any): organization ID - optional

    Returns:
        List[Dict[str, Any]]: List of Pyxis responses
    """
    artifacts = get_artifacts(args.path)
    responses = []
    for artifact_path in artifacts:
        LOGGER.info(f"Uploading artifact: {artifact_path}")
        full_path = os.path.join(args.path, artifact_path)

        response = upload_artifact(args, full_path, org_id)
        responses.append(response)
    return responses


def upload_test_results(args: Any, org_id: Any = None) -> Dict[str, Any]:
    """
    Upload test results using Pyxis API

    Args:
        args (Any): CLI tool arguments
        org_id (Any): organization ID - optional

    Returns:
        Dict[str, Any]: Pyxis test results response
    """
    with open(args.path, "r") as result_file:
        results = json.load(result_file)

    upload_url = urljoin(
        args.pyxis_url,
        f"v1/projects/certification/id/{args.cert_project_id}/test-results",
    )
    results = {
        **results,
        "certification_hash": args.certification_hash,
        "operator_package_name": args.operator_package_name,
        "version": args.operator_version,
    }
    if org_id:
        results["org_id"] = org_id
    return pyxis.post(upload_url, results)


def upload_results_and_artifacts(args: Any) -> Dict[str, Any]:
    """
    Upload test results and artifacts using Pyxis API

    Args:
        args (Any): CLI arguments

    Returns:
        Dict[str, Any]]: Artifacts respones
    """
    org_id = None
    if pyxis.is_internal():
        # External Pyxis gets org_id directly from API key - internally we
        # have to get it from project
        project = pyxis.get_project(args.pyxis_url, args.cert_project_id)
        org_id = project.get("org_id")

    if args.type in ["preflight-logs", "pipeline-logs"]:
        response = upload_artifact(args, args.path, org_id=org_id)
    elif args.type == "preflight-artifacts":
        response = upload_artifacts(args, org_id=org_id)
    elif args.type == "preflight-results":
        response = upload_test_results(args, org_id=org_id)

    return response


def main():  # pragma: no cover
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)

    response = upload_results_and_artifacts(args)
    with open(args.output, "w") as output:
        json.dump(response, output)
    LOGGER.info(f"Output stored in: {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()
