import argparse
import base64
import json
import logging
import os
import sys
import threading
import time
from typing import Any

import stomp

from operatorcert.logger import setup_logger
from operatorcert.umb import start_umb_client

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(
        description="Cli tool to request signature from RADAS"
    )
    parser.add_argument(
        "--manifest-digest",
        help="Manifest digest for the signed content, usually in the format sha256:xxx",
        required=True,
    )
    parser.add_argument(
        "--output",
        help="Path to an output file.",
        default="signing_response.json",
    )
    parser.add_argument(
        "--reference",
        help="Docker reference for the signed content, e.g. registry.redhat.io/redhat/community-operator-index:v4.9",
        required=True,
    )
    parser.add_argument(
        "--requester",
        default="amisstea@redhat.com",
        help="Name of the user that requested the signing, for auditing purposes",
        required=True,
    )
    parser.add_argument(
        "--sig-key-id",
        default="4096R/55A34A82 SHA-256",
        help="The signing key id that the content was signed with",
        required=True,
    )
    parser.add_argument(
        "--sig-key-name",
        default="containerisvsign",
        help="The signing key name that the content was signed with",
        required=True,
    )
    parser.add_argument(
        "--umb-client-name",
        default="operatorpipelines",
        help="Client name to connect to umb, usually a service account name",
        required=True,
    )
    parser.add_argument(
        "--umb-listen-topic",
        default="VirtualTopic.eng.robosignatory.isv.sign",
        help="umb topic to listen to for responses with signed content",
        required=True,
    )
    parser.add_argument(
        "--umb-publish-topic",
        default="VirtualTopic.eng.operatorpipelines.isv.sign",
        help="umb topic to publish to for requesting signing",
        required=True,
    )
    parser.add_argument(
        "--umb-url",
        default="umb.api.redhat.com",
        help="umb host to connect to for messaging",
        required=True,
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


umb = None
result_file = None

# wait for signing response for a total of 5 min, at 5 second intervals
TIMEOUT_COUNT = 60
WAIT_INTERVAL_SEC = 5


class UmbHandler(stomp.ConnectionListener):  # pragma: no cover
    def on_error(self, frame: Any) -> None:
        LOGGER.error("Received an error frame:\n{}".format(frame.body))

    def on_message(self, frame: Any) -> None:
        # handle response from radas in a thread
        t = threading.Thread(target=process_message, args=[frame.body])
        t.start()

    def on_disconnected(self: Any) -> None:
        LOGGER.error("Disconnected from umb.")


def process_message(msg: Any) -> None:
    """
    Process a message received from UMB.
    Args:
        msg: The message body received.
    """
    msg = json.loads(msg)["msg"]

    global umb
    if msg.get("request_id") == umb.id:
        LOGGER.info(f"Received radas response: {msg}")

        global result_file
        with open(result_file, "w") as f:
            json.dump(msg, f)
        LOGGER.info(f"Response from radas successfully received for request {umb.id}")
        sys.exit(0)
    else:
        LOGGER.info(f"Ignored message from another request ({msg.get('request_id')})")


def gen_sig_claim_file(reference: str, digest: str, requested_by: str) -> str:
    """
    Generated a claim file to be signed based on given data.
    Args:
        reference: Docker reference for the signed content,
            e.g. registry.redhat.io/redhat/community-operator-index:v4.9
        digest: Manifest digest for the signed content, usually in the format sha256:xxx
        requested_by: Name of the user that requested the signing, for auditing purposes
    """
    claim = {
        "critical": {
            "image": {"docker-manifest-digest": digest},
            "type": "atomic container signature",
            "identity": {"docker-reference": reference},
        },
        "optional": {"creator": requested_by},
    }

    claim = base64.b64encode(json.dumps(claim).encode("utf-8"))
    return claim.decode("utf-8")


def gen_image_name(reference: str) -> str:
    """
    Generate the image name as a signing input, based on the docker reference.
    Args:
        reference: Docker reference for the signed content,
            e.g. registry.redhat.io/redhat/community-operator-index:v4.9
    """
    no_tag = reference.split(":")[0]
    image_parts = no_tag.split("/")
    return "/".join(image_parts[1:])


def gen_request_msg(args, request_id):
    """
    Generate the request message to send to RADAS.
    Args:
        args: Args from script input.
        request_id: UUID to identify match the request with RADAS's response.

    Returns:

    """
    claim = gen_sig_claim_file(args.reference, args.manifest_digest, args.requester)
    image_name = gen_image_name(args.reference)
    request_msg = {
        "claim_file": claim,
        "docker_reference": args.reference,
        "image_name": image_name,
        "manifest_digest": args.manifest_digest,
        "request_id": request_id,
        "requested_by": args.requester,
        "sig_keyname": args.sig_key_name,
        "sig_key_id": args.sig_key_id,
    }
    return request_msg


def request_signature(args: Any) -> None:
    """
    Format and send out a UMB message to request signing, and retry as needed.
    """
    global umb
    umb = start_umb_client(
        hosts=[args.umb_url], client_name=args.umb_client_name, handler=UmbHandler()
    )
    global result_file
    result_file = args.output

    request_msg = gen_request_msg(args, umb.id)

    umb.connect_and_subscribe(args.umb_listen_topic)

    try:
        retry_count = 3
        for i in range(retry_count + 1):
            LOGGER.info(f"Sending signing request message...attempt #{i+1}")
            umb.send(args.umb_publish_topic, json.dumps(request_msg))

            wait_count = 0
            LOGGER.debug(f"Checking for signing response result file {result_file}...")
            while not os.path.exists(result_file):
                time.sleep(WAIT_INTERVAL_SEC)
                wait_count += 1
                if wait_count > TIMEOUT_COUNT:
                    LOGGER.warning("Timeout from waiting for signing response.")
                    break
            else:
                # exit retry loop if response file detected
                break

            LOGGER.info(f"No signing response received. Retrying.")
    finally:
        # unsubscribe to free up the queue
        LOGGER.info("Unsubscribing from queue and disconnecting from UMB...")
        umb.unsubscribe(args.umb_listen_topic)
        umb.stop()
        if not os.path.exists(result_file):
            LOGGER.error("No signing response received after all 3 retries.")
            sys.exit(1)


def main():  # pragma: no cover
    """
    Main func
    """

    parser = setup_argparser()
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(log_level)

    request_signature(args)


if __name__ == "__main__":  # pragma: no cover
    main()
