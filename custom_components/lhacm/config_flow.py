"""Config flow for LHACM."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
import voluptuous as vol

from .const import (
    CONF_ACKNOWLEDGE_RISK,
    DOMAIN,
)


class LHACMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an LHACM config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            if not user_input.get(CONF_ACKNOWLEDGE_RISK):
                errors["base"] = "acknowledge"
            else:
                return self.async_create_entry(
                    title="LHACM",
                    data={},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACKNOWLEDGE_RISK, default=False): bool,
                }
            ),
            errors=errors,
        )
