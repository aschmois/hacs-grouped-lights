"""Light group entities created from group subentries."""
from __future__ import annotations

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import ATTR_TRANSITION, ColorMode
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import slugify

from .const import DOMAIN, GROUP_SUBENTRY_TYPE

ALL_GROUP_ICON = "mdi:lightbulb-group"


def _clamp_entity_ids(member: str) -> tuple[str, str]:
    """The Zooz brightness-clamp params, as Z-Wave JS exposes them."""
    object_id = member.split(".", 1)[1]
    return (
        f"number.{object_id}_minimum_brightness",
        f"number.{object_id}_maximum_brightness",
    )


def _member_is_onoff(hass: HomeAssistant, member: str) -> bool:
    """A member can't dim if it's a switch, or a dimmer clamped to min == max.

    The clamp is read from the dimmer's own Minimum/Maximum Brightness number
    entities (Zooz via Z-Wave JS) — the device stays the single source of
    truth, so unclamping the switch un-clamps every group it belongs to.
    """
    if member.startswith("switch."):
        return True
    lo_id, hi_id = _clamp_entity_ids(member)
    lo, hi = hass.states.get(lo_id), hass.states.get(hi_id)
    if lo is None or hi is None:
        return False
    try:
        return float(lo.state) == float(hi.state)
    except ValueError:
        return False


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
    """A plugin-owned light group; aggregation via HA's built-in LightGroup.

    Switch members are first-class: they count toward the group's on/off state
    (LightGroup's aggregation is domain-agnostic) but receive plain
    switch.turn_on/off — no brightness or color kwargs.
    """

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
        self._all_member_ids = list(member_ids)
        self._switch_member_ids = [e for e in member_ids if e.startswith("switch.")]
        self._light_member_ids = [e for e in member_ids if not e.startswith("switch.")]
        # Computed each update: True when every member is on/off-only.
        self._onoff = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # The clamp params are the single source of truth for "can this dim":
        # when a member's Minimum/Maximum Brightness change, re-derive.
        clamp_ids = [eid for m in self._light_member_ids for eid in _clamp_entity_ids(m)]
        if clamp_ids:
            self.async_on_remove(
                async_track_state_change_event(self.hass, clamp_ids, self._clamp_changed)
            )

    @callback
    def _clamp_changed(self, _event) -> None:
        self.async_update_group_state()
        self.async_write_ha_state()

    def async_update_group_state(self) -> None:
        super().async_update_group_state()
        self._onoff = bool(self._all_member_ids) and all(
            _member_is_onoff(self.hass, m) for m in self._all_member_ids
        )
        if self._onoff:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_brightness = None

    async def _async_forward(self, service: str, **kwargs) -> None:
        # LightGroup targets self._entity_ids; aiming the base call at the
        # light members only keeps switches out of light.* service calls
        # (which would log "referenced entities missing" for them).
        if self._light_member_ids:
            self._entity_ids = self._light_member_ids
            try:
                if service == SERVICE_TURN_ON:
                    await super().async_turn_on(**kwargs)
                else:
                    await super().async_turn_off(**kwargs)
            finally:
                self._entity_ids = self._all_member_ids
        if self._switch_member_ids:
            await self.hass.services.async_call(
                SWITCH_DOMAIN,
                service,
                {ATTR_ENTITY_ID: self._switch_member_ids},
                blocking=True,
                context=self._context,
            )

    async def async_turn_on(self, **kwargs) -> None:
        if self._onoff:
            kwargs = {k: v for k, v in kwargs.items() if k == ATTR_TRANSITION}
        await self._async_forward(SERVICE_TURN_ON, **kwargs)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_forward(SERVICE_TURN_OFF, **kwargs)
