"""A simple UMB client for the operator-certification pipeline."""

import logging
import os
import ssl
import sys
import uuid
from typing import Any, List

import stomp
from stomp import ConnectionListener

LOGGER = logging.getLogger("operator-cert")


class UmbClient:
    """
    A UMB client for sending and receiving messages from the UMB.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        hostnames: List[tuple[str, int]],
        cert_file: str,
        key_file: str,
        handler: ConnectionListener,
        umb_client_name: str,
    ):
        self.id = str(uuid.uuid4())  # pylint: disable=invalid-name
        self.umb_client_name = umb_client_name
        self.key_file = key_file
        self.cert_file = cert_file
        self.hostnames = hostnames
        self.handler = handler
        self.connection = stomp.Connection(
            keepalive=True,
            host_and_ports=self.hostnames,
            reconnect_attempts_max=5,
            heartbeats=(8000, 0),
        )
        self.connection.set_ssl(
            for_hosts=self.hostnames,
            ssl_version=ssl.PROTOCOL_TLSv1_2,
            key_file=self.key_file,
            cert_file=self.cert_file,
            cert_validator=None,
        )

        self.connection.set_listener("", self.handler)

    def connect_and_subscribe(self, destination: str) -> None:
        """
        Connect to UMB and subscribe to the given destination as a queue.
        Args:
            destination: Destination/topic to subscribe to.
        """
        if not self.connection.is_connected():
            LOGGER.info("Connecting to the UMB...")
            self.connection.connect(wait=True)

        destination = f"/queue/Consumer.{self.umb_client_name}.{self.id}.{destination}"
        self.connection.subscribe(
            destination=destination,
            id=self.id,
            ack="auto",
            headers={"activemq.prefetchSize": 1},
        )
        LOGGER.info("Subscribed to %s with id=%s", destination, self.id)

    def send(self, destination: str, message: str) -> None:
        """
        Send a message to the given destination.
        Args:
            destination: Destination/topic to send message to.
            message: Valid json string to send.
        """
        if not self.connection.is_connected():
            LOGGER.info("Connecting to the UMB...")
            self.connection.connect(wait=True)

        LOGGER.debug("Publishing to topic: /topic/%s", destination)
        LOGGER.info("Writing message to UMB: %s", message)
        self.connection.send(body=message, destination=f"/topic/{destination}")

    def stop(self) -> None:
        """
        Stop the UMB connection
        """
        self.connection.disconnect()

    def unsubscribe(self, destination: str) -> None:
        """
        Unsubscribe from the given destination.
        """
        destination = f"/queue/Consumer.{self.umb_client_name}.{self.id}.{destination}"
        self.connection.unsubscribe(destination=destination, id=self.id)


def start_umb_client(hosts: List[str], client_name: str, handler: Any) -> UmbClient:
    """
    Start the UMB message bus listener and return the instantiated client object.
    Args:
        hosts: UMB hosts to connect to.
        client_name: Client name to connect to UMB with. This should match the client
            name on the UMB cert.
        handler: The UMB handler to use for processing message or handling disconnects.
    """
    host_list = []

    for host in hosts:
        host_list.append((host, 61612))

    cert = os.environ.get("UMB_CERT_PATH")
    key = os.environ.get("UMB_KEY_PATH")

    if cert and key:
        if os.path.exists(cert) and os.path.exists(key):
            LOGGER.debug("umb listener session with cert + key is created.")

            umb_client = UmbClient(
                host_list,
                os.getenv("UMB_CERT_PATH") or "",
                os.getenv("UMB_KEY_PATH") or "",
                handler,
                client_name,
            )
            return umb_client
        LOGGER.error(
            "UMB_CERT_PATH or UMB_KEY_PATH does not point to a file that exists"
        )
        sys.exit(1)
    LOGGER.error(
        "No auth details provided for umb. Define UMB_CERT_PATH + UMB_KEY_PATH."
    )
    sys.exit(1)
