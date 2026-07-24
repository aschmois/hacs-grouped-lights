"""Shared test helpers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grouped_lights.const import DOMAIN


async def setup_integration(
    hass: HomeAssistant, entry: MockConfigEntry | None = None
) -> MockConfigEntry:
    """Create (if needed), register, and set up a config entry."""
    if entry is None:
        entry = MockConfigEntry(domain=DOMAIN, title="Test Room", data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
