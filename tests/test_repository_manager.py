"""Tests for repository manager state preservation."""

from __future__ import annotations

import json
import asyncio
from unittest.mock import AsyncMock

from custom_components.lhacm.const import ProviderType, RepositoryCategory
from custom_components.lhacm.exceptions import ProviderNotFoundError
from custom_components.lhacm.models import ManagedRepository, RepositoryRef
from custom_components.lhacm.repository import RepositoryManager


def _repo(**kwargs) -> ManagedRepository:
    return ManagedRepository(
        ref=RepositoryRef(
            provider=ProviderType.GITLAB,
            base_url="https://gitlab.example.test",
            owner="lab",
            name="demo",
        ),
        category=RepositoryCategory.INTEGRATION,
        **kwargs,
    )


class _FakeHass:
    async def async_add_executor_job(self, target, *args):
        return target(*args)


def test_installed_version_reads_local_manifest(tmp_path) -> None:
    """Refresh preservation uses the installed manifest, not the remote latest."""
    install_path = tmp_path / "demo"
    install_path.mkdir()
    (install_path / "manifest.json").write_text(
        json.dumps({"domain": "demo", "version": "1.0.0"}),
        encoding="utf-8",
    )
    repository = _repo(
        installed=True,
        installed_version="2026-07-12T10:00:00Z",
        installed_path=str(install_path),
    )
    manager = RepositoryManager(None, None)

    assert manager._installed_version(repository) == "1.0.0"


def test_installed_version_falls_back_without_local_manifest() -> None:
    """Existing installed version is preserved when no local manifest is available."""
    repository = _repo(installed=True, installed_version="1.0.0")
    manager = RepositoryManager(None, None)

    assert manager._installed_version(repository) == "1.0.0"


def test_install_uses_selected_ref_when_it_matches_manifest_version() -> None:
    """New installs must download the selected tag, not substitute the default branch."""
    repository = _repo(default_branch="main", manifest_version="1.0.0")
    manager = RepositoryManager(_FakeHass(), None)
    manager._download_archive = AsyncMock(return_value=b"zip")
    manager._extract_archive = lambda archive, repo: None
    manager._target_path = lambda repo: "custom_components/demo"

    installed = asyncio.run(manager.async_install(repository, ref="1.0.0"))

    manager._download_archive.assert_awaited_once_with(repository.ref, "1.0.0")
    assert installed.installed_version == "1.0.0"


def test_install_retries_v_prefixed_tag_when_manifest_version_is_not_a_ref() -> None:
    """Manifest versions like 1.0.0 should fall back to tag refs like v1.0.0."""
    repository = _repo(default_branch="main", manifest_version="1.0.0")
    manager = RepositoryManager(_FakeHass(), None)
    manager._extract_archive = lambda archive, repo: None
    manager._target_path = lambda repo: "custom_components/demo"

    async def _download_archive(ref, revision):
        if revision == "1.0.0":
            raise ProviderNotFoundError("Provider resource was not found")
        if revision == "v1.0.0":
            return b"zip"
        raise AssertionError(f"Unexpected revision {revision}")

    manager._download_archive = AsyncMock(side_effect=_download_archive)

    installed = asyncio.run(manager.async_install(repository, ref="1.0.0"))

    assert [call.args[1] for call in manager._download_archive.await_args_list] == [
        "1.0.0",
        "v1.0.0",
    ]
    assert installed.installed_version == "v1.0.0"
