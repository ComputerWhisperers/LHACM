"""Tests for runtime update entity notifications."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.lhacm import LHACMRuntime


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
