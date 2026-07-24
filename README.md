# Grouped Lights

A Home Assistant integration **and** Lovelace card that make nested light groups a
first-class, plugin-owned concept. You define a hierarchy — an area's master group, the
lamps within it, and the individual bulbs within a lamp — and the integration creates the
matching `light` group entities. A bundled card renders that hierarchy as collapsible,
row-as-slider controls.

## Why

Home Assistant lets you build nested light-group helpers by hand, but they are tedious to
create and maintain, and the default dashboard UI does not present a lamp → bulb hierarchy
well. This plugin owns the group definitions (via config-flow subentries) and ships a card
designed specifically for controlling grouped lights at the area, lamp, or bulb level.

## The integration

- Add **Grouped Lights** from *Settings → Devices & Services* and name the area.
- Add a **group** (a config subentry): a name plus its member light entities. A group's
  members can include other groups, so you can nest **area → lamp → bulb**.
- Each group becomes a real `light.*` group entity (on if any member is on; brightness and
  color forwarded to members) — usable in automations, voice, and any dashboard, not just
  this card.

## The card

Add a card of type `custom:grouped-lights-card`:

```yaml
type: custom:grouped-lights-card
entity: light.room_lamps   # the master/root group to render
# title: Living Room       # optional; defaults to the entity's friendly name
```

Tap along a row to set its brightness; a dot toggles power; a chevron expands a group into
its members; and an info button opens the entity's native more-info dialog for full color,
effects, and history. The card is served and registered automatically by the integration —
no manual resource entry needed.

## Install (HACS)

Add this repository as a HACS **custom repository** (category: Integration), install
*Grouped Lights*, and restart Home Assistant. Requires Home Assistant **2026.2.3** or newer.

## Development

- **Card** (TypeScript / Lit): `cd card && npm install && npm test` (Vitest);
  `npm run build` bundles to `custom_components/grouped_lights/frontend/grouped-lights-card.js`.
- **Integration** (Python): tested with `pytest-homeassistant-custom-component` on Python
  3.13. On platforms without a C toolchain, run the suite in a Linux container.

## License

[MIT](LICENSE)
