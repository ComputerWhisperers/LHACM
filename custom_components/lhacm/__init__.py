"""Local Home Assistant Component Manager integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import aiohttp_client
import voluptuous as vol

from .const import (
    DOMAIN,
    ProviderType,
    RepositoryCategory,
)
from .exceptions import LHACMError
from .models import ManagedRepository, RepositoryRef
from .provider import create_provider
from .repository import RepositoryManager
from .repository_url import parse_repository_url, provider_config_for_repository
from .store import RepositoryStore

LOGGER = logging.getLogger(__name__)

type LHACMConfigEntry = ConfigEntry[LHACMRuntime]


@dataclass
class LHACMRuntime:
    """Runtime state for LHACM."""

    store: RepositoryStore
    session: object
    repositories: dict[str, ManagedRepository] = field(default_factory=dict)


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


async def async_setup_entry(hass: HomeAssistant, entry: LHACMConfigEntry) -> bool:
    """Set up LHACM from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    store = RepositoryStore(hass)
    runtime = LHACMRuntime(
        store=store,
        session=session,
        repositories=await store.async_load(),
    )
    entry.runtime_data = runtime
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    async def add_repository(call: ServiceCall) -> None:
        ref = parse_repository_url(call.data["repository"])
        category = RepositoryCategory(call.data["category"])
        repository = await _validate_repository(hass, runtime, ref, category)
        runtime.repositories[repository.key] = repository
        await runtime.store.async_save(runtime.repositories)
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
        await runtime.store.async_save(runtime.repositories)
        LOGGER.info("Installed repository %s", ref.full_name)

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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LHACMConfigEntry) -> bool:
    """Unload LHACM."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, "add_repository")
        hass.services.async_remove(DOMAIN, "install_repository")
    return True


def _manager_for_ref(
    hass: HomeAssistant,
    runtime: LHACMRuntime,
    ref: RepositoryRef,
) -> RepositoryManager:
    provider = create_provider(provider_config_for_repository(ref), runtime.session)
    return RepositoryManager(hass, provider)


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
