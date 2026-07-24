"""Config flow for Grouped Lights."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, GROUP_SUBENTRY_TYPE


def _group_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("name"): selector.TextSelector(),
            vol.Required("members"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
            vol.Optional("icon"): selector.IconSelector(),
        }
    )


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": user_input["name"],
        "members": list(user_input["members"]),
    }
    if user_input.get("icon"):
        data["icon"] = user_input["icon"]
    return data


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

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {GROUP_SUBENTRY_TYPE: GroupSubentryFlowHandler}


class GroupSubentryFlowHandler(ConfigSubentryFlow):
    """Create/edit one light group (a subentry of an area entry)."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a new group."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("members"):
                errors["members"] = "no_members"
            else:
                return self.async_create_entry(
                    title=user_input["name"], data=_clean(user_input)
                )
        return self.async_show_form(
            step_id="user", data_schema=_group_schema(), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing group's name and members."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("members"):
                errors["members"] = "no_members"
            else:
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=user_input["name"],
                    data=_clean(user_input),
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _group_schema(), subentry.data
            ),
            errors=errors,
        )
