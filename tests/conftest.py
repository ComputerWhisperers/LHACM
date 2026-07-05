"""Test stubs for optional Home Assistant imports."""

from __future__ import annotations

import sys
import types
from datetime import UTC, datetime


def _install_homeassistant_stubs() -> None:
    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    frontend = types.ModuleType("homeassistant.components.frontend")
    http = types.ModuleType("homeassistant.components.http")
    persistent_notification = types.ModuleType("homeassistant.components.persistent_notification")
    websocket_api = types.ModuleType("homeassistant.components.websocket_api")
    config_entries = types.ModuleType("homeassistant.config_entries")
    const = types.ModuleType("homeassistant.const")
    core = types.ModuleType("homeassistant.core")
    dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    helpers = types.ModuleType("homeassistant.helpers")
    issue_registry = types.ModuleType("homeassistant.helpers.issue_registry")
    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")
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

    class StaticPathConfig:
        """Minimal StaticPathConfig stub."""

        def __init__(self, *_args, **_kwargs) -> None:
            pass

    class Platform:
        """Minimal Platform stub."""

        UPDATE = "update"

    def passthrough_decorator(*_args, **_kwargs):
        """Return a decorator that leaves websocket handlers unchanged."""

        def decorator(func):
            return func

        return decorator

    config_entries.ConfigEntry = ConfigEntry
    const.Platform = Platform
    core.HomeAssistant = HomeAssistant
    core.ServiceCall = ServiceCall
    core.callback = lambda func: func
    frontend.async_register_built_in_panel = lambda *_args, **_kwargs: None
    frontend.async_remove_panel = lambda *_args, **_kwargs: None
    http.StaticPathConfig = StaticPathConfig
    persistent_notification.async_dismiss = lambda *_args, **_kwargs: None
    issue_registry.IssueSeverity = types.SimpleNamespace(WARNING="warning")
    issue_registry.async_create_issue = lambda *_args, **_kwargs: None
    helpers.issue_registry = issue_registry
    websocket_api.ActiveConnection = object
    websocket_api.async_register_command = lambda *_args, **_kwargs: None
    websocket_api.async_response = lambda func: func
    websocket_api.require_admin = lambda func: func
    websocket_api.result_message = lambda msg_id, result=None: {"id": msg_id, "result": result}
    websocket_api.websocket_command = passthrough_decorator
    aiohttp_client.async_get_clientsession = lambda _hass: None
    storage.Store = Store
    dispatcher.async_dispatcher_send = lambda *_args, **_kwargs: None
    dt.utcnow = lambda: datetime.now(UTC)

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.components", components)
    sys.modules.setdefault("homeassistant.components.frontend", frontend)
    sys.modules.setdefault("homeassistant.components.http", http)
    sys.modules.setdefault(
        "homeassistant.components.persistent_notification",
        persistent_notification,
    )
    sys.modules.setdefault("homeassistant.components.websocket_api", websocket_api)
    sys.modules.setdefault("homeassistant.config_entries", config_entries)
    sys.modules.setdefault("homeassistant.const", const)
    sys.modules.setdefault("homeassistant.core", core)
    sys.modules.setdefault("homeassistant.helpers", helpers)
    sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aiohttp_client)
    sys.modules.setdefault("homeassistant.helpers.dispatcher", dispatcher)
    sys.modules.setdefault("homeassistant.helpers.issue_registry", issue_registry)
    sys.modules.setdefault("homeassistant.helpers.storage", storage)
    sys.modules.setdefault("homeassistant.util", util)
    sys.modules.setdefault("homeassistant.util.dt", dt)


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
