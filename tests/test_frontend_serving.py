"""The integration serves and registers the bundled card."""
import os

from homeassistant.setup import async_setup_component

from custom_components.grouped_lights import CARD_PATH, CARD_URL, DATA_CARD_REGISTERED

from .helpers import setup_integration


async def test_card_static_path_registered(hass):
    """After setup, the card JS is registered as an HTTP static path."""
    # The bare `hass` fixture has no `http` component (hass.http is None), unlike a real
    # HA process where core `http` is always loaded before custom integrations. Set it up
    # here so the registration path actually runs instead of hitting its no-op guard.
    assert await async_setup_component(hass, "http", {})
    await hass.async_block_till_done()

    await setup_integration(hass)
    assert CARD_URL == "/grouped_lights/grouped-lights-card.js"
    assert os.path.exists(CARD_PATH)
    # Proves the registration path actually ran (not a silent hass.http-is-None no-op).
    assert hass.data.get(DATA_CARD_REGISTERED) is True
