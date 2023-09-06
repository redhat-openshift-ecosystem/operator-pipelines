"""
    Utility functions to support the check_required_fields bundle check
"""

import binascii
import datetime
from base64 import b64decode
from typing import Any

from dateutil.parser import isoparse
from semver import Version

CAPABILITIES = [
    "Basic Install",
    "Seamless Upgrades",
    "Full Lifecycle",
    "Deep Insights",
    "Auto Pilot",
]

CATEGORIES = [
    "AI/Machine Learning",
    "Application Runtime",
    "Big Data",
    "Cloud Provider",
    "Developer Tools",
    "Database",
    "Drivers and plugins",
    "Integration & Delivery",
    "Logging & Tracing",
    "Modernization & Migration",
    "Monitoring",
    "Networking",
    "OpenShift Optional",
    "Security",
    "Storage",
    "Streaming & Messaging",
]


def validate_capabilities(value: Any) -> bool:
    """Return True if the value is a valid capability level"""
    if not isinstance(value, str):
        return False
    return value in CAPABILITIES


def validate_categories(value: Any) -> bool:
    """
    Return True if the value is a valid comma separated list of
    operator categories
    """
    return all(x.strip() in CATEGORIES for x in str(value).split(","))


def validate_timestamp(value: Any) -> bool:
    """Return True if the value is a valid timestamp"""
    if isinstance(value, datetime.datetime):
        # the yaml parser seems to be smart enough to parse timestamps
        # on the fly
        return True
    try:
        _ = isoparse(str(value))
        return True
    except ValueError:
        return False


def validate_semver(value: Any) -> bool:
    """Return True if the value is semver compliant"""
    try:
        _ = Version.parse(value)
        return True
    except (ValueError, TypeError):
        return False


def validate_list_of_dicts(value: Any, fields: dict[str, type]) -> bool:
    """
    Return True if the value is a list of dicts and all entries in the
    list respect the given schema.
    The schema is a dict mapping the field name to its expected type.
    Extra fields are allowed.
    The length of the list is *not* checked, therefore an empty list
    will always return True.
    """
    # must be a list
    if not isinstance(value, list):
        return False
    for item in value:
        # each item must be a dict
        if not isinstance(item, dict):
            return False
        # and must have the required keys
        if not set(fields.keys()).issubset(item.keys()):
            return False
        # and all the value types must match
        for field_name, expected_type in fields.items():
            if not isinstance(item[field_name], expected_type):
                return False
    return True


def validate_icon(value: Any) -> bool:
    """Return True if the value is a valid list of icons"""
    # must be a list of dicts with "base64data" and "mediatype"
    if not validate_list_of_dicts(value, {"base64data": str, "mediatype": str}):
        return False
    if len(value) < 1:
        return False
    for icon in value:
        # base64data must contain valid base64 data
        if len(icon["base64data"]) < 4:
            return False
        try:
            _ = b64decode(icon["base64data"], validate=True)
        except binascii.Error:
            return False
        # mediatype must be a supported image format
        if icon["mediatype"] not in {
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/svg+xml",
        }:
            return False
    return True


def validate_maintainers(value: Any) -> bool:
    """Return True if the value is a list of maintainers"""
    # must be a list of dicts with "name" and "email"
    if not validate_list_of_dicts(value, {"name": str, "email": str}):
        return False
    return len(value) > 0


def validate_links(value: Any) -> bool:
    """Return True if the value is a list of links"""
    # must be a list of dicts with "name" and "links"
    if not validate_list_of_dicts(value, {"name": str, "url": str}):
        return False
    return len(value) > 0


def validate_list_of_strings(value: Any) -> bool:
    """Return True if the value is a list of strings"""
    if not isinstance(value, list):
        return False
    if not all(isinstance(x, str) for x in value):
        return False
    return len(value) > 0
