"""Test stubs for optional Home Assistant imports."""

from __future__ import annotations

import sys
import types


def _install_homeassistant_stubs() -> None:
    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    storage = types.ModuleType("homeassistant.helpers.storage")

    class ConfigEntry:
        """Minimal ConfigEntry stub."""

    class HomeAssistant:
        """Minimal HomeAssistant stub."""

    class ServiceCall:
        """Minimal ServiceCall stub."""

    class Store:
        """Minimal Store stub."""

        def __init__(self, *_args, **_kwargs) -> None:
            pass

    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    core.ServiceCall = ServiceCall
    aiohttp_client.async_get_clientsession = lambda _hass: None
    storage.Store = Store

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.config_entries", config_entries)
    sys.modules.setdefault("homeassistant.core", core)
    sys.modules.setdefault("homeassistant.helpers", helpers)
    sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aiohttp_client)
    sys.modules.setdefault("homeassistant.helpers.storage", storage)


def _install_dependency_stubs() -> None:
    aiohttp = types.ModuleType("aiohttp")
    voluptuous = types.ModuleType("voluptuous")

    class ClientResponse:
        """Minimal ClientResponse stub."""

    class ClientSession:
        """Minimal ClientSession stub."""

    class ClientTimeout:
        """Minimal ClientTimeout stub."""

        def __init__(self, *_args, **_kwargs) -> None:
            pass

    class Schema:
        """Minimal voluptuous Schema stub."""

        def __init__(self, schema) -> None:
            self.schema = schema

    aiohttp.ClientResponse = ClientResponse
    aiohttp.ClientSession = ClientSession
    aiohttp.ClientTimeout = ClientTimeout
    voluptuous.Schema = Schema
    voluptuous.Required = lambda key, default=None: key
    voluptuous.Optional = lambda key, default=None: key
    voluptuous.In = lambda options: options

    sys.modules.setdefault("aiohttp", aiohttp)
    sys.modules.setdefault("voluptuous", voluptuous)


_install_homeassistant_stubs()
_install_dependency_stubs()
