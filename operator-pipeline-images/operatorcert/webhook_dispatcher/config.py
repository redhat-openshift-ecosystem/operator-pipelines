"""A module for configuration models."""

import os
from typing import Any, List, Optional
from urllib.parse import quote_plus

import celpy
import celpy.celparser
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatabaseConfig(BaseModel):
    """Database configuration settings."""

    db_user: str = Field(default_factory=lambda: os.getenv("POSTGRESQL_USER") or "")
    db_password: str = Field(
        default_factory=lambda: os.getenv("POSTGRESQL_PASSWORD") or ""
    )
    db_host: str = Field(default_factory=lambda: os.getenv("POSTGRESQL_HOST") or "")
    db_port: str = Field(default_factory=lambda: os.getenv("POSTGRESQL_PORT") or "")
    db_name: str = Field(default_factory=lambda: os.getenv("POSTGRESQL_DATABASE") or "")

    echo: bool = Field(default=False)
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)

    @property
    def url(self) -> str:
        """
        Get the database URL using the individual parameters or the DATABASE_URL
        environment variable.

        Returns:
            str: The database URL.
        """
        # A user can set the DATABASE_URL or provide the individual parameters
        default_url = (
            f"postgresql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )
        env_url = os.getenv("DATABASE_URL", default_url)
        return env_url


class SecurityConfig(BaseModel):
    """Security configuration for webhook validation."""

    github_webhook_secret: Optional[str] = Field(
        default_factory=lambda: os.getenv("GITHUB_WEBHOOK_SECRET")
    )
    verify_signatures: bool = Field(default=True)
    allowed_github_events: List[str] = Field(default=["pull_request"])


class CapacityConfig(BaseModel):
    """Capacity configuration."""

    type: str
    pipeline_name: str
    max_capacity: int
    namespace: str


class Filter(BaseModel):
    """Filter configuration for webhook events."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    cel_expression: celpy.Expression[Any] | None = Field(
        default=None,
        description="CEL expression to filter events. "
        "If empty, no filtering is applied.",
    )

    @field_validator("cel_expression", mode="before")
    @classmethod
    def validate_cel_expression_and_compile(
        cls, value: str
    ) -> celpy.Expression[Any] | None:
        """
        Validate and parse the CEL expression syntax.

        Raise ValueError if the expression is invalid.

        Args:
            value (celpy.Expression[Any] | None): A parsed cel expression if
            available or None.
        """
        if not value:
            return None

        try:
            env = celpy.Environment()
            ast = env.compile(value)
            return ast
        except celpy.celparser.CELParseError as e:
            raise ValueError(f"Invalid CEL expression: {e}") from e


class DispatcherConfigItem(BaseModel):
    """Configuration for a webhook dispatcher item."""

    name: str
    events: List[str]
    full_repository_name: str
    callback_url: str
    capacity: CapacityConfig
    filter: Optional[Filter] = None


class DispatcherConfig(BaseModel):
    """Configuration for the webhook dispatcher items."""

    items: List[DispatcherConfigItem]


class WebhookDispatcherConfig(BaseModel):
    """Configuration for the webhook dispatcher."""

    dispatcher: DispatcherConfig
    security: SecurityConfig


def load_config(file_path: str) -> WebhookDispatcherConfig:
    """
    Load the webhook dispatcher configuration from a JSON file.

    Args:
        file_path (str): Path to the configuration file.

    Returns:
        WebhookDispatcherConfig: Parsed configuration object.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        yaml_data = yaml.safe_load(file)

    return WebhookDispatcherConfig(**yaml_data)
