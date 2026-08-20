"""Group light entity creation and aggregation."""
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grouped_lights.const import DOMAIN, GROUP_SUBENTRY_TYPE


def _subentry(name, members):
    return ConfigSubentryData(
        subentry_type=GROUP_SUBENTRY_TYPE,
        title=name,
        data={"name": name, "members": list(members)},
        unique_id=None,
    )


def _entry_with_group(members):
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Room",
        data={},
        subentries_data=[_subentry("Floor Lamp", members)],
    )


def _group_entity_id(hass, entry, subentry_id=None):
    ent_reg = er.async_get(hass)
    subentry_id = subentry_id or next(iter(entry.subentries))
    return ent_reg.async_get_entity_id("light", DOMAIN, f"{DOMAIN}_{subentry_id}")


def _all_entity_id(hass, entry):
    return er.async_get(hass).async_get_entity_id(
        "light", DOMAIN, f"{DOMAIN}_{entry.entry_id}_all"
    )


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


async def test_area_all_group_lists_its_groups(hass):
    """Every area gets one "all" entity whose members are its top-level groups."""
    hass.states.async_set("light.bulb_1", "off", {"supported_color_modes": ["onoff"]})
    entry = _entry_with_group(["light.bulb_1"])
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    all_eid = _all_entity_id(hass, entry)
    assert all_eid is not None
    state = hass.states.get(all_eid)
    assert state.attributes["friendly_name"] == "Test Room"
    assert state.attributes["icon"] == "mdi:lightbulb-group"
    assert state.attributes["entity_id"] == [_group_entity_id(hass, entry)]


async def test_area_all_group_skips_nested_groups(hass):
    """A group used inside another group is not also a member of "all"."""
    hass.states.async_set("light.bulb_1", "off", {"supported_color_modes": ["onoff"]})
    entry = MockConfigEntry(
        domain=DOMAIN, title="Test Room", data={},
        subentries_data=[
            _subentry("Inner Lamp", ["light.bulb_1"]),
            # The outer group holds the inner group, by the entity id the inner
            # group is registered under.
            _subentry("Outer Lamp", ["light.inner_lamp"]),
        ],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    inner_id, outer_id = list(entry.subentries)
    assert _group_entity_id(hass, entry, inner_id) == "light.inner_lamp"
    members = hass.states.get(_all_entity_id(hass, entry)).attributes["entity_id"]
    assert members == [_group_entity_id(hass, entry, outer_id)]


from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from .helpers import setup_integration


async def test_group_created_after_subentry_added_at_runtime(hass):
    """Adding a group after setup creates its entity (entry reloads)."""
    hass.states.async_set("light.bulb_1", "on", {"supported_color_modes": ["onoff"], "color_mode": "onoff"})
    hass.states.async_set("light.bulb_2", "off", {"supported_color_modes": ["onoff"]})
    entry = await setup_integration(hass)  # no groups yet

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, GROUP_SUBENTRY_TYPE), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "Floor Lamp", "members": ["light.bulb_1", "light.bulb_2"]},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    eid = _group_entity_id(hass, entry)
    assert eid is not None
    assert hass.states.get(eid) is not None


async def test_switch_member_counts_toward_group_state(hass):
    """A switch member turns the group on like any light would."""
    hass.states.async_set("light.bulb_1", "off", {"supported_color_modes": ["brightness"]})
    hass.states.async_set("switch.sink", "on")
    entry = _entry_with_group(["light.bulb_1", "switch.sink"])
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(_group_entity_id(hass, entry)).state == "on"


async def test_switch_members_forwarded_to_switch_services(hass):
    """turn_on/off reach switch members via the switch domain, without kwargs."""
    from pytest_homeassistant_custom_component.common import async_mock_service

    hass.states.async_set("switch.sink", "off")
    entry = _entry_with_group(["switch.sink"])
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    eid = _group_entity_id(hass, entry)

    on_calls = async_mock_service(hass, "switch", "turn_on")
    off_calls = async_mock_service(hass, "switch", "turn_off")

    await hass.services.async_call(
        "light", "turn_on", {"entity_id": eid, "brightness": 128}, blocking=True
    )
    assert len(on_calls) == 1
    assert on_calls[0].data["entity_id"] == ["switch.sink"]
    assert "brightness" not in on_calls[0].data

    await hass.services.async_call("light", "turn_off", {"entity_id": eid}, blocking=True)
    assert len(off_calls) == 1
    assert off_calls[0].data["entity_id"] == ["switch.sink"]


async def test_onoff_group_reports_onoff_and_strips_brightness(hass):
    """A group flagged on/off-only presents as a toggle and never dims."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    hass.states.async_set(
        "light.dimmer", "on",
        {"brightness": 200, "supported_color_modes": ["brightness"], "color_mode": "brightness",
         "supported_features": 32},
    )
    entry = MockConfigEntry(
        domain=DOMAIN, title="Test Room", data={},
        subentries_data=[ConfigSubentryData(
            subentry_type=GROUP_SUBENTRY_TYPE, title="Extractor",
            data={"name": "Extractor", "members": ["light.dimmer"], "onoff": True},
            unique_id=None,
        )],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    eid = _group_entity_id(hass, entry)
    state = hass.states.get(eid)
    assert state.attributes["supported_color_modes"] == ["onoff"]
    assert state.attributes.get("brightness") is None

    seen = []
    hass.bus.async_listen("call_service", lambda e: seen.append(e.data))
    await hass.services.async_call(
        "light", "turn_on", {"entity_id": eid, "brightness_pct": 40, "transition": 2}, blocking=True
    )
    await hass.async_block_till_done()
    forwarded = [
        d for d in seen
        if d["domain"] == "light" and d["service"] == "turn_on"
        and d["service_data"].get("entity_id") == ["light.dimmer"]
    ]
    assert len(forwarded) == 1
    data = forwarded[0]["service_data"]
    assert "brightness_pct" not in data and "brightness" not in data
    assert data.get("transition") == 2
