"""Websocket API for the LHACM frontend."""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
import voluptuous as vol

from .const import DOMAIN, RepositoryCategory
from .exceptions import LHACMError
from .models import ManagedRepository
from .repository_url import parse_repository_url


def async_setup(hass: HomeAssistant) -> None:
    """Register LHACM websocket commands."""
    websocket_api.async_register_command(hass, lhacm_info)
    websocket_api.async_register_command(hass, lhacm_repositories_list)
    websocket_api.async_register_command(hass, lhacm_repositories_add)
    websocket_api.async_register_command(hass, lhacm_repositories_remove)
    websocket_api.async_register_command(hass, lhacm_repositories_refresh)
    websocket_api.async_register_command(hass, lhacm_repository_download)
    websocket_api.async_register_command(hass, lhacm_repository_uninstall)


def _runtime(hass: HomeAssistant):
    entries = hass.data.get(DOMAIN, {})
    return next(iter(entries.values()))


@websocket_api.websocket_command({vol.Required("type"): "lhacm/info"})
@websocket_api.require_admin
@websocket_api.async_response
async def lhacm_info(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return LHACM info."""
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            {
                "categories": [category.value for category in RepositoryCategory],
                "disabled_reason": None,
            },
        )
    )


@websocket_api.websocket_command({vol.Required("type"): "lhacm/repositories/list"})
@websocket_api.require_admin
@websocket_api.async_response
async def lhacm_repositories_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List repositories."""
    runtime = _runtime(hass)
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            [_repository_payload(repo) for repo in runtime.repositories.values()],
        )
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "lhacm/repositories/add",
        vol.Required("repository"): str,
        vol.Required("category"): vol.In([category.value for category in RepositoryCategory]),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def lhacm_repositories_add(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add a custom repository."""
    runtime = _runtime(hass)
    try:
        ref = parse_repository_url(msg["repository"])
        repository = await runtime.validate_repository(ref, RepositoryCategory(msg["category"]))
        runtime.repositories[repository.key] = repository
        await runtime.store.async_save(runtime.repositories)
    except LHACMError as exception:
        connection.send_error(msg["id"], "repository_error", str(exception))
        return

    connection.send_message(websocket_api.result_message(msg["id"], _repository_payload(repository)))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "lhacm/repositories/remove",
        vol.Required("repository"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def lhacm_repositories_remove(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Remove a custom repository from LHACM."""
    runtime = _runtime(hass)
    repository = runtime.repositories.get(msg["repository"])
    if repository and repository.installed:
        manager = runtime.manager_for_ref(repository.ref)
        try:
            await manager.async_uninstall(repository)
        except LHACMError as exception:
            connection.send_error(msg["id"], "remove_error", str(exception))
            return
    runtime.repositories.pop(msg["repository"], None)
    await runtime.save()
    connection.send_message(websocket_api.result_message(msg["id"]))


@websocket_api.websocket_command({vol.Required("type"): "lhacm/repositories/refresh"})
@websocket_api.require_admin
@websocket_api.async_response
async def lhacm_repositories_refresh(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Refresh all repositories."""
    runtime = _runtime(hass)
    await runtime.refresh_all()
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            [_repository_payload(repo) for repo in runtime.repositories.values()],
        )
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "lhacm/repository/download",
        vol.Required("repository"): str,
        vol.Optional("version"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def lhacm_repository_download(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Download a repository."""
    runtime = _runtime(hass)
    repository = runtime.repositories.get(msg["repository"])
    if repository is None:
        connection.send_error(msg["id"], "repository_not_found", "Repository not found")
        return

    manager = runtime.manager_for_ref(repository.ref)
    try:
        repository = await manager.async_install(repository, ref=msg.get("version"))
        runtime.repositories[repository.key] = repository
        await runtime.save()
    except LHACMError as exception:
        connection.send_error(msg["id"], "download_error", str(exception))
        return

    connection.send_message(websocket_api.result_message(msg["id"], _repository_payload(repository)))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "lhacm/repository/uninstall",
        vol.Required("repository"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def lhacm_repository_uninstall(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Uninstall a repository but keep it in LHACM."""
    runtime = _runtime(hass)
    repository = runtime.repositories.get(msg["repository"])
    if repository is None:
        connection.send_error(msg["id"], "repository_not_found", "Repository not found")
        return

    manager = runtime.manager_for_ref(repository.ref)
    try:
        repository = await manager.async_uninstall(repository)
        runtime.repositories[repository.key] = repository
        await runtime.save()
    except LHACMError as exception:
        connection.send_error(msg["id"], "uninstall_error", str(exception))
        return

    connection.send_message(websocket_api.result_message(msg["id"], _repository_payload(repository)))


def _repository_payload(repository: ManagedRepository) -> dict[str, Any]:
    """Return frontend repository data with HACS-compatible field names."""
    return {
        "authors": [],
        "available_version": repository.available_version,
        "can_download": True,
        "category": repository.category.value,
        "config_flow": False,
        "country": [],
        "custom": repository.custom,
        "description": repository.description or "",
        "domain": repository.domain,
        "downloads": repository.downloads,
        "file_name": "",
        "full_name": repository.ref.full_name,
        "hide": False,
        "homeassistant": None,
        "id": repository.key,
        "installed_version": repository.installed_version or "",
        "installed": repository.installed,
        "last_updated": repository.last_updated or "",
        "local_path": "",
        "name": repository.display_name,
        "new": False,
        "pending_upgrade": repository.pending_update,
        "stars": repository.stars,
        "state": None,
        "status": repository.status,
        "topics": repository.topics,
        "source_url": repository.source_url or f"{repository.ref.base_url}/{repository.ref.full_name}",
    }
