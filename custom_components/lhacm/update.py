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
            entity.repository_updated()

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_REPOSITORIES_UPDATED, sync_entities)
    )
    sync_entities()


class LHACMRepositoryUpdateEntity(UpdateEntity):
    """A Home Assistant update entity for an LHACM repository."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.SPECIFIC_VERSION
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(self, runtime, repository_key: str) -> None:
        """Initialize entity."""
        self._runtime = runtime
        self._repository_key = repository_key
        self._attr_unique_id = f"{DOMAIN}_{repository_key}"

    @property
    def repository(self) -> ManagedRepository | None:
        """Return the backing repository."""
        return self._runtime.repositories.get(self._repository_key)

    def repository_updated(self) -> None:
        """Write a fresh state after repository metadata changes."""
        self._clear_cached_update_properties()
        self.async_write_ha_state()

    def _clear_cached_update_properties(self) -> None:
        """Clear Home Assistant cached properties backed by repository data."""
        for property_name in (
            "device_info",
            "entity_picture",
            "installed_version",
            "latest_version",
            "release_summary",
            "release_url",
            "state",
            "state_attributes",
            "title",
        ):
            self.__dict__.pop(property_name, None)

    @property
    def name(self) -> str:
        """Return entity name."""
        repository = self.repository
        return f"{repository.display_name} update" if repository else "LHACM repository update"

    @property
    def title(self) -> str | None:
        """Return update title."""
        repository = self.repository
        return repository.display_name if repository else None

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
        return repository.last_release_url or repository.source_url

    @property
    def release_summary(self) -> str | None:
        """Return a short update summary."""
        repository = self.repository
        if not repository:
            return None
        return repository.last_release_name or repository.description

    @property
    def entity_picture(self) -> str | None:
        """Return repository artwork for Home Assistant update cards."""
        repository = self.repository
        if not repository:
            return None
        if repository.brand_icon_url:
            return repository.brand_icon_url
        if repository.category.value == "integration" and repository.domain:
            return f"/api/brands/{repository.domain}/icon.png"
        return None

    async def async_release_notes(self) -> str | None:
        """Return release notes for the Home Assistant update dialog."""
        repository = self.repository
        if not repository:
            return None
        if repository.last_release_notes:
            return repository.last_release_notes
        if repository.available_version:
            return f"# {repository.available_version} - {repository.display_name}"
        return repository.description

    async def async_update(self) -> None:
        """Refresh repository metadata."""
        repository = self.repository
        if repository:
            await self._runtime.refresh_repository(repository)
            self.repository_updated()

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
        self._attr_in_progress = True
        self.repository_updated()
        manager = self._runtime.manager_for_ref(repository.ref)
        try:
            repository = await manager.async_install(repository, ref=version)
            self._runtime.repositories[repository.key] = repository
            await self._runtime.save()
            await self._runtime.async_restart_required(repository, "updated")
        finally:
            self._attr_in_progress = False
            self.repository_updated()
