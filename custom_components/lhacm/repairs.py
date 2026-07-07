"""Repair flows for LHACM."""

from __future__ import annotations

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
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
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
