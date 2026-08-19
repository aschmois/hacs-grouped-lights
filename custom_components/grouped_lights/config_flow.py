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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, selector

from .const import DOMAIN, GROUP_SUBENTRY_TYPE

ICON_SINGLE = "mdi:lightbulb"
ICON_GROUP = "mdi:lightbulb-group"


def _group_schema() -> vol.Schema:
    """Members first: the name and icon defaults are derived from them."""
    return vol.Schema(
        {
            vol.Required("members"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["light", "switch"], multiple=True)
            ),
            vol.Optional("name"): selector.TextSelector(),
            vol.Optional("icon"): selector.IconSelector(),
        }
    )


def _member_name(hass: HomeAssistant, entity_id: str) -> str:
    """Best available display name for a single member light."""
    state = hass.states.get(entity_id)
    if state and (friendly := state.attributes.get("friendly_name")):
        return str(friendly)
    entry = er.async_get(hass).async_get(entity_id)
    if entry and (name := entry.name or entry.original_name):
        return str(name)
    return entity_id.split(".", 1)[-1].replace("_", " ").title()


def _validate(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """Validate the group form; return (data, errors).

    A name is optional for a single member (we borrow the light's own name) and
    required once there is more than one. The icon defaults to a single-bulb or
    a bulb-group icon to match.
    """
    members = list(user_input.get("members") or [])
    if not members:
        return None, {"members": "no_members"}

    name = str(user_input.get("name") or "").strip()
    if not name:
        if len(members) > 1:
            return None, {"name": "name_required"}
        name = _member_name(hass, members[0])

    icon = user_input.get("icon") or (ICON_GROUP if len(members) > 1 else ICON_SINGLE)
    return {"name": name, "members": members, "icon": icon}, {}


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
            data, errors = _validate(self.hass, user_input)
            if data is not None:
                return self.async_create_entry(title=data["name"], data=data)
        return self.async_show_form(
            step_id="user", data_schema=_group_schema(), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing group's members, name and icon."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = _validate(self.hass, user_input)
            if data is not None:
                return self.async_update_and_abort(
                    self._get_entry(), subentry, title=data["name"], data=data
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _group_schema(), subentry.data
            ),
            errors=errors,
        )
