"""
Definition of Repo, Operator, Bundle, Catalog and CatalogOperator classes
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property, total_ordering
from pathlib import Path
from typing import Any, Optional, SupportsIndex, Union

from semantic_version import NpmSpec, Version

from .exceptions import (
    InvalidBundleException,
    InvalidCatalogException,
    InvalidOperatorCatalogException,
    InvalidOperatorException,
    InvalidRepoException,
)
from .utils import load_multidoc_yaml, load_yaml

log = logging.getLogger(__name__)


@total_ordering
class Bundle:
    """
    An operator bundle as specified in
    https://github.com/operator-framework/operator-registry/blob/master/docs/design/operator-bundle.md
    """

    METADATA_DIR = "metadata"
    MANIFESTS_DIR = "manifests"

    def __init__(
        self, bundle_path: Union[str, Path], operator: Optional["Operator"] = None
    ):
        log.debug("Loading bundle at %s", bundle_path)
        self._bundle_path = Path(bundle_path).resolve()
        if not self.probe(self._bundle_path):
            raise InvalidBundleException(f"Not a valid bundle: {self._bundle_path}")
        self.operator_version = self._bundle_path.name
        self.operator_name = self._bundle_path.parent.name
        self._manifests_path = self._bundle_path / self.MANIFESTS_DIR
        self._metadata_path = self._bundle_path / self.METADATA_DIR
        self._parent = operator

    @cached_property
    def annotations(self) -> dict[str, Any]:
        """
        :return: The content of the "annotations" field in metadata/annotations.yaml
        """
        return self.load_metadata("annotations.yaml").get("annotations", {}) or {}

    @cached_property
    def dependencies(self) -> list[Any]:
        """
        :return: The content of the "dependencies" field in metadata/dependencies.yaml
        """
        return self.load_metadata("dependencies.yaml").get("dependencies", []) or []

    @cached_property
    def csv(self) -> dict[str, Any]:
        """
        :return: The content of the CSV file for the bundle
        """
        csv = load_yaml(self.csv_file_name)
        if not isinstance(csv, dict):
            raise InvalidBundleException(f"Invalid CSV contents ({self.csv_file_name})")
        return csv

    @cached_property
    def release_config(self) -> Any:
        """
        :return: The content of the "release-config.yaml" file in the bundle directory
        """
        path = self._bundle_path / "release-config.yaml"
        if not path.is_file():
            return None
        return load_yaml(path)

    @property
    def metadata_operator_name(self) -> str:
        """
        :return: The operator name as defined in the annotations file
        """
        return str(
            self.annotations.get("operators.operatorframework.io.bundle.package.v1", "")
        )

    @cached_property
    def csv_full_name(self) -> tuple[str, str]:
        """
        :return: A tuple containing operator name and bundle version
        extracted from the bundle's csv file
        """
        try:
            csv_full_name = self.csv["metadata"]["name"]
            name, version = csv_full_name.split(".", 1)
            return name, version.lstrip("v")
        except (KeyError, ValueError) as exc:
            raise InvalidBundleException(
                f"CSV for {self} has invalid .metadata.name"
            ) from exc

    @property
    def csv_operator_name(self) -> str:
        """
        :return: The operator name from the csv file
        """
        name, _ = self.csv_full_name
        return name

    @property
    def csv_operator_version(self) -> str:
        """
        :return: The bundle version from the csv file
        """
        _, version = self.csv_full_name
        return version

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

    @property
    def root(self) -> Path:
        """
        :return: The path to the root of the bundle
        """
        return self._bundle_path

    @property
    def operator(self) -> "Operator":
        """
        :return: The Operator object the bundle belongs to
        """
        if self._parent is None:
            self._parent = Operator(self._bundle_path.parent)
        return self._parent

    def load_metadata(self, filename: str) -> dict[str, Any]:
        """
        Load and parse a yaml file from the metadata directory of the bundle
        :param filename: Name of the file
        :return: The parsed content of the file
        """
        try:
            content = load_yaml(self._metadata_path / filename)
            if not isinstance(content, dict):
                if content is None:
                    return {}
                raise InvalidBundleException(f"Invalid {filename} contents")
            return content
        except FileNotFoundError:
            return {}

    @cached_property
    def csv_file_name(self) -> Path:
        """
        :return: The path of the CSV file for the bundle
        """
        for suffix in ["yaml", "yml"]:
            try:
                return next(
                    self._manifests_path.glob(f"*.clusterserviceversion.{suffix}")
                )
            except StopIteration:
                continue
        raise InvalidBundleException(
            f"CSV file for {self.operator_name}/{self.operator_version} not found"
        )

    @property
    def channels(self) -> set[str]:
        """
        :return: Set of channels the bundle belongs to
        """
        try:
            return {
                x.strip()
                for x in self.annotations[
                    "operators.operatorframework.io.bundle.channels.v1"
                ].split(",")
            }
        except KeyError:
            return set()

    @property
    def default_channel(self) -> Optional[str]:
        """
        :return: Default channel for the bundle
        """
        try:
            return str(
                self.annotations[
                    "operators.operatorframework.io.bundle.channel.default.v1"
                ]
            ).strip()
        except KeyError:
            return None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        if self.csv_operator_name != other.csv_operator_name:
            return False
        try:
            return Version(  # type: ignore
                self.csv_operator_version.lstrip("v")
            ) == Version(other.csv_operator_version.lstrip("v"))
        except ValueError:
            log.warning(
                "Can't compare bundle versions %s and %s as semver: using lexical order instead",
                self,
                other,
            )
            return self.csv_operator_version == other.csv_operator_version

    def __ne__(self, other: Any) -> bool:
        return not self == other

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"< not supported between instances of '{self.__class__.__name__}'"
                f" and '{other.__class__.__name__}"
            )
        if self.csv_operator_name != other.csv_operator_name:
            return self.csv_operator_name < other.csv_operator_name
        try:
            return Version(self.csv_operator_version.lstrip("v")) < Version(  # type: ignore
                other.csv_operator_version.lstrip("v")
            )
        except ValueError:
            log.warning(
                "Can't compare bundle versions %s and %s as semver: using lexical order instead",
                self,
                other,
            )
            return self.csv_operator_version < other.csv_operator_version

    def __hash__(self) -> int:
        return hash((self.operator_name, self.operator_version))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.operator_name}/{self.operator_version})"
        )


@total_ordering
class Operator:
    """An operator containing a collection of bundles"""

    _bundle_cache: dict[str, Bundle]

    CONFIG_FILE = "ci.yaml"

    def __init__(self, operator_path: Union[str, Path], repo: Optional["Repo"] = None):
        log.debug("Loading operator at %s", operator_path)
        self._operator_path = Path(operator_path).resolve()
        if not self.probe(self._operator_path):
            raise InvalidOperatorException(
                f"Not a valid operator: {self._operator_path}"
            )
        self.operator_name = self._operator_path.name
        self._parent = repo
        self._bundle_cache = {}

    @cached_property
    def config(self) -> Any:
        """
        :return: The contents of the ci.yaml for the operator
        """
        try:
            return load_yaml(self._operator_path / self.CONFIG_FILE)
        except FileNotFoundError:
            log.info("No ci.yaml found for %s", self)
            return {}

    @classmethod
    def probe(cls, path: Path) -> bool:
        """
        :return: True if path looks like an operator
        """
        return path.is_dir() and (
            # At least one bundle or a ci.yaml file is required to consider
            # a directory an operator
            any(Bundle.probe(x) for x in path.iterdir())
            or (path / cls.CONFIG_FILE).is_file()
        )

    @property
    def root(self) -> Path:
        """
        :return: The path to the root of the operator
        """
        return self._operator_path

    @property
    def repo(self) -> "Repo":
        """
        :return: The Repo object the operator belongs to
        """
        if self._parent is None:
            self._parent = Repo(self._operator_path.parent.parent)
        return self._parent

    def all_catalogs(self) -> Iterator["Catalog"]:
        """
        :return: All the catalogs containing the operator
        """
        for catalog in self.repo.all_catalogs():
            if catalog.has(self.operator_name):
                yield catalog

    def all_operator_catalogs(self) -> Iterator["OperatorCatalog"]:
        """
        :return: All operator catalogs
        """
        for catalog in self.repo.all_catalogs():
            if catalog.has(self.operator_name):
                yield catalog.operator_catalog(self.operator_name)

    def all_bundles(self) -> Iterator[Bundle]:
        """
        :return: All the bundles for the operator
        """
        for version_path in self._operator_path.iterdir():
            try:
                yield self._bundle_cache[version_path.name]
            except KeyError:
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
        try:
            return self._bundle_cache[operator_version]
        except KeyError:
            bundle = Bundle(self.bundle_path(operator_version), self)
            self._bundle_cache[operator_version] = bundle
            return bundle

    def has(self, operator_version: str) -> bool:
        """
        Check if the operator has a bundle for the given version
        :param operator_version: Version to check for
        :return: True if the operator contains a bundle for such version
        """
        return operator_version in self._bundle_cache or Bundle.probe(
            self.bundle_path(operator_version)
        )

    @cached_property
    def channels(self) -> set[str]:
        """
        :return: All channels defined by the operator bundles
        """
        return {x for y in self.all_bundles() for x in y.channels}

    @cached_property
    def default_channel(self) -> Optional[str]:
        """
        :return: Default channel as defined in
        https://github.com/operator-framework/operator-registry/blob/master/docs/design/opm-tooling.md
        """
        # The default channel for an operator is defined as the default
        # channel of the highest bundle version
        try:
            version_channel_pairs: list[tuple[Union[str, Version], str]] = [
                (
                    Version(x.csv_operator_version),
                    x.default_channel,
                )
                for x in self.all_bundles()
                if x.default_channel is not None
            ]
        except ValueError:
            log.warning(
                "%s has bundles with non-semver compliant version:"
                " using lexical order to determine default channel",
                self,
            )
            version_channel_pairs = [
                (
                    x.csv_operator_version,
                    x.default_channel,
                )
                for x in self.all_bundles()
                if x.default_channel is not None
            ]
        try:
            return sorted(version_channel_pairs)[-1][1]
        except IndexError:
            return None

    def channel_bundles(self, channel: str) -> list[Bundle]:
        """
        :param channel: Name of the channel
        :return: List of bundles in the given channel
        """
        return sorted({x for x in self.all_bundles() if channel in x.channels})

    def head(self, channel: str) -> Optional[Bundle]:
        """
        :param channel: Name of the channel
        :return: Head of the channel
        """
        channel_bundles = self.channel_bundles(channel)
        return None if not channel_bundles else channel_bundles[-1]

    @staticmethod
    def _resolve_skip_range(
        channel: str, all_bundles_set: set[Bundle]
    ) -> dict[Bundle, set[Bundle]]:
        """
        Partially resolve the update graph according to field
        'metadata'.'annotations'.'olm.skipRange'.
        """
        edges: dict[Bundle, set[Bundle]] = {}
        version_to_bundle = {x.csv_operator_version: x for x in all_bundles_set}
        for bundle in all_bundles_set:
            if (
                skip_range := bundle.csv.get("metadata", {})
                .get("annotations", {})
                .get("olm.skipRange")
            ):
                try:
                    skip_range_parsed = NpmSpec(skip_range)
                except ValueError:
                    log.warning("Invalid skipRange: '%s' is ignored.", skip_range)
                else:
                    for (
                        bundle_version,
                        potentially_replaced_bundle,
                    ) in version_to_bundle.items():
                        if (
                            Version(bundle_version) in skip_range_parsed
                            and channel in bundle.channels
                            and channel in potentially_replaced_bundle.channels
                        ):
                            edges.setdefault(potentially_replaced_bundle, set()).add(
                                bundle
                            )
        return edges

    @staticmethod
    def _replaces_graph(
        channel: str, bundles: list[Bundle]
    ) -> dict[Bundle, set[Bundle]]:
        all_bundles_set = set(bundles)
        edges: dict[Bundle, set[Bundle]] = Operator._resolve_skip_range(
            channel, all_bundles_set
        )
        version_to_bundle = {x.csv_operator_version: x for x in all_bundles_set}
        for bundle in all_bundles_set:
            spec = bundle.csv.get("spec", {})
            replaces = spec.get("replaces")
            skips = spec.get("skips", [])
            previous = set(skips) | {replaces}
            for replaced_bundle_name in previous:
                if replaced_bundle_name is None:
                    continue
                if "." not in replaced_bundle_name:
                    raise ValueError(
                        f"{bundle} has invalid 'replaces' field: '{replaced_bundle_name}'"
                    )
                replaced_bundle_version = replaced_bundle_name.split(".", 1)[1]
                try:
                    replaced_bundle = version_to_bundle[
                        replaced_bundle_version.lstrip("v")
                    ]
                    if (
                        channel in bundle.channels
                        and channel in replaced_bundle.channels
                    ):
                        edges.setdefault(replaced_bundle, set()).add(bundle)
                except KeyError:
                    pass
        return edges

    def update_graph(self, channel: str) -> dict[Bundle, set[Bundle]]:
        """
        Return the update graph for the given channel
        :param channel: Name of the channel
        :return: Update graph edges in the form of a dictionary mapping each bundle
            to a set of bundles that can replace it
        """
        all_bundles = self.channel_bundles(channel)
        update_strategy = self.config.get("updateGraph", "replaces-mode")
        if update_strategy == "semver-mode":
            return {x: {y} for x, y in zip(all_bundles, all_bundles[1:])}
        if update_strategy == "replaces-mode":
            return self._replaces_graph(channel, all_bundles)
        raise NotImplementedError(
            f"{self}: unsupported updateGraph value: {update_strategy}"
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.operator_name == other.operator_name

    def __ne__(self, other: Any) -> bool:
        return not self == other

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Can't compare {self.__class__.__name__} to {other.__class__.__name__}"
            )
        return self.operator_name < other.operator_name

    def __iter__(self) -> Iterator[Bundle]:
        yield from self.all_bundles()

    def __hash__(self) -> int:
        return hash((self.operator_name,))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.operator_name})"


class OperatorCatalog:
    """
    Operator catalog class representing a File Based Catalog for given operator
    """

    CATALOG_NAMES = ("catalog.yaml", "catalog.yml", "catalog.json")

    def __init__(
        self,
        operator_catalog_path: Union[str, Path],
        catalog: Optional["Catalog"] = None,
    ):
        log.debug("Loading operator catalog at %s", operator_catalog_path)
        self._operator_catalog_path = Path(operator_catalog_path).resolve()
        if not self.probe(self._operator_catalog_path):
            raise InvalidOperatorCatalogException(
                f"Not a valid operator catalog: {self._operator_catalog_path}"
            )
        self.operator_name = self._operator_catalog_path.name
        self._parent = catalog

    @classmethod
    def probe(cls, path: Path) -> bool:
        """
        :return: True if path looks like an operator catalog
        """
        if not path.is_dir():
            return False
        file_names = {file.name for file in path.iterdir()}
        return path.is_dir() and bool(file_names & set(cls.CATALOG_NAMES))

    @property
    def root(self) -> Path:
        """
        :return: The path to the root of the operator catalog
        """
        return self._operator_catalog_path

    @property
    def repo(self) -> "Repo":
        """
        :return: The Repo object the operator belongs to
        """
        return self.catalog.repo

    @property
    def catalog(self) -> "Catalog":
        """
        :return: The Catalog object the operator belongs to
        """
        if self._parent is None:
            self._parent = Catalog(self._operator_catalog_path.parent)
        return self._parent

    @property
    def operator(self) -> "Operator":
        """
        :return: The Operator object the operator catalog belongs to
        """
        return self.repo.operator(self.operator_name)

    @property
    def operator_catalog_name(self) -> str:
        """
        :return: The operator catalog name combining the catalog name
            and the operator name eg.: 'v4.12/operator-x'
        """
        return self.catalog.catalog_name + "/" + self.operator_name

    @property
    def catalog_content_path(
        self,
    ) -> Path:
        """
        Return the path where a catalog with the given
        name would be located
        :param catalog_name: Name of the catalog
        :return: Path to the catalog
        """
        file_names = {file.name for file in self._operator_catalog_path.iterdir()}
        catalog_name = file_names & set(self.CATALOG_NAMES)
        return self._operator_catalog_path / list(catalog_name)[0]

    @property
    def catalog_content(self) -> list[dict[str, Any]]:
        """
        Return the catalog content.

        Catalog is represented as a multi document yaml file,
        therefore the content is represented as a list of dictionaries
        where each dictionary represents single document in the yaml file.

        :return: The list of dictionaries representing the catalog content
        """
        return load_multidoc_yaml(self.catalog_content_path)

    def get_catalog_bundles(self) -> list[Any]:
        """
        Get all object with schema olm.bundle from the catalog content

        Returns:
            list[Any]: List of all bundles in the catalog
        """
        content = self.catalog_content
        bundles = []
        for item in content:
            if item.get("schema") == "olm.bundle":
                bundles.append(item)
        return bundles

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.operator_catalog_name == other
        if not isinstance(other, self.__class__):
            return False
        return self.operator_catalog_name == other.operator_catalog_name

    def __ne__(self, other: Any) -> bool:
        return not self == other

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Can't compare {self.__class__.__name__} to {other.__class__.__name__}"
            )
        return self.operator_catalog_name < other.operator_catalog_name

    def __hash__(self) -> int:
        return hash((self.operator_catalog_name,))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.operator_catalog_name})"


@dataclass
class OperatorCatalogList(list[OperatorCatalog]):
    """
    A list of operator catalogs
    """

    def __init__(self, operator_catalogs: Optional[list[OperatorCatalog]] = None):
        if operator_catalogs is None:
            operator_catalogs = []
        if any(not isinstance(item, OperatorCatalog) for item in operator_catalogs):
            raise TypeError("All items must be instances of OperatorCatalog")
        super().__init__(list(set(operator_catalogs)))  # only unique items

    def append(self, item: Any) -> None:
        if not isinstance(item, OperatorCatalog):
            raise TypeError(
                f"Only instances of OperatorCatalog are allowed, got {type(item).__name__}"
            )
        if item in self:
            raise ValueError(f"Duplicate items are not allowed: {item}")
        super().append(item)

    def extend(self, items: Any) -> None:
        if any(not isinstance(item, OperatorCatalog) for item in items):
            raise TypeError("All items must be instances of OperatorCatalog")
        if any(item in self for item in items):
            raise ValueError("Duplicate items are not allowed")
        super().extend(items)

    def insert(self, index: SupportsIndex, item: Any) -> None:
        if not isinstance(item, OperatorCatalog):
            raise TypeError(
                f"Only instances of OperatorCatalog are allowed, got {type(item).__name__}"
            )
        if item in self:
            raise ValueError(f"Duplicate items are not allowed: {item}")
        super().insert(index, item)

    def __repr__(self) -> str:
        return f"{list(self.__iter__())}"


class Catalog:
    """
    Catalog class representing a File Based Catalog of specific version.
    A Repo can contain multiple Catalogs: for example one Catalog per OpenShift version.
    An Operator can be published to one or more of the Catalogs of the
    Repo it belongs to.
    """

    CATALOG_DIR = "catalogs"

    def __init__(self, catalog_path: Union[str, Path], repo: Optional["Repo"] = None):
        log.debug("Loading catalog at %s", catalog_path)
        self._catalog_path = Path(catalog_path).resolve()
        if not self.probe(self._catalog_path):
            raise InvalidCatalogException(f"Not a valid catalog: {self._catalog_path}")
        self.catalog_name = self._catalog_path.name
        self._parent = repo
        self._operator_catalog_cache: dict[str, OperatorCatalog] = {}

    @classmethod
    def probe(cls, path: Path) -> bool:
        """
        :return: True if path looks like an catalog
        """
        return path.is_dir() and any(OperatorCatalog.probe(x) for x in path.iterdir())

    @property
    def root(self) -> Path:
        """
        :return: The path to the root of the catalog
        """
        return self._catalog_path

    @property
    def repo(self) -> "Repo":
        """
        :return: The Repo object the operator belongs to
        """
        if self._parent is None:
            self._parent = Repo(self._catalog_path.parent.parent)
        return self._parent

    def all_operator_catalogs(self) -> Iterator[OperatorCatalog]:
        """
        :return: All the operator catalogs in the catalog
        """
        for operator_catalog_path in self._catalog_path.iterdir():
            try:
                yield self._operator_catalog_cache[operator_catalog_path.name]
            except KeyError:
                if OperatorCatalog.probe(operator_catalog_path):
                    yield self.operator_catalog(operator_catalog_path.name)

    def operator_catalog_path(self, operator_name: str) -> Path:
        """
        Return the path where an operator catalog with the given
        name would be located
        :param operator_name: Name of the operator
        :return: Path to the operator catalog
        """
        return self._catalog_path / operator_name

    def operator_catalog(self, operator_name: str) -> OperatorCatalog:
        """
        Load the operator catalog with the given name
        :param operator_name: Name of the operator
        :return: The loaded operator catalog
        """
        try:
            return self._operator_catalog_cache[operator_name]
        except KeyError:
            operator_catalog = OperatorCatalog(
                self.operator_catalog_path(operator_name), self
            )
            self._operator_catalog_cache[operator_name] = operator_catalog
            return operator_catalog

    def has(self, operator_name: str) -> bool:
        """
        Check if the catalog contains an operatorcatalog with the given name
        :param operator_name: Name of the operator to look for
        :return: True if the repo contains an operator with the given name
        """
        return operator_name in self._operator_catalog_cache or OperatorCatalog.probe(
            self.operator_catalog_path(operator_name)
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.catalog_name == other.catalog_name

    def __ne__(self, other: Any) -> bool:
        return not self == other

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Can't compare {self.__class__.__name__} to {other.__class__.__name__}"
            )
        return self.catalog_name < other.catalog_name

    def __iter__(self) -> Iterator[OperatorCatalog]:
        yield from self.all_operator_catalogs()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.catalog_name})"


class Repo:
    """A repository containing a collection of operators"""

    _operator_cache: dict[str, Operator]
    _catalog_cache: dict[str, Catalog]

    OPERATORS_DIR = "operators"
    CATALOGS_DIR = "catalogs"

    def __init__(self, repo_path: Union[str, Path]):
        log.debug("Loading repo at %s", repo_path)
        self._repo_path = Path(repo_path).resolve()
        if not self.probe(self._repo_path):
            raise InvalidRepoException(
                f"Not a valid operator repository: {self._repo_path}"
            )
        self._operators_path = self._repo_path / self.OPERATORS_DIR
        self._catalogs_path = self._repo_path / self.CATALOGS_DIR

        self._operator_cache = {}
        self._catalog_cache = {}

    @cached_property
    def config(self) -> Any:
        """
        :return: The contents of the config.yaml for the repo
        """
        try:
            return load_yaml(self._repo_path / "config.yaml")
        except FileNotFoundError:
            log.warning("No config.yaml found for %s", self)
            return {}

    @classmethod
    def probe(cls, path: Path) -> bool:
        """
        :return: True if path looks like an operator repo
        """
        return path.is_dir() and (path / cls.OPERATORS_DIR).is_dir()

    @property
    def root(self) -> Path:
        """
        :return: The path to the root of the repository
        """
        return self._repo_path

    def all_catalogs(self) -> Iterator[Catalog]:
        """
        :return: All the catalogs in the repo
        """
        if not self._catalogs_path.is_dir():
            return
        for catalog_path in self._catalogs_path.iterdir():
            try:
                yield self._catalog_cache[catalog_path.name]
            except KeyError:
                if Catalog.probe(catalog_path):
                    yield self.catalog(catalog_path.name)
                else:
                    print(f"Catalog {catalog_path.name} is not valid")

    def catalog_path(self, catalog_name: str) -> Path:
        """
        Return the path where a catalog with the given
        name would be located
        :param catalog_name: Name of the catalog
        :return: Path to the catalog
        """
        return self._catalogs_path / catalog_name

    def catalog(self, catalog_name: str) -> Catalog:
        """
        Load the catalog with the given name
        :param catalog_name: Name of the catalog
        :return: The loaded catalog
        """
        try:
            return self._catalog_cache[catalog_name]
        except KeyError:
            catalog = Catalog(self.catalog_path(catalog_name), self)
            self._catalog_cache[catalog_name] = catalog
            return catalog

    def all_operators(self) -> Iterator[Operator]:
        """
        :return: All the operators in the repo
        """
        for operator_path in self._operators_path.iterdir():
            try:
                yield self._operator_cache[operator_path.name]
            except KeyError:
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
        try:
            return self._operator_cache[operator_name]
        except KeyError:
            operator = Operator(self.operator_path(operator_name), self)
            self._operator_cache[operator_name] = operator
            return operator

    def has(self, operator_name: str) -> bool:
        """
        Check if the repo contains an operator with the given name
        :param operator_name: Name of the operator to look for
        :return: True if the repo contains an operator with the given name
        """
        return operator_name in self._operator_cache or Operator.probe(
            self.operator_path(operator_name)
        )

    def has_catalog(self, catalog_name: str) -> bool:
        """
        Check if the repo contains a catalog with the given name
        :param catalog_name: Name of the catalog to look for
        :return: True if the repo contains a catalog with the given name
        """
        return catalog_name in self._catalog_cache or Catalog.probe(
            self.catalog_path(catalog_name)
        )

    def __iter__(self) -> Iterator[Operator]:
        yield from self.all_operators()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._repo_path == other._repo_path

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._repo_path})"
