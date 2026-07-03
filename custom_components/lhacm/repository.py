"""Repository validation and installation for LHACM."""

from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
from typing import Any
import zipfile

from aiohttp import ClientTimeout
from homeassistant.core import HomeAssistant

from .const import RepositoryCategory
from .exceptions import RepositoryValidationError, LHACMError
from .models import ManagedRepository, RepositoryRef, SourceFile
from .provider import RepositoryProvider


class RepositoryManager:
    """Manage repositories for a single provider."""

    def __init__(self, hass: HomeAssistant, provider: RepositoryProvider) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.provider = provider

    async def async_validate(
        self,
        ref: RepositoryRef,
        category: RepositoryCategory,
    ) -> ManagedRepository:
        """Validate a repository and return a managed representation."""
        source = await self.provider.get_repository(ref)
        if source.archived:
            raise RepositoryValidationError("Repository is archived")

        tree = await self.provider.get_tree(ref, source.default_branch)
        manifest_file = self._find_manifest(tree, category, ref.name)
        manifest = await self._read_json_file(manifest_file.download_url)

        domain = manifest.get("domain") if isinstance(manifest, dict) else None
        if category == RepositoryCategory.INTEGRATION and not domain:
            raise RepositoryValidationError("Integration repository is missing manifest domain")

        releases = [release for release in await self.provider.get_releases(ref) if not release.draft]
        stable_releases = [release for release in releases if not release.prerelease]
        last_version = stable_releases[0].tag if stable_releases else None

        return ManagedRepository(
            ref=ref,
            category=category,
            domain=domain,
            default_branch=source.default_branch,
            last_version=last_version,
            name=manifest.get("name") if isinstance(manifest, dict) else source.ref.name,
            description=source.description,
            stars=source.stars,
            downloads=0,
            last_updated=None,
        )

    async def async_install(
        self,
        repository: ManagedRepository,
        *,
        ref: str | None = None,
    ) -> ManagedRepository:
        """Install a managed repository from its archive."""
        revision = ref or repository.last_version or repository.default_branch
        if not revision:
            raise LHACMError("No branch, tag, or release is available to install")

        archive = await self._download_archive(repository.ref, revision)
        await self.hass.async_add_executor_job(
            self._extract_archive,
            archive,
            repository,
        )
        repository.installed = True
        repository.installed_version = revision
        return repository

    def _find_manifest(
        self,
        tree: list[SourceFile],
        category: RepositoryCategory,
        repository_name: str,
    ) -> SourceFile:
        if category != RepositoryCategory.INTEGRATION:
            hacs_file = next((item for item in tree if item.path == "hacs.json"), None)
            if hacs_file and hacs_file.download_url:
                return hacs_file
            raise RepositoryValidationError(f"{category} repositories need hacs.json")

        candidates = [
            item
            for item in tree
            if not item.is_directory and item.path.endswith("manifest.json") and item.download_url
        ]
        preferred_paths = [
            f"custom_components/{repository_name}/manifest.json",
            f"{repository_name}/manifest.json",
            "manifest.json",
        ]
        for path in preferred_paths:
            if match := next((item for item in candidates if item.path == path), None):
                return match
        if len(candidates) == 1:
            return candidates[0]
        raise RepositoryValidationError("Could not determine integration manifest path")

    async def _read_json_file(self, url: str | None) -> dict[str, Any]:
        if not url:
            raise RepositoryValidationError("No downloadable manifest was found")
        response = await self.provider.session.get(
            url,
            headers=self.provider.archive_headers(),
            ssl=self.provider.config.verify_ssl,
            timeout=ClientTimeout(total=60),
        )
        await self.provider._raise_for_status(response)
        return json.loads(await response.text())

    async def _download_archive(self, ref: RepositoryRef, revision: str) -> bytes:
        url = self.provider.archive_url(ref, revision)
        response = await self.provider.session.get(
            url,
            headers=self.provider.archive_headers(),
            ssl=self.provider.config.verify_ssl,
            timeout=ClientTimeout(total=120),
        )
        await self.provider._raise_for_status(response)
        return await response.read()

    def _extract_archive(self, archive: bytes, repository: ManagedRepository) -> None:
        target = self._target_path(repository)
        target_parent = target.parent
        target_parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = pathlib.Path(temp_dir) / "repository.zip"
            archive_path.write_bytes(archive)
            extract_path = pathlib.Path(temp_dir) / "extract"
            extract_path.mkdir()
            with zipfile.ZipFile(archive_path) as zip_file:
                self._safe_extract(zip_file, extract_path)

            source = self._source_path(extract_path, repository)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)

    def _target_path(self, repository: ManagedRepository) -> pathlib.Path:
        if repository.category == RepositoryCategory.INTEGRATION:
            if not repository.domain:
                raise RepositoryValidationError("Integration repository is missing domain")
            return pathlib.Path(self.hass.config.path("custom_components", repository.domain))
        if repository.category == RepositoryCategory.PLUGIN:
            return pathlib.Path(self.hass.config.path("www", "community", repository.ref.name))
        if repository.category == RepositoryCategory.THEME:
            return pathlib.Path(self.hass.config.path("themes", repository.ref.name))
        if repository.category == RepositoryCategory.PYTHON_SCRIPT:
            return pathlib.Path(self.hass.config.path("python_scripts"))
        if repository.category == RepositoryCategory.APPDAEMON:
            return pathlib.Path(self.hass.config.path("appdaemon", "apps", repository.ref.name))
        if repository.category == RepositoryCategory.TEMPLATE:
            return pathlib.Path(self.hass.config.path("custom_templates", repository.ref.name))
        raise RepositoryValidationError(f"Unsupported category: {repository.category}")

    def _source_path(
        self,
        extract_path: pathlib.Path,
        repository: ManagedRepository,
    ) -> pathlib.Path:
        roots = [item for item in extract_path.iterdir() if item.is_dir()]
        root = roots[0] if len(roots) == 1 else extract_path
        if repository.category == RepositoryCategory.INTEGRATION:
            candidates = [
                root / "custom_components" / str(repository.domain),
                root / str(repository.domain),
                root,
            ]
            for candidate in candidates:
                if (candidate / "manifest.json").exists():
                    return candidate
            raise RepositoryValidationError("Archive did not contain the integration manifest")
        return root

    def _safe_extract(self, zip_file: zipfile.ZipFile, destination: pathlib.Path) -> None:
        destination = destination.resolve()
        for member in zip_file.infolist():
            member_path = (destination / member.filename).resolve()
            if destination not in member_path.parents and member_path != destination:
                raise RepositoryValidationError("Archive contains an unsafe path")
        zip_file.extractall(destination)
