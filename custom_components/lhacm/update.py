"""Update entities for LHACM managed repositories."""

from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_REPOSITORIES_UPDATED
from .models import ManagedRepository


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LHACM update entities."""
    runtime = entry.runtime_data
    entities: dict[str, LHACMRepositoryUpdateEntity] = {}

    def sync_entities() -> None:
        new_entities = []
        for repository in runtime.repositories.values():
            if not repository.installed or repository.key in entities:
                continue
            entity = LHACMRepositoryUpdateEntity(runtime, repository.key)
            entities[repository.key] = entity
            new_entities.append(entity)
        if new_entities:
            async_add_entities(new_entities)
        for entity in entities.values():
            entity.async_write_ha_state()

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_REPOSITORIES_UPDATED, sync_entities)
    )
    sync_entities()


class LHACMRepositoryUpdateEntity(UpdateEntity):
    """A Home Assistant update entity for an LHACM repository."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(self, runtime, repository_key: str) -> None:
        """Initialize entity."""
        self._runtime = runtime
        self._repository_key = repository_key
        self._attr_unique_id = f"{DOMAIN}_{repository_key}"

    @property
    def repository(self) -> ManagedRepository | None:
        """Return the backing repository."""
        return self._runtime.repositories.get(self._repository_key)

    @property
    def name(self) -> str:
        """Return entity name."""
        repository = self.repository
        return f"{repository.display_name} update" if repository else "LHACM repository update"

    @property
    def device_info(self) -> dict:
        """Return device information for the repository."""
        repository = self.repository
        if repository is None:
            return {"identifiers": {(DOMAIN, self._repository_key)}, "name": "LHACM repository"}
        return {
            "identifiers": {(DOMAIN, repository.key)},
            "name": repository.display_name,
            "manufacturer": repository.ref.provider.value,
            "model": repository.category.value,
            "configuration_url": repository.source_url,
            "sw_version": repository.installed_version,
            "via_device": (DOMAIN, "lhacm"),
        }

    @property
    def extra_state_attributes(self) -> dict:
        """Return repository attributes."""
        repository = self.repository
        if repository is None:
            return {}
        return {
            "repository": repository.ref.full_name,
            "provider": repository.ref.provider.value,
            "category": repository.category.value,
            "source_url": repository.source_url,
            "installed_path": repository.installed_path,
        }

    @property
    def installed_version(self) -> str | None:
        """Return installed version."""
        repository = self.repository
        return repository.installed_version if repository else None

    @property
    def latest_version(self) -> str | None:
        """Return latest version."""
        repository = self.repository
        return repository.available_version if repository else None

    @property
    def release_url(self) -> str | None:
        """Return release URL."""
        repository = self.repository
        if not repository:
            return None
        return repository.source_url

    @property
    def entity_picture(self) -> str | None:
        """Return no entity picture."""
        return None

    async def async_update(self) -> None:
        """Refresh repository metadata."""
        repository = self.repository
        if repository:
            await self._runtime.refresh_repository(repository)

    async def async_install(
        self,
        version: str | None = None,
        backup: bool = False,
        **kwargs,
    ) -> None:
        """Install an update."""
        repository = self.repository
        if not repository:
            return
        manager = self._runtime.manager_for_ref(repository.ref)
        repository = await manager.async_install(repository, ref=version)
        self._runtime.repositories[repository.key] = repository
        await self._runtime.save()
