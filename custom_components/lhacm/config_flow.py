"""Config flow for LHACM."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
import voluptuous as vol

from .const import (
    CONF_ACKNOWLEDGE_RISK,
    CONF_APPDAEMON_DISCOVERY,
    CONF_SIDEPANEL_ICON,
    CONF_SIDEPANEL_TITLE,
    DEFAULT_SIDEPANEL_ICON,
    DEFAULT_SIDEPANEL_TITLE,
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
                    options={
                        CONF_SIDEPANEL_TITLE: DEFAULT_SIDEPANEL_TITLE,
                        CONF_SIDEPANEL_ICON: DEFAULT_SIDEPANEL_ICON,
                        CONF_APPDAEMON_DISCOVERY: False,
                    },
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

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return LHACMOptionsFlow(config_entry)


class LHACMOptionsFlow(config_entries.OptionsFlow):
    """Handle LHACM options."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage LHACM options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SIDEPANEL_TITLE,
                        default=options.get(CONF_SIDEPANEL_TITLE, DEFAULT_SIDEPANEL_TITLE),
                    ): str,
                    vol.Optional(
                        CONF_SIDEPANEL_ICON,
                        default=options.get(CONF_SIDEPANEL_ICON, DEFAULT_SIDEPANEL_ICON),
                    ): str,
                    vol.Optional(
                        CONF_APPDAEMON_DISCOVERY,
                        default=options.get(CONF_APPDAEMON_DISCOVERY, False),
                    ): bool,
                }
            ),
        )
