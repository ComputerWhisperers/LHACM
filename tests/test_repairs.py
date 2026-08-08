"""Tests for LHACM repair flows."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.lhacm import DOMAIN
from custom_components.lhacm.repairs import RestartRequiredRepairFlow, ir


class FakeServices:
    """Minimal service caller."""

    def __init__(self) -> None:
        self.calls = []

    async def async_call(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


def test_restart_repair_confirm_cleans_visible_legacy_repairs(monkeypatch) -> None:
    """Confirming restart should remove all visible LHACM restart repair issues."""
    deleted = []
    legacy_issue = SimpleNamespace(domain=DOMAIN, issue_id="restart_required_deadbeef1234")
    hass = SimpleNamespace(services=FakeServices())
    flow = RestartRequiredRepairFlow("restart_required", {})
    flow.hass = hass

    monkeypatch.setattr(ir, "async_delete_issue", lambda *args, **kwargs: deleted.append(args))
    monkeypatch.setattr(
        ir,
        "async_get",
        lambda _hass: SimpleNamespace(issues={(DOMAIN, "restart_required_deadbeef1234"): legacy_issue}),
        raising=False,
    )

    result = asyncio.run(flow.async_step_confirm({}))

    assert result["type"] == "create_entry"
    assert (hass, DOMAIN, "restart_required") in deleted
    assert (hass, DOMAIN, "restart_required_deadbeef1234") in deleted
    assert hass.services.calls == [(("homeassistant", "restart"), {"blocking": False})]
