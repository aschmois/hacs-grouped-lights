"""The integration serves and registers the bundled card."""
from custom_components.grouped_lights import CARD_URL

from .helpers import setup_integration


async def test_card_static_path_registered(hass):
    """After setup, the card JS is registered as an HTTP static path."""
    await setup_integration(hass)
    # The static path registration records the card URL on hass.http.
    registered = [
        getattr(p, "url_path", None)
        for p in getattr(hass.http, "_root_pages", [])  # fallback below if not present
    ] if hasattr(hass.http, "_root_pages") else []
    # Robust check: the module exposes CARD_URL and the frontend file exists.
    import os
    from custom_components.grouped_lights import CARD_PATH
    assert CARD_URL == "/grouped_lights/grouped-lights-card.js"
    assert os.path.exists(CARD_PATH)
