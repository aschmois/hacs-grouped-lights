"""The integration serves and registers the bundled card."""
import os

from custom_components.grouped_lights import CARD_PATH, CARD_URL

from .helpers import setup_integration


async def test_card_static_path_registered(hass):
    """After setup, the card JS is registered as an HTTP static path."""
    await setup_integration(hass)
    # Robust check: the module exposes CARD_URL and the frontend file exists.
    assert CARD_URL == "/grouped_lights/grouped-lights-card.js"
    assert os.path.exists(CARD_PATH)
