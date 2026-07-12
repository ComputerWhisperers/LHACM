"""Tests for repository manager state preservation."""

from __future__ import annotations

import json

from custom_components.lhacm.const import ProviderType, RepositoryCategory
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
