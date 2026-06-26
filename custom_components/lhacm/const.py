"""Constants for LHACM."""

from __future__ import annotations

from enum import StrEnum

DOMAIN = "lhacm"
NAME = "Local Home Assistant Component Manager"
NAME_SHORT = "LHACM"
VERSION = "1.0.0"

CONF_PROVIDER = "provider"
CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"
CONF_VERIFY_SSL = "verify_ssl"
CONF_ACKNOWLEDGE_RISK = "acknowledge_risk"

STORE_REPOSITORIES = "repositories"


class ProviderType(StrEnum):
    """Supported source repository providers."""

    GITLAB = "gitlab"
    GITEA = "gitea"
    UNKNOWN = "unknown"


class RepositoryCategory(StrEnum):
    """Supported repository categories."""

    INTEGRATION = "integration"
    PLUGIN = "plugin"
    THEME = "theme"
    PYTHON_SCRIPT = "python_script"
    APPDAEMON = "appdaemon"
    TEMPLATE = "template"
