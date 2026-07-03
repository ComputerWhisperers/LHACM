"""System health for LHACM."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(hass: HomeAssistant, register) -> None:
    """Register system health callbacks."""
    register.async_register_info(DOMAIN, _system_health_info)


async def _system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return LHACM system health information."""
    runtimes = hass.data.get(DOMAIN, {})
    runtime = next(iter(runtimes.values()), None)
    if runtime is None:
        return {"repositories": 0, "installed": 0}
    repositories = list(runtime.repositories.values())
    return {
        "repositories": len(repositories),
        "installed": len([repository for repository in repositories if repository.installed]),
        "pending_updates": len(
            [repository for repository in repositories if repository.pending_update]
        ),
    }

