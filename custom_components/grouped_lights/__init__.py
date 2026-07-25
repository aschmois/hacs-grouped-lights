"""Grouped Lights — plugin-owned nested light groups."""
from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]

CARD_URL = "/grouped_lights/grouped-lights-card.js"
CARD_PATH = os.path.join(os.path.dirname(__file__), "frontend", "grouped-lights-card.js")
DATA_CARD_REGISTERED = "grouped_lights_card_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grouped Lights from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Reload when a group subentry is added / edited / removed so its light
    # entity is (re)created or torn down.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await _async_register_card_once(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the entry's platforms."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its subentries change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the Lovelace resource once the last area is removed."""
    if any(e.entry_id != entry.entry_id for e in hass.config_entries.async_entries(DOMAIN)):
        return  # other areas still need the card
    hass.data.pop(DATA_CARD_REGISTERED, None)
    resources = _lovelace_storage_resources(hass)
    if resources is None:
        return
    try:
        await resources.async_get_info()  # ensure the collection is loaded
        for item in list(resources.async_items()):
            if str(item.get("url", "")).split("?")[0] == CARD_URL:
                await resources.async_delete_item(item["id"])
    except Exception as err:  # noqa: BLE001 - best-effort cleanup
        _LOGGER.debug("Grouped Lights: could not remove the card resource: %s", err)


async def _async_register_card_once(hass: HomeAssistant) -> None:
    """Serve + register the bundled card exactly once per HA process (survives reloads)."""
    if hass.data.get(DATA_CARD_REGISTERED):
        return
    if not os.path.exists(CARD_PATH) or hass.http is None:
        return
    # Claim the slot before awaiting so two areas setting up at once cannot both
    # register; released again if serving the file fails, so a later area retries.
    hass.data[DATA_CARD_REGISTERED] = True
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, CARD_PATH, False)]
        )
    except Exception as err:  # noqa: BLE001 - card is optional; lights must still work
        hass.data[DATA_CARD_REGISTERED] = False
        _LOGGER.warning("Grouped Lights: could not register card static path: %s", err)
        return
    try:
        integration = await async_get_integration(hass, DOMAIN)
        card_url = f"{CARD_URL}?v={integration.version}"
    except Exception as err:  # noqa: BLE001 - fall back to the bare URL
        _LOGGER.debug("Grouped Lights: card resource registration fell back (%s)", err)
        card_url = CARD_URL
    await _async_register_card_resource(hass, card_url)


async def _async_register_card_resource(hass: HomeAssistant, card_url: str) -> None:
    """Make the card load on every dashboard, including the companion app.

    A Lovelace *resource* (storage mode) is loaded by the frontend at runtime
    from the resource list, exactly like a HACS frontend plugin, so it survives
    the mobile app's precached app-shell. `add_extra_js_url` only injects the
    module into the server-rendered index — invisible to the app — so it is the
    fallback for when there is no storage collection to write to (YAML resource
    mode, or Lovelace not set up).
    """
    resources = _lovelace_storage_resources(hass)
    if resources is not None:
        try:
            await _async_upsert_card_resource(resources, card_url)
            return
        except Exception as err:  # noqa: BLE001 - degrade to index injection
            _LOGGER.warning(
                "Grouped Lights: could not register the card as a Lovelace resource "
                "(%s); falling back to a frontend extra module URL",
                err,
            )
    try:
        add_extra_js_url(hass, card_url)
    except Exception as err:  # noqa: BLE001 - card is optional; entry setup must not fail
        _LOGGER.debug("Grouped Lights: could not register extra JS url (%s)", err)


async def _async_upsert_card_resource(resources, card_url: str) -> None:
    """Create or version-bump our single card resource (dedupe by base URL)."""
    await resources.async_get_info()  # ensures the collection is loaded
    existing = next(
        (
            item
            for item in resources.async_items()
            if str(item.get("url", "")).split("?")[0] == CARD_URL
        ),
        None,
    )
    if existing is None:
        await resources.async_create_item({"res_type": "module", "url": card_url})
    elif existing.get("url") != card_url:
        await resources.async_update_item(existing["id"], {"url": card_url})


def _lovelace_storage_resources(hass: HomeAssistant):
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
    except ImportError:
        return None
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None or getattr(lovelace, "resource_mode", None) != "storage":
        return None
    return getattr(lovelace, "resources", None)
