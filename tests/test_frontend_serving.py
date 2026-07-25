"""The integration serves the card and makes it load, including on mobile.

The card is registered as a Lovelace *resource* (storage mode) so the frontend
loads it at runtime like a HACS plugin — the companion app serves a precached
app-shell, so a module injected into the server-rendered index (what
``add_extra_js_url`` does) never reaches it. That fallback is only for when
there is no storage collection to write to.
"""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grouped_lights import (
    CARD_PATH,
    CARD_URL,
    DATA_CARD_REGISTERED,
    async_remove_entry,
)
from custom_components.grouped_lights.const import DOMAIN

from .helpers import setup_integration


class _FakeResources:
    """Minimal stand-in for Lovelace's ResourceStorageCollection."""

    def __init__(self, items=None):
        self._items = list(items or [])
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []
        self.deleted: list[str] = []

    async def async_get_info(self):
        return {"resources": len(self._items)}

    def async_items(self):
        return list(self._items)

    async def async_create_item(self, data):
        item = {"id": "res1", "type": data["res_type"], "url": data["url"]}
        self._items.append(item)
        self.created.append(data)
        return item

    async def async_update_item(self, item_id, updates):
        self.updated.append((item_id, updates))
        for it in self._items:
            if it["id"] == item_id:
                it.update(updates)
        return {}

    async def async_delete_item(self, item_id):
        self.deleted.append(item_id)
        self._items = [it for it in self._items if it["id"] != item_id]


def _mock_http():
    http = MagicMock()
    http.async_register_static_paths = AsyncMock()
    return http


async def _setup(hass, *, lovelace=None):
    """Set up an area entry; returns (extra_js_urls_registered, http_mock)."""
    registered_urls: list[str] = []

    def _fake_add_extra_js_url(_hass, url, es5=False):
        registered_urls.append(url)

    if lovelace is not None:
        hass.data[LOVELACE_DATA] = lovelace

    entry = MockConfigEntry(domain=DOMAIN, title="Test Room", data={})
    entry.add_to_hass(hass)
    http = _mock_http()
    with (
        patch.object(hass, "http", http),
        patch(
            "custom_components.grouped_lights.add_extra_js_url",
            side_effect=_fake_add_extra_js_url,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return registered_urls, http


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


async def test_card_registered_as_lovelace_resource(hass):
    """In storage mode the card is a module resource — the path mobile can load."""
    resources = _FakeResources()
    lovelace = SimpleNamespace(resource_mode="storage", resources=resources)

    registered_urls, _ = await _setup(hass, lovelace=lovelace)

    assert len(resources.created) == 1, "card was not registered as a resource"
    created = resources.created[0]
    assert created["res_type"] == "module"
    assert created["url"].split("?")[0] == CARD_URL
    assert "?v=" in created["url"], "resource URL should carry a version cache-buster"
    # Must NOT also inject into the index — that would double-load the module.
    assert registered_urls == [], (
        f"add_extra_js_url should not be used in storage mode: {registered_urls}"
    )


async def test_stale_resource_is_version_bumped_not_duplicated(hass):
    resources = _FakeResources(
        items=[{"id": "old", "type": "module", "url": f"{CARD_URL}?v=0.0.1"}]
    )
    lovelace = SimpleNamespace(resource_mode="storage", resources=resources)

    await _setup(hass, lovelace=lovelace)

    assert resources.created == [], "should update in place, not create a duplicate"
    assert len(resources.updated) == 1
    item_id, updates = resources.updated[0]
    assert item_id == "old"
    assert updates["url"].split("?")[0] == CARD_URL
    assert updates["url"] != f"{CARD_URL}?v=0.0.1"


async def test_current_resource_is_left_alone(hass):
    from custom_components.grouped_lights import async_get_integration

    integration = await async_get_integration(hass, DOMAIN)
    current = f"{CARD_URL}?v={integration.version}"
    resources = _FakeResources(items=[{"id": "cur", "type": "module", "url": current}])
    lovelace = SimpleNamespace(resource_mode="storage", resources=resources)

    await _setup(hass, lovelace=lovelace)

    assert resources.created == []
    assert resources.updated == []


async def test_falls_back_to_extra_js_without_lovelace(hass):
    registered_urls, _ = await _setup(hass)
    assert any(u.split("?")[0] == CARD_URL for u in registered_urls), (
        f"fallback did not register the card URL: {registered_urls}"
    )


async def test_falls_back_in_yaml_resource_mode(hass):
    resources = _FakeResources()
    lovelace = SimpleNamespace(resource_mode="yaml", resources=resources)

    registered_urls, _ = await _setup(hass, lovelace=lovelace)

    assert resources.created == [], "must not write to a YAML resource collection"
    assert any(u.split("?")[0] == CARD_URL for u in registered_urls)


async def test_removing_the_last_area_deletes_the_resource(hass):
    resources = _FakeResources(
        items=[
            {"id": "ours", "type": "module", "url": f"{CARD_URL}?v=0.4.0"},
            {"id": "other", "type": "module", "url": "/hacsfiles/other/other.js"},
        ]
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(resource_mode="storage", resources=resources)
    entry = MockConfigEntry(domain=DOMAIN, title="Test Room", data={})
    entry.add_to_hass(hass)

    await async_remove_entry(hass, entry)

    assert resources.deleted == ["ours"]
    assert [it["id"] for it in resources.async_items()] == ["other"]


async def test_removing_one_of_several_areas_keeps_the_resource(hass):
    """Areas are separate config entries; the card is shared between them."""
    resources = _FakeResources(
        items=[{"id": "ours", "type": "module", "url": f"{CARD_URL}?v=0.4.0"}]
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(resource_mode="storage", resources=resources)
    first = MockConfigEntry(domain=DOMAIN, title="Test Room", data={})
    first.add_to_hass(hass)
    second = MockConfigEntry(domain=DOMAIN, title="Second Room", data={})
    second.add_to_hass(hass)

    await async_remove_entry(hass, first)

    assert resources.deleted == []
