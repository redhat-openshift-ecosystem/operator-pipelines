"""
Schema of the integration tests configuration file
"""

from pathlib import Path
from typing import Optional, Type, TypeVar

from pydantic import BaseModel
from yaml import safe_load


class GitHubRepoConfig(BaseModel):
    """
    A GitHub repository
    """

    url: str
    token: Optional[str] = None
    ssh_key: Optional[Path] = None


class ContainerRegistryConfig(BaseModel):
    """
    A container registry
    """

    base_ref: str
    username: Optional[str] = None
    password: Optional[str] = None


class IIBConfig(BaseModel):
    """
    An IIB API endpoint
    """

    url: str
    keytab: Path


C = TypeVar("C", bound="Config")


class Config(BaseModel):
    """
    Root configuration object
    """

    # GitHub repo containing fixtures used by test cases
    fixtures_repository: GitHubRepoConfig
    # Main GitHub repo to be used by test cases. PRs submitted to this repo will trigger
    # the hosted pipeline
    operator_repository: GitHubRepoConfig
    # GitHub repo to submit PRs from
    contributor_repository: GitHubRepoConfig
    # Container registry where to store bundle and index images created by test cases
    bundle_registry: ContainerRegistryConfig
    # Container registry where to push the operator-pipeline image
    test_registry: ContainerRegistryConfig
    # The IIB instance to be used by integration tests
    iib: IIBConfig

    @classmethod
    def from_yaml(cls: Type[C], path: Path) -> C:
        """
        Parse a yaml configuration file

        Args:
            path: path to the configuration file

        Returns:
            the parsed configuration object
        """
        return cls(**safe_load(path.read_text()))
