"""Integration setup/unload lifecycle."""
from homeassistant.config_entries import ConfigEntryState

from .helpers import setup_integration


async def test_setup_and_unload_entry(hass):
    """Setting up the entry loads it; unloading returns it to NOT_LOADED."""
    entry = await setup_integration(hass)
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
