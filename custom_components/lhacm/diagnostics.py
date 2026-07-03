"""Diagnostics support for LHACM."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

REDACT_KEYS = {"token", "authorization", "private-token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for an LHACM config entry."""
    runtime = entry.runtime_data
    return {
        "entry": {
            "entry_id": entry.entry_id,
            "domain": entry.domain,
            "title": entry.title,
            "options": dict(entry.options),
        },
        "repositories": [
            {
                "key": repository.key,
                "provider": repository.ref.provider,
                "base_url": repository.ref.base_url,
                "full_name": repository.ref.full_name,
                "category": repository.category,
                "domain": repository.domain,
                "installed": repository.installed,
                "installed_version": repository.installed_version,
                "available_version": repository.available_version,
                "pending_update": repository.pending_update,
                "installed_path": repository.installed_path,
                "last_checked": repository.last_checked,
            }
            for repository in runtime.repositories.values()
        ],
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device,
) -> dict[str, Any]:
    """Return diagnostics for a repository device."""
    runtime = entry.runtime_data
    identifiers = {identifier[1] for identifier in device.identifiers if identifier[0] == DOMAIN}
    repositories = [
        repository
        for repository in runtime.repositories.values()
        if repository.key in identifiers
    ]
    return {
        "repositories": [
            {
                "key": repository.key,
                "full_name": repository.ref.full_name,
                "installed_version": repository.installed_version,
                "available_version": repository.available_version,
                "source_url": repository.source_url,
            }
            for repository in repositories
        ]
    }

