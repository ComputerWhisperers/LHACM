"""Tests for runtime update entity notifications."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.lhacm import DOMAIN, LHACMRuntime, ir
from custom_components.lhacm.models import ManagedRepository, RepositoryRef
from custom_components.lhacm.const import ProviderType, RepositoryCategory


class FakeStore:
    """Minimal async store."""

    def __init__(self) -> None:
        self.saved = None

    async def async_save(self, repositories) -> None:
        self.saved = repositories


class FakeUpdateEntity:
    """Minimal update entity writer."""

    def __init__(self) -> None:
        self.writes = 0

    def async_write_ha_state(self) -> None:
        self.writes += 1


def test_runtime_save_writes_registered_update_entities() -> None:
    """Repository refresh/save immediately writes HA update entity state."""
    store = FakeStore()
    entity = FakeUpdateEntity()
    runtime = LHACMRuntime(
        store=store,
        session=None,
        hass=SimpleNamespace(),
        repositories={},
        update_entities={"repo": entity},
    )

    asyncio.run(runtime.save())

    assert store.saved == {}
    assert entity.writes == 1


def _repo(owner: str, name: str, display_name: str) -> ManagedRepository:
    return ManagedRepository(
        ref=RepositoryRef(
            provider=ProviderType.GITLAB,
            base_url="https://gitlab.example.test",
            owner=owner,
            name=name,
        ),
        category=RepositoryCategory.INTEGRATION,
        name=display_name,
    )


def test_restart_required_repairs_are_aggregated(monkeypatch) -> None:
    """Multiple repository updates should create one restart repair issue."""
    created = []
    deleted = []
    runtime = LHACMRuntime(
        store=FakeStore(),
        session=None,
        hass=SimpleNamespace(),
        repositories={},
    )

    monkeypatch.setattr(ir, "async_create_issue", lambda *args, **kwargs: created.append((args, kwargs)))
    monkeypatch.setattr(ir, "async_delete_issue", lambda *args, **kwargs: deleted.append(args))

    asyncio.run(runtime.async_restart_required(_repo("lab", "one", "One"), "updated"))
    asyncio.run(runtime.async_restart_required(_repo("lab", "two", "Two"), "updated"))

    assert [call[0][2] for call in created] == ["restart_required", "restart_required"]
    assert created[-1][1]["data"]["name"] == "One, Two"
    assert created[-1][1]["data"]["repositories"] == [
        "gitlab:https://gitlab.example.test:lab/one",
        "gitlab:https://gitlab.example.test:lab/two",
    ]
    assert created[-1][1]["issue_domain"] == DOMAIN
