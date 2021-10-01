import argparse
import json
import logging
import os
import re
import sys
from typing import Any

from twirp.context import Context
from twirp.exceptions import TwirpServerException
from google.protobuf.json_format import Parse

from operatorcert.webhook.webhook import webhook_twirp
from operatorcert.webhook.webhook import webhook_pb2
from operatorcert.logger import setup_logger


LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Call the IBM webhook to trigger marketplace replication"
    )
    parser.add_argument(
        "--bundle-image",
        required=True,
        help="Registry path to the operator bundle image",
    )
    parser.add_argument(
        "--bundle-image-digest",
        required=True,
        help="Digest of the operator bundle image",
    )
    parser.add_argument("--git-repo-url", required=True, help="URL of the git repo")
    parser.add_argument("--package", required=True, help="Operator package name")
    parser.add_argument(
        "--ocp-version", required=True, help="OCP versions in the bundle annotations"
    )
    parser.add_argument(
        "--version", required=True, help="Version of the operator bundle"
    )
    parser.add_argument(
        "--webhook-url",
        default="https://mirroring-mirroring.cicd-us-east-2-bx2-4x16-e45420c0be249b88cfacab5f393b43c1-0000.us-east.containers.appdomain.cloud",
        help="URL to call the webhook",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def call_ibm_webhook(args: Any) -> None:
    # Marketplace repos:
    # https://github.com/redhat-openshift-ecosystem/redhat-marketplace-operators-preprod/
    # https://github.com/redhat-openshift-ecosystem/redhat-marketplace-operators/
    marketplace_repo_regex = re.compile(
        ".*github\.com\/redhat-openshift-ecosystem\/redhat-marketplace-operators*"
    )
    if not marketplace_repo_regex.match(args.git_repo_url):
        LOGGER.info(
            f"{args.git_repo_url} is not a redhat-marketplace repo. Skipping "
            f"marketplace replication."
        )
        return
    else:
        LOGGER.info(
            f"{args.git_repo_url} is a redhat-marketplace repo. Proceeding with calling"
            f" IBM webhook to trigger marketplace replication."
        )

    token = os.environ.get("IBM_WEBHOOK_TOKEN")
    if not token:
        LOGGER.error(
            "No auth details provided for IBM webhook. Define IBM_WEBHOOK_TOKEN."
        )
        sys.exit(1)

    bundle_data = {
        "package": args.package,
        "ocp_version": args.ocp_version,
        "organization": "redhat-marketplace",
        "related_images": [
            {"digest": args.bundle_image_digest, "image": args.bundle_image}
        ],
        "version": args.version,
    }

    client = webhook_twirp.MirrorServiceClient(args.webhook_url)
    try:
        headers = {"X-Drpc-Metadata": f"auth.token={token}"}
        request = Parse(
            json.dumps({"data": [bundle_data]}), webhook_pb2.NewOperatorBundlesRequest()
        )
        response = client.NewOperatorBundles(
            ctx=Context(),
            request=request,
            headers=headers,
            server_path_prefix="",
            # TODO enable SSL verification for prod webhook
            verify=False,
        )
        LOGGER.debug("Webhook response: %s", response)
    except TwirpServerException as e:
        LOGGER.exception(str(e))
        sys.exit(1)


def main():
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(log_level)

    call_ibm_webhook(args)


if __name__ == "__main__":
    main()
