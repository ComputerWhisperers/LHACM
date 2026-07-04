"""Constants for LHACM."""

from __future__ import annotations

from enum import StrEnum

DOMAIN = "lhacm"
NAME = "Local Home Assistant Component Manager"
NAME_SHORT = "LHACM"
VERSION = "1.0.8"

CONF_ACKNOWLEDGE_RISK = "acknowledge_risk"
CONF_SIDEPANEL_TITLE = "sidepanel_title"
CONF_SIDEPANEL_ICON = "sidepanel_icon"
CONF_APPDAEMON_DISCOVERY = "appdaemon_discovery"

DEFAULT_SIDEPANEL_TITLE = "LHACM"
DEFAULT_SIDEPANEL_ICON = "mdi:store-cog"

STORE_REPOSITORIES = "repositories"
SIGNAL_REPOSITORIES_UPDATED = f"{DOMAIN}_repositories_updated"


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
