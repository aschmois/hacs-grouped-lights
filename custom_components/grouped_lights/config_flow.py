"""Config flow for Grouped Lights."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import DOMAIN


class GroupedLightsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create one config entry per area/room."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name the area and create the entry."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required("name"): selector.TextSelector()}),
            )
        return self.async_create_entry(title=user_input["name"], data={})
