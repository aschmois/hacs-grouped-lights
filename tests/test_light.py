"""Group light entity creation and aggregation."""
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grouped_lights.const import DOMAIN, GROUP_SUBENTRY_TYPE


def _entry_with_group(members):
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Room",
        data={},
        subentries_data=[
            ConfigSubentryData(
                subentry_type=GROUP_SUBENTRY_TYPE,
                title="Floor Lamp",
                data={"name": "Floor Lamp", "members": list(members)},
                unique_id=None,
            )
        ],
    )


def _group_entity_id(hass, entry):
    ent_reg = er.async_get(hass)
    subentry_id = next(iter(entry.subentries))
    return ent_reg.async_get_entity_id("light", DOMAIN, f"{DOMAIN}_{subentry_id}")


async def test_group_on_if_any_member_on(hass):
    hass.states.async_set(
        "light.bulb_1", "on",
        {"brightness": 200, "supported_color_modes": ["brightness"], "color_mode": "brightness"},
    )
    hass.states.async_set(
        "light.bulb_2", "off", {"supported_color_modes": ["brightness"]}
    )
    entry = _entry_with_group(["light.bulb_1", "light.bulb_2"])
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    eid = _group_entity_id(hass, entry)
    assert eid is not None
    state = hass.states.get(eid)
    assert state.state == "on"
    assert state.attributes["brightness"] == 200


async def test_group_off_when_all_members_off(hass):
    hass.states.async_set("light.bulb_1", "off", {"supported_color_modes": ["brightness"]})
    hass.states.async_set("light.bulb_2", "off", {"supported_color_modes": ["brightness"]})
    entry = _entry_with_group(["light.bulb_1", "light.bulb_2"])
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    eid = _group_entity_id(hass, entry)
    assert hass.states.get(eid).state == "off"
