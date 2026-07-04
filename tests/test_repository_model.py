"""Tests for managed repository lifecycle state."""

from __future__ import annotations

from custom_components.lhacm.const import ProviderType, RepositoryCategory
from custom_components.lhacm.models import ManagedRepository, RepositoryRef


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


def test_release_pending_update() -> None:
    """Release repositories are pending when latest tag differs."""
    repository = _repo(installed=True, installed_version="v1.0.0", last_version="v1.1.0")

    assert repository.pending_update is True
    assert repository.status == "pending-upgrade"


def test_branch_pending_update() -> None:
    """Branch repositories compare provider activity markers."""
    repository = _repo(
        installed=True,
        installed_version="main",
        installed_commit="old",
        default_branch="main",
        last_updated="new",
    )

    assert repository.pending_update is True


def test_brand_icon_url_round_trip() -> None:
    """Repository brand icon URLs are persisted."""
    repository = _repo(brand_icon_url="https://gitlab.example.test/icon.png")

    restored = ManagedRepository.from_json(repository.to_json())

    assert restored.brand_icon_url == "https://gitlab.example.test/icon.png"
