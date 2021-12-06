import argparse
import json
import logging
import os
import pathlib
import re
import sys
from typing import Any

from twirp.context import Context
from twirp.exceptions import TwirpServerException
from google.protobuf.json_format import Parse

from operatorcert import get_csv_content
from operatorcert.webhook.webhook import webhook_twirp
from operatorcert.webhook.webhook import webhook_pb2
from operatorcert.logger import setup_logger


LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Call the IBM webhook to trigger marketplace replication"
    )
    parser.add_argument(
        "--bundle-path",
        required=True,
        help="Location of the operator bundle",
    )
    parser.add_argument("--package", required=True, help="Operator package name")
    parser.add_argument(
        "--ocp-version", required=True, help="OCP versions in the bundle annotations"
    )
    parser.add_argument(
        "--organization",
        required=True,
        help="Organization from the project config.yaml, e.g. redhat-marketplace",
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
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Turn on SSL verification when triggering IBM webhook",
    )
    return parser


def call_ibm_webhook(args: Any) -> None:
    if args.organization == "redhat-marketplace":
        LOGGER.info(
            "Project organization is redhat-marketplace. Proceeding with calling IBM "
            "webhook to trigger marketplace replication."
        )
    else:
        LOGGER.info(
            "Not a redhat-marketplace project. Skipping marketplace replication."
        )
        return

    token = os.environ.get("IBM_WEBHOOK_TOKEN")
    if not token:
        LOGGER.error(
            "No auth details provided for IBM webhook. Define IBM_WEBHOOK_TOKEN."
        )
        sys.exit(1)

    csv = get_csv_content(pathlib.Path(args.bundle_path), args.package)
    related_images = csv.get("spec", {}).get("relatedImages")
    if not related_images:
        LOGGER.error("No related images found in cluster service version file.")
        sys.exit(1)

    bundle_data = {
        "package": args.package,
        "ocp_version": args.ocp_version,
        "organization": args.organization,
        "related_images": related_images,
        "version": args.version,
    }
    LOGGER.debug(f"Sending bundle data: {bundle_data}")

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
            # TODO: Currently, the endpoint in insecure in the preprod environments.
            # When the production endpoint will be ready, we should be able to use it securely without additional cert.
            verify=args.verify,
        )
        LOGGER.debug("Webhook response: %s", response)
    except TwirpServerException as e:  # pragma: no cover
        LOGGER.exception(str(e))
        sys.exit(1)


def main():  # pragma: no cover
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(log_level)

    call_ibm_webhook(args)


if __name__ == "__main__":  # pragma: no cover
    main()
