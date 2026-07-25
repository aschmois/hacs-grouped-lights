"""Light group entities created from group subentries."""
from __future__ import annotations

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import slugify

from .const import DOMAIN, GROUP_SUBENTRY_TYPE

ALL_GROUP_ICON = "mdi:lightbulb-group"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one group light per group subentry, plus the area's "all" group."""
    registry = er.async_get(hass)
    group_entity_ids: list[str] = []
    nested: set[str] = set()

    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != GROUP_SUBENTRY_TYPE:
            continue
        data = subentry.data
        name = data["name"]
        members = list(data["members"])
        nested.update(members)
        # Reserve the entity id up front so the "all" group can list this group
        # as a member on the very first setup, before the platform adds it.
        group_entity_ids.append(_reserve_entity_id(registry, entry, subentry_id, name))
        async_add_entities(
            [GroupedLight(subentry_id, name, members, data.get("icon"))],
            config_subentry_id=subentry_id,
        )

    # One entity for the whole area: the groups that are not nested inside
    # another group — i.e. the roots of the area -> lamp -> bulb tree.
    async_add_entities(
        [
            GroupedLight(
                f"{entry.entry_id}_all",
                entry.title,
                [eid for eid in group_entity_ids if eid not in nested],
                ALL_GROUP_ICON,
            )
        ]
    )


def _reserve_entity_id(
    registry: er.EntityRegistry, entry: ConfigEntry, subentry_id: str, name: str
) -> str:
    """Entity id a group subentry's light has (creating its registry entry if new)."""
    unique_id = f"{DOMAIN}_{subentry_id}"
    if existing := registry.async_get_entity_id(LIGHT_DOMAIN, DOMAIN, unique_id):
        return existing
    return registry.async_get_or_create(
        LIGHT_DOMAIN,
        DOMAIN,
        unique_id,
        suggested_object_id=slugify(name),
        original_name=name,
        config_entry=entry,
        config_subentry_id=subentry_id,
    ).entity_id


class GroupedLight(LightGroup):
    """A plugin-owned light group; aggregation via HA's built-in LightGroup."""

    def __init__(
        self,
        key: str,
        name: str,
        member_ids: list[str],
        icon: str | None = None,
    ) -> None:
        # mode=False -> the group is "on" if ANY member is on (not all).
        super().__init__(f"{DOMAIN}_{key}", name, member_ids, mode=False)
        if icon:
            self._attr_icon = icon
