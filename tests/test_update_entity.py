"""Tests for LHACM update entities."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.lhacm.const import ProviderType, RepositoryCategory
from custom_components.lhacm.models import ManagedRepository, RepositoryRef
from custom_components.lhacm.update import LHACMRepositoryUpdateEntity


def _repo() -> ManagedRepository:
    return ManagedRepository(
        ref=RepositoryRef(
            provider=ProviderType.GITLAB,
            base_url="https://gitlab.example.test",
            owner="lab",
            name="demo",
        ),
        category=RepositoryCategory.INTEGRATION,
        name="Demo",
        installed=True,
        installed_version="1.0.0",
        manifest_version="1.0.1",
    )


def test_repository_updated_clears_home_assistant_update_caches() -> None:
    """Repository updates clear cached HA properties before writing state."""
    repository = _repo()
    entity = LHACMRepositoryUpdateEntity(
        SimpleNamespace(repositories={repository.key: repository}),
        repository.key,
    )
    entity.__dict__.update(
        {
            "installed_version": "1.0.0",
            "latest_version": "1.0.0",
            "state": "off",
            "state_attributes": {"latest_version": "1.0.0"},
            "title": "Old title",
        }
    )

    entity.repository_updated()

    assert "installed_version" not in entity.__dict__
    assert "latest_version" not in entity.__dict__
    assert "state" not in entity.__dict__
    assert "state_attributes" not in entity.__dict__
    assert "title" not in entity.__dict__
    assert entity.state_writes == 1
