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


async def _add_group(hass, entry, name="Floor Lamp",
                     members=("light.bulb_1", "light.bulb_2")):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, GROUP_SUBENTRY_TYPE), context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": name, "members": list(members)}
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
    }


async def test_add_group_rejects_empty_members(hass):
    entry = await setup_integration(hass)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, GROUP_SUBENTRY_TYPE), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Empty", "members": []}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"members": "no_members"}


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
