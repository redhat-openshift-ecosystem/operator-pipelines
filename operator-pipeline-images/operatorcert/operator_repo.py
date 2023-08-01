"""
    This module defines classes to simplify handling of repositories
    containing kubernetes operator bundles
"""

import logging
from functools import cached_property, total_ordering
from pathlib import Path
from typing import Any, Iterator, Union, Dict, List

import yaml
from semver import Version

log = logging.getLogger(__name__)


def _find_yaml(path: Path) -> Path:
    """Look for yaml files with alternate extensions"""

    if path.is_file():
        return path
    tries = [path]
    for alt_extension in [".yaml", ".yml"]:
        if alt_extension == path.suffix:
            continue
        new_path = path.with_suffix(alt_extension)
        if new_path.is_file():
            return new_path
        tries.append(new_path)
    tries_str = ", ".join([str(x) for x in tries])
    raise FileNotFoundError(f"Can't find yaml file. Tried: {tries_str}")


def _load_yaml_strict(path: Path) -> Any:
    """Returns the parsed contents of the YAML file at the given path"""

    log.debug("Loading %s", path)
    with path.open("r") as yaml_file:
        return yaml.safe_load(yaml_file)


def load_yaml(path: Path) -> Any:
    """Same as _load_yaml_strict but tries both .yaml and .yml extensions"""
    return _load_yaml_strict(_find_yaml(path))


class OperatorRepoException(Exception):
    """Base exception class"""


class InvalidRepoException(OperatorRepoException):
    """Error caused by an invalid repository structure"""


class InvalidOperatorException(OperatorRepoException):
    """Error caused by an invalid operator"""


class InvalidBundleException(OperatorRepoException):
    """Error caused by an invalid bundle"""


@total_ordering
class Bundle:
    """
    An operator bundle as specified in
    https://github.com/operator-framework/operator-registry/blob/master/docs/design/operator-bundle.md
    """

    METADATA_DIR = "metadata"
    MANIFESTS_DIR = "manifests"

    def __init__(self, bundle_path: Union[str, Path]):
        log.debug("Loading bundle at %s", bundle_path)
        self._bundle_path = Path(bundle_path)
        if not self.probe(self._bundle_path):
            raise InvalidBundleException(f"Not a valid bundle: {bundle_path}")
        self.operator_version = self._bundle_path.name
        self.operator_name = self._bundle_path.parent.name
        try:
            csv_full_name = self.csv["metadata"]["name"]
            self.csv_operator_name, self.csv_operator_version = csv_full_name.split(
                ".", 1
            )
        except ValueError as exc:
            raise InvalidBundleException(
                f"Invalid .metadata.name in CSV for {self}"
            ) from exc
        except (KeyError, TypeError) as exc:
            raise InvalidBundleException(f"Invalid CSV contents for {self}") from exc

    @cached_property
    def annotations(self) -> Dict[str, Any]:
        """
        :return: The content of the "annotations" field in metadata/annotations.yaml
        """
        return self.load_metadata("annotations.yaml").get("annotations", {})

    @cached_property
    def dependencies(self) -> List[Any]:
        """
        :return: The content of the "dependencies" field in metadata/dependencies.yaml
        """
        return self.load_metadata("dependencies.yaml").get("dependencies", [])

    @cached_property
    def csv(self) -> Dict[str, Any]:
        """
        :return: The content of the CSV file for the bundle
        """
        return load_yaml(self.csv_file_name)

    @classmethod
    def probe(cls, path: Path) -> bool:
        """
        :return: True if path looks like a bundle
        """
        return (
            path.is_dir()
            and (path / cls.MANIFESTS_DIR).is_dir()
            and (path / cls.METADATA_DIR).is_dir()
        )

    def root(self) -> str:
        """
        :return: The path to the root of the bundle
        """
        return str(self._bundle_path)

    def operator(self) -> "Operator":
        """
        :return: The operator the bundle belongs to
        """
        return Operator(self._bundle_path.parent)

    def load_metadata(self, filename: str) -> Dict[str, Any]:
        """
        Load and parse a yaml file from the metadata directory of the bundle
        :param filename: Name of the file
        :return: The parsed content of the file
        """
        try:
            return load_yaml(self._bundle_path / self.METADATA_DIR / filename)
        except FileNotFoundError:
            return {}

    @cached_property
    def csv_file_name(self) -> Path:
        """
        :return: The path of the CSV file for the bundle
        """
        for file_path in (self._bundle_path / self.MANIFESTS_DIR).iterdir():
            if file_path.is_file() and any(
                file_path.name.endswith(x)
                for x in [".clusterserviceversion.yaml", ".clusterserviceversion.yml"]
            ):
                return file_path
        raise InvalidBundleException(
            f"CSV file for {self.operator_name}/{self.operator_version} not found"
        )

    def __eq__(self, other: "Bundle") -> bool:
        if self.csv_operator_name != other.csv_operator_name:
            return False
        try:
            # First, try to interpret bundle version as semver
            return Version.parse(
                self.csv_operator_version.lstrip("v")
            ) == Version.parse(other.csv_operator_version.lstrip("v"))
        except ValueError:
            log.warning(
                "Cannot compare %s and %s as semver: falling back to string comparison",
                self,
                other,
            )
            return self.csv_operator_version == other.csv_operator_version

    def __ne__(self, other: "Bundle") -> bool:
        return not self == other

    def __lt__(self, other: "Bundle") -> bool:
        if self.csv_operator_name != other.csv_operator_name:
            raise ValueError("Can't compare bundles from different operators")
        try:
            # First, try to interpret bundle version as semver
            return Version.parse(self.csv_operator_version.lstrip("v")) < Version.parse(
                other.csv_operator_version.lstrip("v")
            )
        except ValueError:
            log.warning(
                "Cannot compare %s and %s as semver: falling back to string comparison",
                self,
                other,
            )
            return self.csv_operator_version < other.csv_operator_version

    def __hash__(self):
        return hash((self.operator_name, self.operator_version))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.operator_name}/{self.operator_version})"
        )


@total_ordering
class Operator:
    """An operator containing a collection of bundles"""

    def __init__(self, operator_path: Union[str, Path]):
        log.debug("Loading operator at %s", operator_path)
        self._operator_path = Path(operator_path)
        if not self.probe(self._operator_path):
            raise InvalidOperatorException(f"Not a valid operator: {operator_path}")
        self.operator_name = self._operator_path.name

    @cached_property
    def config(self) -> Any:
        """
        :return: The contents of the ci.yaml for the operator
        """
        try:
            return load_yaml(self._operator_path / "ci.yaml")
        except FileNotFoundError:
            log.info("No ci.yaml found for %s", self)
            return {}

    @classmethod
    def probe(cls, path: Path) -> bool:
        """
        :return: True if path looks like an operator
        """
        return path.is_dir() and any(Bundle.probe(x) for x in path.iterdir())

    def root(self) -> str:
        """
        :return: The path to the root of the operator
        """
        return str(self._operator_path)

    def all_bundles(self) -> Iterator[Bundle]:
        """
        :return: All the bundles for the operator
        """
        for version_path in self._operator_path.iterdir():
            if Bundle.probe(version_path):
                yield self.bundle(version_path.name)

    def bundle_path(self, operator_version: str) -> Path:
        """
        Return the path where a bundle for the given version
        would be located
        :param operator_version: Version of the bundle
        :return: Path to the bundle
        """
        return self._operator_path / operator_version

    def bundle(self, operator_version: str) -> Bundle:
        """
        Load the bundle for the given version
        :param operator_version: Version of the bundle
        :return: The loaded bundle
        """
        return Bundle(self.bundle_path(operator_version))

    def has(self, operator_version: str) -> bool:
        """
        Check if the operator has a bundle for the given version
        :param operator_version: Version to check for
        :return: True if the operator contains a bundle for such version
        """
        return Bundle.probe(self.bundle_path(operator_version))

    def __eq__(self, other: "Operator") -> bool:
        return self.operator_name == other.operator_name

    def __ne__(self, other: "Operator") -> bool:
        return self.operator_name != other.operator_name

    def __lt__(self, other: "Operator") -> bool:
        return self.operator_name < other.operator_name

    def __iter__(self) -> Iterator[Bundle]:
        yield from self.all_bundles()

    def __hash__(self):
        return hash((self.operator_name,))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.operator_name})"


class Repo:
    """A repository containing a collection of operators"""

    OPERATORS_DIR = "operators"

    def __init__(self, repo_path: Union[str, Path]):
        log.debug("Loading repo at %s", repo_path)
        self._repo_path = Path(repo_path)
        if not self.probe(self._repo_path):
            raise InvalidRepoException(f"Not a valid operator repository: {repo_path}")
        self._operators_path = self._repo_path / self.OPERATORS_DIR

    @cached_property
    def config(self) -> Any:
        """
        :return: The contents of the ci/pipeline-config.yaml for the repo
        """
        try:
            return load_yaml(self._repo_path / "ci" / "pipeline-config.yaml")
        except FileNotFoundError:
            log.warning("No ci/pipeline-config.yaml found for %s", self)
            return {}

    @classmethod
    def probe(cls, path: Path) -> bool:
        """
        :return: True if path looks like an operator repo
        """
        return path.is_dir() and (path / cls.OPERATORS_DIR).is_dir()

    def root(self) -> str:
        """
        :return: The path to the root of the repository
        """
        return str(self._repo_path)

    def all_operators(self) -> Iterator[Operator]:
        """
        :return: All the operators in the repo
        """
        for operator_path in self._operators_path.iterdir():
            if Operator.probe(operator_path):
                yield self.operator(operator_path.name)

    def operator_path(self, operator_name: str) -> Path:
        """
        Return the path where an operator with the given
        name would be located
        :param operator_name: Name of the operator
        :return: Path to the operator
        """
        return self._operators_path / operator_name

    def operator(self, operator_name: str) -> Operator:
        """
        Load the operator with the given name
        :param operator_name: Name of the operator
        :return: The loaded operator
        """
        return Operator(self.operator_path(operator_name))

    def has(self, operator_name: str) -> bool:
        """
        Check if the repo contains an operator with the given name
        :param operator_name: Name of the operator to look for
        :return: True if the repo contains an operator with the given name
        """
        return Operator.probe(self.operator_path(operator_name))

    def __iter__(self) -> Iterator[Operator]:
        yield from self.all_operators()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._repo_path})"
