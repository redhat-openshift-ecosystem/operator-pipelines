"""Module containing data classes and validators for PR parsed files"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

import yaml
from operator_repo import OperatorCatalog
from operator_repo import Repo as OperatorRepo


class ValidationError(Exception):
    """
    Exception raised when the result of the detect_changes function
    violates any of the constraints
    """


AffectedBundle = tuple[str, str]
AffectedOperator = str
AffectedCatalog = str
AffectedCatalogOperator = tuple[str, str]


@dataclass
class AffectedBundleCollection:
    """A collection of affected bundles"""

    added: set[AffectedBundle] = field(default_factory=set)
    modified: set[AffectedBundle] = field(default_factory=set)
    deleted: set[AffectedBundle] = field(default_factory=set)

    @property
    def union(self) -> set[AffectedBundle]:
        """All the affected bundles"""
        return self.added | self.modified | self.deleted

    def to_dict(self) -> Dict[str, Any]:
        """
        Dump the results to the dictionary

        Returns:
            Dict[str, Any]: A dictionary with the detected changes results
        """
        return {
            "affected_bundles": [f"{x}/{y}" for x, y in self.union],
            "added_bundles": [f"{x}/{y}" for x, y in self.added],
            "modified_bundles": [f"{x}/{y}" for x, y in self.modified],
            "deleted_bundles": [f"{x}/{y}" for x, y in self.deleted],
        }


@dataclass
class AffectedOperatorCollection:
    """A collection of affected operators"""

    added: set[AffectedOperator] = field(default_factory=set)
    modified: set[AffectedOperator] = field(default_factory=set)
    deleted: set[AffectedOperator] = field(default_factory=set)

    @property
    def union(self) -> set[AffectedOperator]:
        """All the affected operators"""
        return self.added | self.modified | self.deleted

    def to_dict(self) -> Dict[str, Any]:
        """
        Dump the results to the dictionary

        Returns:
            Dict[str, Any]: A dictionary with the detected changes results
        """
        return {
            "affected_operators": list(self.union),
            "added_operators": list(self.added),
            "modified_operators": list(self.modified),
            "deleted_operators": list(self.deleted),
        }


@dataclass
class AffectedCatalogOperatorCollection:
    """A collection of affected bundles"""

    added: set[AffectedCatalogOperator] = field(default_factory=set)
    modified: set[AffectedCatalogOperator] = field(default_factory=set)
    deleted: set[AffectedCatalogOperator] = field(default_factory=set)

    @property
    def union(self) -> set[AffectedCatalogOperator]:
        """All the affected bundles"""
        return self.added | self.modified | self.deleted

    @property
    def catalogs_with_added_or_modified_operators(self) -> set[str]:
        """Catalogs with added or modified operators"""
        return {catalog for catalog, _ in self.added | self.modified}

    def to_dict(self) -> Dict[str, Any]:
        """
        Dump the results to the dictionary

        Returns:
            Dict[str, Any]: A dictionary with the detected changes results
        """
        return {
            "affected_catalog_operators": [f"{x}/{y}" for x, y in self.union],
            "added_catalog_operators": [f"{x}/{y}" for x, y in self.added],
            "modified_catalog_operators": [f"{x}/{y}" for x, y in self.modified],
            "deleted_catalog_operators": [f"{x}/{y}" for x, y in self.deleted],
            "catalogs_with_added_or_modified_operators": list(
                self.catalogs_with_added_or_modified_operators
            ),
        }


@dataclass
class AffectedCatalogCollection:
    """A collection of affected operators"""

    added: set[AffectedCatalog] = field(default_factory=set)
    modified: set[AffectedCatalog] = field(default_factory=set)
    deleted: set[AffectedCatalog] = field(default_factory=set)

    @property
    def union(self) -> set[AffectedCatalog]:
        """All the affected operators"""
        return self.added | self.modified | self.deleted

    def to_dict(self) -> Dict[str, Any]:
        """
        Dump the results to the dictionary

        Returns:
            Dict[str, Any]: A dictionary with the detected changes results
        """
        return {
            "affected_catalogs": list(self.union),
            "added_catalogs": list(self.added),
            "modified_catalogs": list(self.modified),
            "deleted_catalogs": list(self.deleted),
            "added_or_modified_catalogs": list(self.added | self.modified),
        }


class ParserResults:
    """
    Data class to store the results of the detect_changes function
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        affected_operators: AffectedOperatorCollection,
        affected_bundles: AffectedBundleCollection,
        affected_catalogs: AffectedCatalogCollection,
        affected_catalog_operators: AffectedCatalogOperatorCollection,
        extra_files: set[str],
    ):
        self.affected_operators = affected_operators
        self.affected_bundles = affected_bundles
        self.affected_catalogs = affected_catalogs
        self.affected_catalog_operators = affected_catalog_operators
        self.extra_files = extra_files

    def to_dict(self) -> Dict[str, Any]:
        """
        Dump the results to the dictionary

        Returns:
            Dict[str, Any]: A dictionary with the detected changes results
        """
        result = {
            **(self.affected_operators.to_dict()),
            **(self.affected_bundles.to_dict()),
            **(self.affected_catalogs.to_dict()),
            **(self.affected_catalog_operators.to_dict()),
            "extra_files": list(self.extra_files),
        }
        self.enrich_result(result)
        return result

    @staticmethod
    def enrich_result(result: dict[str, Any]) -> None:
        """
        Enrich the result of the detect_changes function
        with additional fields

        Args:
            result: Dictionary with the detected changes
        """

        operator_name = ""
        bundle_version = ""

        affected_operators = result.get("affected_operators", [])
        affected_bundles = result.get("affected_bundles", [])
        affected_catalog_operators = result.get("affected_catalog_operators", [])

        if affected_operators:
            operator_name = affected_operators[0]

        if affected_bundles:
            _, bundle_version = affected_bundles[0].split("/")

        if affected_catalog_operators and operator_name == "":
            # Even if the change affects only files in catalogs/ we still need to know
            # what operator is affected by the change when accessing info in the operator's ci.yaml
            operator_name = affected_catalog_operators[0][1]

        result["operator_name"] = operator_name
        result["bundle_version"] = bundle_version

        result["operator_path"] = f"operators/{operator_name}" if operator_name else ""
        result["bundle_path"] = (
            f"operators/{operator_name}/{bundle_version}" if bundle_version else ""
        )


class ParserRules:
    """
    A set of rules tha defines an action of what can or can't be done
    when submitting a PR
    """

    def __init__(
        self, results: ParserResults, head_repo: OperatorRepo, base_rep: OperatorRepo
    ) -> None:
        self.object = results
        self.head_repo = head_repo
        self.base_repo = base_rep
        self.errors: List[str] = []

    def check_extra_files(self) -> None:
        """
        Check if there are any extra files in the PR outside of the operator
        """
        if len(self.object.extra_files) > 0:
            self.errors.append(
                f"The PR affects non-operator files: {sorted(self.object.extra_files)}"
            )

    def check_affected_operators(self) -> None:
        """
        The PR should affect at most one operator
        """
        if len(self.object.affected_operators.union) > 1:
            self.errors.append(
                "The PR affects more than one operator: "
                f"{sorted(self.object.affected_operators.union)}"
            )

    def check_modified_bundles(self) -> None:
        """
        Check if the PR modifies existing bundles
        """
        if len(self.object.affected_bundles.modified) > 0:
            self.errors.append(
                f"The PR modifies existing bundles: {sorted(self.object.affected_bundles.modified)}"
            )

    def _check_deleted_bundle_fbc(self) -> None:
        """
        Check if a deleted bundle has FBC enabled
        """
        operators = set()
        for operator_name, _ in self.object.affected_bundles.deleted:
            operators.add(operator_name)
        for operator_name in operators:
            operator = self.base_repo.operator(operator_name)
            if not operator.config.get("fbc", {}).get("enabled", False):
                self.errors.append(
                    f"The PR deletes an existing operator: {operator}. "
                    "This feature is only allowed for bundles with FBC enabled."
                )

    def _fetch_bundles_from_catalog_file(
        self, operator_catalog: OperatorCatalog
    ) -> list[Dict[str, Any]]:
        """
        Fetch bundles from the catalog file
        """
        catalog_content_path = operator_catalog.catalog_content_path
        with open(catalog_content_path, "r", encoding="utf-8") as catalog_file:
            yaml_content = yaml.safe_load_all(catalog_file)

            bundles = [
                item for item in yaml_content if item.get("schema") == "olm.bundle"
            ]
        return bundles

    def _check_deleted_bundle_used_in_catalog(self) -> None:
        """
        Check if a deleted bundle is used in a catalog
        """
        for operator_name, bundle_version in self.object.affected_bundles.deleted:
            operator = self.base_repo.operator(operator_name)
            bundle = operator.bundle(bundle_version)
            bundle_csv_full_name = bundle.csv["metadata"]["name"]

            # Check a current catalogs and find if there is a bundle that is in use
            all_catalogs = self.head_repo.all_catalogs()
            for catalog in all_catalogs:
                if not catalog.has(operator_name):
                    continue
                operator_catalog = catalog.operator_catalog(operator_name)
                bundles = self._fetch_bundles_from_catalog_file(operator_catalog)
                for catalog_bundle in bundles:
                    if catalog_bundle.get("name") == bundle_csv_full_name:
                        self.errors.append(
                            f"The PR deletes a bundle ({operator_name}/{bundle_version}) "
                            f"that is in use by a catalog ({catalog})"
                        )
                        break

    def check_deleted_bundles(self) -> None:
        """
        Check if the PR deletes any bundles and if so, check if delete is allowed
        """
        if len(self.object.affected_bundles.deleted) == 0:
            return
        self._check_deleted_bundle_fbc()
        self._check_deleted_bundle_used_in_catalog()

    def check_added_bundles(self) -> None:
        """
        Check if the PR adds any bundles and verify PR doesn't combine added
        and deleted bundles
        """
        if len(self.object.affected_bundles.added) > 1:
            self.errors.append(
                f"The PR affects more than one bundle: {sorted(self.object.affected_bundles.added)}"
            )
        if (
            len(self.object.affected_bundles.added) > 0
            and len(self.object.affected_bundles.deleted) > 0
        ):
            self.errors.append(
                "The PR adds and deletes bundles at the same time. "
                "This is not allowed. Please split the changes into 2 separate pull requests."
            )

    def check_affected_catalog_operators(self) -> None:
        """
        Check if the PR affects at most one catalog operator and PR doesn't contains
        catalog changes and operator changes
        """
        added_or_modified_bundles = (
            self.object.affected_bundles.added | self.object.affected_bundles.modified
        )
        if len(added_or_modified_bundles) > 0 and (
            len(self.object.affected_catalog_operators.union) > 0
        ):
            self.errors.append(
                f"The PR affects a bundle ({sorted(added_or_modified_bundles)}) and catalog "
                f"({sorted(self.object.affected_catalog_operators.union)}) at the same time. "
                "Split operator and catalog changes into 2 separate pull requests."
            )
        catalog_operators = sorted(
            list(
                {
                    operator[1]
                    for operator in self.object.affected_catalog_operators.union
                }
            )
        )
        if len(catalog_operators) > 1:
            self.errors.append(
                f"The PR affects more than one catalog operator: {catalog_operators}"
            )

    def validate(self) -> None:
        """
        Run a test suite to validate the changes
        A test suite is defined as a set of methods that start with "check_"

        Raises:
            ValidationError: Raise an exception if any of the checks fail
        """
        for check in dir(self):
            if check.startswith("check_") and callable(getattr(self, check)):
                getattr(self, check)()
        if self.errors:
            raise ValidationError("\n".join(self.errors))
