"""A module for working with bundle images."""

import json
import logging
import os
import shutil
import tempfile
from typing import Any, Optional

import yaml
from operatorcert import utils

LOGGER = logging.getLogger("operator-cert")


class BundleImage:
    """
    A class representing a bundle image. The class provides methods to work with
    the bundle image content.
    """

    def __init__(
        self, image_pullspec: str, auth_file_path: Optional[str] = None
    ) -> None:
        self.image_pullspec = image_pullspec
        self.auth_file_path = auth_file_path

        self._inspect_data: dict[str, Any] = {}
        self._content_path = ""

    def __str__(self) -> str:
        """
        A string representation of the bundle image pull spec.

        Returns:
            str: A bundle image pull spec.
        """
        return self.image_pullspec

    def __repr__(self) -> str:
        """
        A representation of a BundleImage object.

        Returns:
            str: A representation of a BundleImage object.
        """
        return f"BundleImage({self.image_pullspec})"

    def __del__(self) -> None:
        """
        A method to clean up the content path.
        """
        if not self._content_path:
            return
        if os.path.exists(self._content_path):
            shutil.rmtree(self._content_path, ignore_errors=True)

    @property
    def content_path(self) -> str:
        """
        A property to get the content path of the bundle image. The content path is
        a directory where the bundle image content is extracted.

        Returns:
            str: A path to the content directory.
        """
        if not self._content_path:
            # Create a temporary directory and copy and extract the image
            self._content_path = tempfile.mkdtemp()
            self._copy_and_extract_image()
        return self._content_path

    def _copy_and_extract_image(self) -> None:
        """
        A method to copy and extract the bundle image content to a local temporary
        directory.
        """
        # Copy the image to the content path and extract the content
        # only if the content path is not set.
        self._copy_image()
        self._extract_content()

    @property
    def inspect_data(self) -> dict[str, Any]:
        """
        A property to get the inspect data of the bundle image. The inspect data
        is a dictionary with the image metadata retrieved using the `skopeo inspect`

        Returns:
            dict[str, Any]: A dictionary with the image metadata.
        """
        if not self._inspect_data:
            command = [
                "skopeo",
                "inspect",
                "--no-tags",
                f"docker://{self.image_pullspec}",
            ]
            if self.auth_file_path:
                command.extend(["--authfile", self.auth_file_path])

            output = utils.run_command(command)
            self._inspect_data = json.loads(output.stdout.decode("utf-8"))
        return self._inspect_data

    def _copy_image(self) -> None:
        """
        A method to copy the bundle image to a local directory using the `skopeo copy`
        """
        command = [
            "skopeo",
            "copy",
            f"docker://{self.image_pullspec}",
            f"dir:{self.content_path}",
        ]
        if self.auth_file_path:
            command.extend(["--authfile", self.auth_file_path])

        utils.run_command(command, retries=5)

    def _extract_content(self) -> None:
        """
        A method to extract the bundle image content to the content path. The method
        extracts the content of the first layer of the image. Bundle images should
        have just one layer wchich contains the bundle content including metadata
        adn manifests.
        """
        # there should be just one layer in the bundle image
        layer_to_extract = self.manifest_file.get("layers")[0].get("digest")
        layer_to_extract = layer_to_extract.removeprefix("sha256:")
        command = [
            "tar",
            "-xvf",
            os.path.join(self.content_path, layer_to_extract),
        ]
        utils.run_command(command, cwd=self.content_path)

    @property
    def labels(self) -> dict[str, str]:
        """
        A property to get the labels of the bundle image.

        Returns:
            dict[str, str]: A dictionary with the image labels.
        """
        return self.inspect_data.get("Labels", {}) or {}

    @property
    def annotations(self) -> Any:
        """
        A property to get the annotations of the bundle image.

        Returns:
            Any: A dictionary with the image annotations.
        """
        return yaml.safe_load(self.get_bundle_file("metadata/annotations.yaml"))

    @property
    def manifest_file(self) -> Any:
        """
        A property to get the manifest.json file of the bundle image.

        Returns:
            Any: A json loaded manifest file.
        """
        with open(
            os.path.join(self.content_path, "manifest.json"), encoding="utf8"
        ) as f:
            manifest = json.load(f)
        return manifest

    @property
    def config(self) -> Any:
        """
        A property to get the config file of the bundle image.

        Returns:
            Any: A dictionary with the config file content.
        """
        config_file_name = self.manifest_file.get("config", {}).get("digest")
        config_file_name = config_file_name.removeprefix("sha256:")
        with open(
            os.path.join(self.content_path, config_file_name), encoding="utf8"
        ) as f:
            config = json.load(f)
        return config

    def get_bundle_file(self, file_name: str) -> str:
        """
        A method to get any file given by argument from the bundle image content.

        Args:
            file_name (str): A name of the file to get from the bundle image content.

        Returns:
            str: A content of the file as a string.
        """
        with open(os.path.join(self.content_path, file_name), encoding="utf8") as f:
            return f.read()

    def get_csv_file(self) -> Optional[str]:
        """
        A method to get the ClusterServiceVersion file from the bundle image content.

        Returns:
            Optional[str]: A content of the ClusterServiceVersion file as a string.
        """
        for file_name in os.listdir(os.path.join(self.content_path, "manifests")):
            csv_files_extensions = [
                "clusterserviceversion.yaml",
                "clusterserviceversion.yml",
            ]
            if file_name.endswith(tuple(csv_files_extensions)):
                return self.get_bundle_file(os.path.join("manifests", file_name))
        return None
