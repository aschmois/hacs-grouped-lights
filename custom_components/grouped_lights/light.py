"""Light group entities created from group subentries."""
from __future__ import annotations

from homeassistant.components.group.light import LightGroup
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, GROUP_SUBENTRY_TYPE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one group light per group subentry."""
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != GROUP_SUBENTRY_TYPE:
            continue
        data = subentry.data
        async_add_entities(
            [
                GroupedLight(
                    subentry_id,
                    data["name"],
                    list(data["members"]),
                    data.get("icon"),
                )
            ],
            config_subentry_id=subentry_id,
        )


class GroupedLight(LightGroup):
    """A plugin-owned light group; aggregation via HA's built-in LightGroup."""

    def __init__(
        self,
        subentry_id: str,
        name: str,
        member_ids: list[str],
        icon: str | None = None,
    ) -> None:
        # mode=False -> the group is "on" if ANY member is on (not all).
        super().__init__(f"{DOMAIN}_{subentry_id}", name, member_ids, mode=False)
        if icon:
            self._attr_icon = icon
