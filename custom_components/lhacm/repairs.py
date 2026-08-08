"""Repair flows for LHACM."""

from __future__ import annotations

import hashlib
from typing import Any

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


class RestartRequiredRepairFlow(RepairsFlow):
    """Repair flow that restarts Home Assistant after an LHACM update."""

    def __init__(self, issue_id: str, data: dict[str, Any] | None) -> None:
        """Initialize the flow."""
        self._issue_id = issue_id
        self._data = data or {}

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        return await self.async_step_confirm(user_input)

    async def async_step_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> data_entry_flow.FlowResult:
        """Ask the user to confirm the restart."""
        if user_input is not None:
            _async_delete_restart_required_issues(
                self.hass,
                self._issue_id,
                self._data.get("repositories") or [],
            )
            await self.hass.services.async_call(
                "homeassistant",
                "restart",
                blocking=False,
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": str(self._data.get("name") or "the integration"),
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create a repair flow."""
    return RestartRequiredRepairFlow(issue_id, data)


def _legacy_restart_issue_id(repository_key: str) -> str:
    """Return the pre-aggregate restart repair issue id for a repository."""
    issue_hash = hashlib.sha1(repository_key.encode()).hexdigest()[:12]
    return f"restart_required_{issue_hash}"


def _async_delete_restart_required_issues(
    hass: HomeAssistant,
    issue_id: str,
    repository_keys,
) -> None:
    """Delete aggregate and legacy restart repair issues."""
    ir.async_delete_issue(hass, DOMAIN, issue_id)
    ir.async_delete_issue(hass, DOMAIN, "restart_required")
    for repository_key in repository_keys:
        ir.async_delete_issue(hass, DOMAIN, _legacy_restart_issue_id(str(repository_key)))
    registry = getattr(ir, "async_get", lambda _hass: None)(hass)
    issues = getattr(registry, "issues", {}) or {}
    for key, issue in list(issues.items()):
        domain = getattr(issue, "domain", None)
        found_issue_id = getattr(issue, "issue_id", None)
        if isinstance(key, tuple) and len(key) >= 2:
            domain = domain or key[0]
            found_issue_id = found_issue_id or key[1]
        if domain == DOMAIN and str(found_issue_id or "").startswith("restart_required_"):
            ir.async_delete_issue(hass, DOMAIN, str(found_issue_id))
