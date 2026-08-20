"""Config flow and subentry tests."""
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER  # used in Task 4
from homeassistant.data_entry_flow import FlowResultType

from custom_components.grouped_lights.const import DOMAIN, GROUP_SUBENTRY_TYPE
from .helpers import setup_integration


async def test_user_flow_creates_entry(hass):
    """The user step names the area and creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Test Room"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Room"
    assert result["data"] == {}


async def test_multiple_entries_allowed(hass):
    """A second area can be added (integration is not single-instance)."""
    for name in ("Test Room", "Second Room"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"name": name}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2


async def _submit_group(hass, entry, user_input):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, GROUP_SUBENTRY_TYPE), context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input
    )


async def _add_group(hass, entry, name="Floor Lamp",
                     members=("light.bulb_1", "light.bulb_2")):
    return await _submit_group(
        hass, entry, {"name": name, "members": list(members)}
    )


async def test_add_group_subentry_stores_members(hass):
    entry = await setup_integration(hass)
    result = await _add_group(hass, entry)
    assert result["type"] == FlowResultType.CREATE_ENTRY

    subentry = next(iter(entry.subentries.values()))
    assert subentry.subentry_type == GROUP_SUBENTRY_TYPE
    assert subentry.title == "Floor Lamp"
    assert subentry.data == {
        "name": "Floor Lamp",
        "members": ["light.bulb_1", "light.bulb_2"],
        "icon": "mdi:lightbulb-group",
        "onoff": False,
    }


async def test_add_group_rejects_empty_members(hass):
    entry = await setup_integration(hass)
    result = await _submit_group(hass, entry, {"name": "Empty", "members": []})
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"members": "no_members"}


async def test_single_member_name_defaults_to_the_light(hass):
    """One light + no name: borrow the light's friendly name and bulb icon."""
    hass.states.async_set("light.bulb_1", "off", {"friendly_name": "Desk Bulb"})
    entry = await setup_integration(hass)
    result = await _submit_group(hass, entry, {"members": ["light.bulb_1"]})
    assert result["type"] == FlowResultType.CREATE_ENTRY

    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "Desk Bulb"
    assert subentry.data == {
        "name": "Desk Bulb",
        "members": ["light.bulb_1"],
        "icon": "mdi:lightbulb",
        "onoff": False,
    }


async def test_single_member_name_falls_back_to_entity_id(hass):
    """No state, no registry entry: prettify the object_id."""
    entry = await setup_integration(hass)
    result = await _submit_group(hass, entry, {"members": ["light.bulb_1"]})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert next(iter(entry.subentries.values())).data["name"] == "Bulb 1"


async def test_multiple_members_require_a_name(hass):
    entry = await setup_integration(hass)
    result = await _submit_group(
        hass, entry, {"members": ["light.bulb_1", "light.bulb_2"]}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"name": "name_required"}


async def test_blank_name_is_treated_as_missing(hass):
    entry = await setup_integration(hass)
    result = await _submit_group(
        hass, entry, {"name": "   ", "members": ["light.bulb_1", "light.bulb_2"]}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"name": "name_required"}


async def test_explicit_icon_wins_over_the_default(hass):
    entry = await setup_integration(hass)
    result = await _submit_group(
        hass,
        entry,
        {"name": "Floor Lamp", "members": ["light.bulb_1"], "icon": "mdi:floor-lamp"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert next(iter(entry.subentries.values())).data["icon"] == "mdi:floor-lamp"


async def test_reconfigure_group_updates_members(hass):
    entry = await setup_integration(hass)
    await _add_group(hass, entry)
    subentry_id = next(iter(entry.subentries))

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, GROUP_SUBENTRY_TYPE),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
    )
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "Main Lamp", "members": ["light.bulb_1", "light.bulb_2", "light.bulb_3"]},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    subentry = entry.subentries[subentry_id]
    assert subentry.title == "Main Lamp"
    assert subentry.data["members"] == ["light.bulb_1", "light.bulb_2", "light.bulb_3"]
    assert subentry.data["icon"] == "mdi:lightbulb-group"


async def test_reconfigure_requires_a_name_for_multiple_members(hass):
    """The same name/icon rules apply when editing, not just adding."""
    entry = await setup_integration(hass)
    await _add_group(hass, entry)
    subentry_id = next(iter(entry.subentries))

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, GROUP_SUBENTRY_TYPE),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"members": ["light.bulb_1", "light.bulb_2"]}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"name": "name_required"}
