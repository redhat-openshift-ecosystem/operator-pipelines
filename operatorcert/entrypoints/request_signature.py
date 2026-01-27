"""Sign a container image using RADAS."""

import argparse
import base64
import json
import logging
import os
import sys
import threading
import time
import uuid
from typing import Any, Dict

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
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--manifest-digest",
        help="Manifest digest for the signed content, usually in the format sha256:xxx,"
        "separated by commas if there are multiple",
    )
    parser.add_argument(
        "--output",
        help="Path to an output file.",
        default="signing_response.json",
    )
    parser.add_argument(
        "--reference",
        help="Docker reference for the signed content, "
        "e.g. registry.redhat.io/redhat/community-operator-index:v4.9,"
        "separated by commas if there are multiple",
    )
    group.add_argument(
        "--blob",
        help="Blob that needs to be signed. Encoded in base64 format. "
        "Separated by commas if there are multiple",
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


REQUEST_IDS: Any = None

# wait for signing response for a total of 5 min, at 5 second intervals
TIMEOUT_COUNT = 60
WAIT_INTERVAL_SEC: float = 5


class UmbHandler(stomp.ConnectionListener):  # type: ignore  # pragma: no cover
    """
    UmbHandler class
    """

    def __init__(self, output_file: str) -> None:
        super().__init__()
        self.output_file = output_file

    def on_error(self, frame: Any) -> None:
        """
        On error callback

        Args:
            frame (Any): Message frame
        """
        LOGGER.error("Received an error frame:\n%s", frame.body)

    def on_message(self, frame: Any) -> None:
        """
        On message callback

        Args:
            frame (Any): Message frame
        """
        # handle response from radas in a thread
        thread = threading.Thread(
            target=process_message, args=[frame.body, self.output_file]
        )
        thread.start()

    def on_disconnected(self: Any) -> None:
        """
        On disconnected callback
        """
        LOGGER.error("Disconnected from umb.")


def process_message(msg: Any, output_file: str) -> None:
    """
    Process a message received from UMB.
    Args:
        msg: The message body received.
        output_file (str): Path to an output file.
    """
    msg = json.loads(msg)["msg"]

    msg_request_id = msg.get("request_id")
    if REQUEST_IDS and msg_request_id in REQUEST_IDS:
        LOGGER.info("Received radas response: %s", msg)

        result_file_path = f"{msg_request_id}-{output_file}"
        with open(result_file_path, "w", encoding="utf-8") as result_file_handler:
            json.dump(msg, result_file_handler)
        LOGGER.info(
            "Response from radas successfully received for request %s", msg_request_id
        )
        # Give some time for logs to be written to disk
        time.sleep(1)
        sys.exit(0)
    else:
        LOGGER.info("Ignored message from another request (%s)", msg_request_id)


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

    claim_b64 = base64.b64encode(json.dumps(claim).encode("utf-8"))
    return claim_b64.decode("utf-8")


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


def gen_request_msg(
    args: Any, digest: str, reference: str, request_id: str
) -> Dict[str, Any]:
    """
    Generate the request message to send to RADAS.
    Args:
        args: Args from script input.
        digest: Manifest digest for the signed content, usually in the format sha256:xxx
        reference: Docker reference for the signed content,
            e.g. registry.redhat.io/redhat/community-operator-index:v4.9
        request_id: UUID to identify match the request with RADAS's response.

    Returns:

    """
    claim = gen_sig_claim_file(reference, digest, args.requester)
    image_name = gen_image_name(reference)
    request_msg = {
        "claim_file": claim,
        "docker_reference": reference,
        "image_name": image_name,
        "manifest_digest": digest,
        "request_id": request_id,
        "requested_by": args.requester,
        "sig_keyname": args.sig_key_name,
        "sig_key_id": args.sig_key_id,
    }
    return request_msg


def gen_request_msg_blob(args: Any, blob: str, request_id: str) -> Dict[str, Any]:
    """
    Generate the request message to send to RADAS.
    Args:
        args: Args from script input.
        blob: Blob that needs to be signed.
        request_id: UUID to identify match the request with RADAS's response.

    Returns:

    """
    request_msg = {
        "artifact": blob,
        "request_id": request_id,
        "requested_by": args.requester,
        "sig_keyname": args.sig_key_name,
        "sig_key_id": args.sig_key_id,
    }
    return request_msg


def request_signature(  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    args: Any,
) -> None:
    """
    Format and send out a UMB message to request signing, and retry as needed.
    """

    output_file = args.output
    manifests = []
    references = []
    blobs = []

    # Fill the arrays for manifests and references, or blobs
    if args.manifest_digest is not None and args.reference is not None:
        manifests = args.manifest_digest.strip(",").split(",")
        references = args.reference.strip(",").split(",")

        if len(manifests) != len(references):
            LOGGER.error(
                "Manifest digest list does not match the length of reference list."
            )
            sys.exit(1)
    elif args.blob is not None:
        if args.reference is not None:
            LOGGER.warning(
                "When signing blobs, reference is not needed. It will be ignored."
            )
        blobs = args.blob.strip(",").split(",")
    else:
        LOGGER.error(
            "--reference is needed when --manifest-digest is used to sign images"
        )
        sys.exit(1)

    umb = start_umb_client(
        hosts=[args.umb_url],
        client_name=args.umb_client_name,
        handler=UmbHandler(output_file=output_file),
    )

    request_msgs = {}
    global REQUEST_IDS  # pylint: disable=global-statement
    REQUEST_IDS = set()

    if len(manifests) > 0:
        for manifest, reference in zip(manifests, references):
            request_id = str(uuid.uuid4())
            request_msgs[request_id] = gen_request_msg(
                args=args,
                digest=manifest,
                reference=reference,
                request_id=request_id,
            )
            REQUEST_IDS.add(request_id)
    else:
        for blob in blobs:
            request_id = str(uuid.uuid4())
            request_msgs[request_id] = gen_request_msg_blob(
                args=args,
                blob=blob,
                request_id=request_id,
            )
            REQUEST_IDS.add(request_id)

    umb.connect_and_subscribe(args.umb_listen_topic)

    results = []
    try:
        retry_count = 3
        for i in range(retry_count + 1):
            LOGGER.info(
                "Sending %s signing request messages...attempt #%s",
                len(REQUEST_IDS),
                i + 1,
            )
            for request_id in REQUEST_IDS:
                umb.send(args.umb_publish_topic, json.dumps(request_msgs[request_id]))

            wait_count = 0
            LOGGER.debug(
                "Checking for signing response result files with prefixes %s",
                REQUEST_IDS,
            )
            while len(REQUEST_IDS) != 0:
                wait_count += 1
                if wait_count > TIMEOUT_COUNT:
                    LOGGER.warning("Timeout from waiting for signing response.")
                    break

                time.sleep(WAIT_INTERVAL_SEC)

                sig_received = set()
                for request_id in REQUEST_IDS:
                    if os.path.exists(f"{request_id}-{output_file}"):
                        with open(
                            f"{request_id}-{output_file}", "r", encoding="utf-8"
                        ) as result_file_handler:
                            result_json = json.load(result_file_handler)
                            signing_status = result_json["signing_status"]
                            if signing_status == "success":
                                results.append(result_json)
                                sig_received.add(request_id)
                            elif signing_status == "failure":
                                LOGGER.error(
                                    "Signing failure received for request %s",
                                    request_id,
                                )
                            else:
                                LOGGER.warning(
                                    "Unknown signing status received for request %s: %s",
                                    request_id,
                                    signing_status,
                                )

                REQUEST_IDS = REQUEST_IDS - sig_received
            else:
                # exit retry loop if all response files detected
                break

            LOGGER.info("Not all successful signing responses received. Retrying.")
    finally:
        # unsubscribe to free up the queue
        LOGGER.info("Unsubscribing from queue and disconnecting from UMB...")
        umb.unsubscribe(args.umb_listen_topic)
        umb.stop()
        if REQUEST_IDS:
            LOGGER.error(
                "Missing signing responses after all 3 retries for %s", REQUEST_IDS
            )
            sys.exit(1)
        else:
            LOGGER.info("All signing responses received. Writing result to file...")
            with open(args.output, "w", encoding="utf-8") as results_file:
                json.dump(results, results_file)


def main() -> None:  # pragma: no cover
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
