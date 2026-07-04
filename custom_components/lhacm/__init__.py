"""Local Home Assistant Component Manager integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import aiohttp_client
import voluptuous as vol

from .const import (
    CONF_SIDEPANEL_ICON,
    CONF_SIDEPANEL_TITLE,
    DEFAULT_SIDEPANEL_ICON,
    DEFAULT_SIDEPANEL_TITLE,
    DOMAIN,
    ProviderType,
    RepositoryCategory,
    SIGNAL_REPOSITORIES_UPDATED,
    VERSION,
)
from .exceptions import LHACMError
from .models import ManagedRepository, RepositoryRef
from .provider import create_provider
from .repository import RepositoryManager
from .repository_url import parse_repository_url, provider_config_for_repository
from .store import RepositoryStore
from .websocket import async_setup as async_setup_websocket

LOGGER = logging.getLogger(__name__)

type LHACMConfigEntry = ConfigEntry[LHACMRuntime]

PLATFORMS = [Platform.UPDATE]


@dataclass
class LHACMRuntime:
    """Runtime state for LHACM."""

    store: RepositoryStore
    session: object
    hass: HomeAssistant
    repositories: dict[str, ManagedRepository] = field(default_factory=dict)

    def manager_for_ref(self, ref: RepositoryRef) -> RepositoryManager:
        """Create a repository manager for a repository reference."""
        provider = create_provider(provider_config_for_repository(ref), self.session)
        return RepositoryManager(self.hass, provider)

    async def validate_repository(
        self,
        ref: RepositoryRef,
        category: RepositoryCategory,
    ) -> ManagedRepository:
        """Validate a repository, probing unknown local hosts as GitLab then Gitea."""
        return await _validate_repository(self.hass, self, ref, category)

    async def save(self) -> None:
        """Persist repositories and notify listeners."""
        await self.store.async_save(self.repositories)
        async_dispatcher_send(self.hass, SIGNAL_REPOSITORIES_UPDATED)

    async def refresh_repository(self, repository: ManagedRepository) -> ManagedRepository:
        """Refresh a repository from its provider."""
        manager = self.manager_for_ref(repository.ref)
        refreshed = await manager.async_refresh(repository)
        self.repositories[refreshed.key] = refreshed
        await self.save()
        return refreshed

    async def refresh_all(self) -> None:
        """Refresh all known repositories."""
        for repository in list(self.repositories.values()):
            try:
                await self.refresh_repository(repository)
            except LHACMError as exception:
                LOGGER.warning("Could not refresh %s: %s", repository.ref.full_name, exception)


ADD_REPOSITORY_SCHEMA = vol.Schema(
    {
        vol.Required("repository"): str,
        vol.Optional("category", default=RepositoryCategory.INTEGRATION): vol.In(
            [category.value for category in RepositoryCategory]
        ),
    }
)

INSTALL_REPOSITORY_SCHEMA = vol.Schema(
    {
        vol.Required("repository"): str,
        vol.Optional("ref"): str,
    }
)

REPOSITORY_KEY_SCHEMA = vol.Schema({vol.Required("repository"): str})


async def async_setup_entry(hass: HomeAssistant, entry: LHACMConfigEntry) -> bool:
    """Set up LHACM from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    store = RepositoryStore(hass)
    runtime = LHACMRuntime(
        store=store,
        session=session,
        hass=hass,
        repositories=await store.async_load(),
    )
    entry.runtime_data = runtime
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    async def add_repository(call: ServiceCall) -> None:
        ref = parse_repository_url(call.data["repository"])
        category = RepositoryCategory(call.data["category"])
        repository = await _validate_repository(hass, runtime, ref, category)
        runtime.repositories[repository.key] = repository
        await runtime.save()
        LOGGER.info("Added %s repository %s", category, repository.ref.full_name)

    async def install_repository(call: ServiceCall) -> None:
        ref = parse_repository_url(call.data["repository"])
        repository = runtime.repositories.get(ref.provider_key)
        if repository is None:
            repository = await _validate_repository(
                hass,
                runtime,
                ref,
                RepositoryCategory.INTEGRATION,
            )
        manager = _manager_for_ref(hass, runtime, repository.ref)
        repository = await manager.async_install(repository, ref=call.data.get("ref"))
        runtime.repositories[repository.key] = repository
        await runtime.save()
        LOGGER.info("Installed repository %s", ref.full_name)

    async def uninstall_repository(call: ServiceCall) -> None:
        repository = runtime.repositories[call.data["repository"]]
        manager = runtime.manager_for_ref(repository.ref)
        repository = await manager.async_uninstall(repository)
        runtime.repositories[repository.key] = repository
        await runtime.save()
        LOGGER.info("Uninstalled repository %s", repository.ref.full_name)

    async def remove_repository(call: ServiceCall) -> None:
        repository = runtime.repositories.get(call.data["repository"])
        if repository and repository.installed:
            manager = runtime.manager_for_ref(repository.ref)
            await manager.async_uninstall(repository)
        runtime.repositories.pop(call.data["repository"], None)
        await runtime.save()

    async def refresh_repositories(_call: ServiceCall) -> None:
        await runtime.refresh_all()

    hass.services.async_register(
        DOMAIN,
        "add_repository",
        add_repository,
        schema=ADD_REPOSITORY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "install_repository",
        install_repository,
        schema=INSTALL_REPOSITORY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "uninstall_repository",
        uninstall_repository,
        schema=REPOSITORY_KEY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "remove_repository",
        remove_repository,
        schema=REPOSITORY_KEY_SCHEMA,
    )
    hass.services.async_register(DOMAIN, "refresh", refresh_repositories)
    await _async_register_frontend(hass, entry)
    async_setup_websocket(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LHACMConfigEntry) -> bool:
    """Unload LHACM."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, "add_repository")
        hass.services.async_remove(DOMAIN, "install_repository")
        hass.services.async_remove(DOMAIN, "uninstall_repository")
        hass.services.async_remove(DOMAIN, "remove_repository")
        hass.services.async_remove(DOMAIN, "refresh")
        frontend.async_remove_panel(hass, DOMAIN)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: LHACMConfigEntry) -> None:
    """Reload LHACM when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _manager_for_ref(
    hass: HomeAssistant,
    runtime: LHACMRuntime,
    ref: RepositoryRef,
) -> RepositoryManager:
    provider = create_provider(provider_config_for_repository(ref), runtime.session)
    return RepositoryManager(hass, provider)


async def _async_register_frontend(hass: HomeAssistant, entry: LHACMConfigEntry) -> None:
    panel_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"/{DOMAIN}_frontend",
                str(panel_path),
                cache_headers=False,
            )
        ]
    )
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=entry.options.get(CONF_SIDEPANEL_TITLE, DEFAULT_SIDEPANEL_TITLE),
        sidebar_icon=entry.options.get(CONF_SIDEPANEL_ICON, DEFAULT_SIDEPANEL_ICON),
        frontend_url_path=DOMAIN,
        config={
            "_panel_custom": {
                "name": "lhacm-panel",
                "module_url": f"/{DOMAIN}_frontend/lhacm-panel.js?v={VERSION}",
                "embed_iframe": False,
                "trust_external": False,
            }
        },
        require_admin=True,
    )


async def _validate_repository(
    hass: HomeAssistant,
    runtime: LHACMRuntime,
    ref: RepositoryRef,
    category: RepositoryCategory,
) -> ManagedRepository:
    errors: list[str] = []
    for candidate in _candidate_refs(ref):
        manager = _manager_for_ref(hass, runtime, candidate)
        try:
            return await manager.async_validate(candidate, category)
        except LHACMError as exception:
            errors.append(f"{candidate.provider}: {exception}")
    raise LHACMError("; ".join(errors) or "Repository could not be validated")


def _candidate_refs(ref: RepositoryRef) -> list[RepositoryRef]:
    if ref.provider != ProviderType.UNKNOWN:
        return [ref]
    return [
        RepositoryRef(
            provider=provider,
            base_url=ref.base_url,
            owner=ref.owner,
            name=ref.name,
        )
        for provider in (ProviderType.GITLAB, ProviderType.GITEA)
    ]
