"""Storage helpers for LHACM."""

from __future__ import annotations

import json
import pathlib

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
        repositories = {
            key: ManagedRepository.from_json(value)
            for key, value in data.get("repositories", {}).items()
        }
        for repository in repositories.values():
            self._apply_installed_manifest_version(repository)
        return repositories

    async def async_save(self, repositories: dict[str, ManagedRepository]) -> None:
        """Save managed repositories."""
        await self._store.async_save(
            {"repositories": {key: repo.to_json() for key, repo in repositories.items()}}
        )

    def _apply_installed_manifest_version(self, repository: ManagedRepository) -> None:
        """Migrate old timestamp versions to the installed manifest version."""
        if not repository.installed or not repository.installed_path:
            return
        manifest_path = pathlib.Path(repository.installed_path) / "manifest.json"
        if not manifest_path.is_file():
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        version = manifest.get("version") if isinstance(manifest, dict) else None
        if not version:
            return
        repository.manifest_version = str(version)
        if repository.installed_version == repository.last_updated:
            repository.installed_version = str(version)
