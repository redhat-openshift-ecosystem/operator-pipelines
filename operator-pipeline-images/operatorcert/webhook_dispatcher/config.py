"""A module for configuration models."""

import os
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration settings."""

    url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://user:password@localhost:5432/webhook_dispatcher",
        )
    )
    echo: bool = Field(default=False)
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)


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


class DispatcherConfigItem(BaseModel):
    """Configuration for a webhook dispatcher item."""

    name: str
    events: List[str]
    full_repository_name: str
    callback_url: str
    capacity: CapacityConfig


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
