"""Config flow and subentry tests."""
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.grouped_lights.const import DOMAIN


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
