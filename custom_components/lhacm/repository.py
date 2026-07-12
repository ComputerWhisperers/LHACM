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
from homeassistant.util import dt as dt_util

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
        existing: ManagedRepository | None = None,
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
        latest_release = stable_releases[0] if stable_releases else None
        last_version = latest_release.tag if latest_release else None
        manifest_version = self._manifest_version(manifest)
        brand_icon = self._find_brand_icon(tree, category, source.default_branch, domain)

        repository = ManagedRepository(
            ref=ref,
            category=category,
            domain=domain,
            default_branch=source.default_branch,
            last_version=last_version,
            last_release_name=latest_release.name if latest_release else None,
            last_release_notes=latest_release.body if latest_release else None,
            last_release_url=latest_release.html_url if latest_release else None,
            manifest_version=manifest_version,
            name=manifest.get("name") if isinstance(manifest, dict) else source.ref.name,
            description=source.description,
            stars=source.stars,
            downloads=0,
            last_updated=source.last_updated,
            source_url=source.html_url or f"{ref.base_url}/{ref.full_name}",
            brand_icon_url=brand_icon.download_url if brand_icon else None,
            topics=source.topics,
            last_checked=dt_util.utcnow().isoformat(),
        )
        if existing is not None:
            repository.installed = existing.installed
            repository.installed_version = self._installed_version(existing)
            repository.installed_commit = existing.installed_commit
            repository.installed_path = existing.installed_path
            repository.custom = existing.custom
        return repository

    def _manifest_version(self, manifest: dict[str, Any]) -> str | None:
        """Return the repository manifest version if one exists."""
        version = manifest.get("version") if isinstance(manifest, dict) else None
        if version in (None, ""):
            return None
        return str(version)

    def _installed_version(self, existing: ManagedRepository) -> str | None:
        """Return the version currently installed on disk."""
        manifest_version = self._installed_manifest_version(existing)
        if manifest_version:
            return manifest_version
        return existing.installed_version

    def _installed_manifest_version(self, repository: ManagedRepository) -> str | None:
        """Read the installed manifest version for a downloaded repository."""
        if not repository.installed_path:
            return None
        manifest_path = pathlib.Path(repository.installed_path) / "manifest.json"
        if not manifest_path.is_file():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        version = manifest.get("version") if isinstance(manifest, dict) else None
        if version in (None, ""):
            return None
        return str(version)

    def _find_brand_icon(
        self,
        tree: list[SourceFile],
        category: RepositoryCategory,
        branch: str,
        domain: str | None,
    ) -> SourceFile | None:
        """Find a repository-provided brand icon."""
        if category != RepositoryCategory.INTEGRATION:
            return None
        candidates = [
            item
            for item in tree
            if not item.is_directory
            and item.download_url
            and (
                item.path.lower() == "brand/icon.png"
                or item.path.lower().endswith("/brand/icon.png")
            )
        ]
        preferred_paths = []
        if domain:
            preferred_paths.append(f"custom_components/{domain}/brand/icon.png")
            preferred_paths.append(f"{domain}/brand/icon.png")
        preferred_paths.append("brand/icon.png")
        for path in preferred_paths:
            match = next((item for item in candidates if item.path.lower() == path.lower()), None)
            if match:
                return match
        return candidates[0] if candidates else None

    async def async_install(
        self,
        repository: ManagedRepository,
        *,
        ref: str | None = None,
    ) -> ManagedRepository:
        """Install a managed repository from its archive."""
        revision = ref or repository.last_version or repository.default_branch
        if ref and not repository.last_version and ref == repository.available_version:
            revision = repository.default_branch
        if not revision:
            raise LHACMError("No branch, tag, or release is available to install")

        archive = await self._download_archive(repository.ref, revision)
        await self.hass.async_add_executor_job(
            self._extract_archive,
            archive,
            repository,
        )
        repository.installed = True
        repository.installed_version = ref or repository.last_version or repository.manifest_version or revision
        repository.installed_commit = repository.last_updated
        repository.installed_path = str(self._target_path(repository))
        return repository

    async def async_refresh(self, repository: ManagedRepository) -> ManagedRepository:
        """Refresh repository metadata while preserving install state."""
        return await self.async_validate(repository.ref, repository.category, existing=repository)

    async def async_uninstall(self, repository: ManagedRepository) -> ManagedRepository:
        """Uninstall repository files from Home Assistant."""
        await self.hass.async_add_executor_job(self._remove_repository_files, repository)
        repository.installed = False
        repository.installed_version = None
        repository.installed_commit = None
        repository.installed_path = None
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

    def _remove_repository_files(self, repository: ManagedRepository) -> None:
        target = self._target_path(repository)
        config_root = pathlib.Path(self.hass.config.path()).resolve()
        resolved = target.resolve()
        if config_root not in resolved.parents and resolved != config_root:
            raise RepositoryValidationError("Install path is outside the Home Assistant config path")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

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
