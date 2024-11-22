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

    operator_repository: GitHubRepoConfig
    contributor_repository: GitHubRepoConfig
    bundle_registry: ContainerRegistryConfig
    test_registry: ContainerRegistryConfig
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
