"""Storage helpers for LHACM."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORE_REPOSITORIES
from .models import ManagedRepository

STORAGE_VERSION = 1


class RepositoryStore:
    """Persist managed repositories."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{STORE_REPOSITORIES}")

    async def async_load(self) -> dict[str, ManagedRepository]:
        """Load managed repositories."""
        data = await self._store.async_load()
        if not data:
            return {}
        return {
            key: ManagedRepository.from_json(value)
            for key, value in data.get("repositories", {}).items()
        }

    async def async_save(self, repositories: dict[str, ManagedRepository]) -> None:
        """Save managed repositories."""
        await self._store.async_save(
            {"repositories": {key: repo.to_json() for key, repo in repositories.items()}}
        )

