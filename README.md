# Grouped Lights

A Home Assistant integration **and** Lovelace card that makes nested light groups a
first-class, plugin-owned concept. You define a hierarchy — an area's master group, the
lamps within it, and the individual bulbs within a lamp — and the integration creates the
corresponding `light` group entities. A bundled, LIFX-style card renders that hierarchy as
collapsible, row-as-slider controls.

> **Status:** design phase. See the design spec in
> [`docs/superpowers/specs/`](docs/superpowers/specs/2026-07-23-grouped-lights-card-design.md).

## Why

Home Assistant lets you build nested light-group helpers by hand, but they are tedious to
create and maintain, and the default dashboard UI does not present a lamp → bulb hierarchy
well. This plugin owns the group definitions (via config-flow subentries) and ships a card
designed specifically for controlling grouped lights at the area, lamp, or bulb level.

## Features (planned v1)

- Define groups as Home Assistant **config subentries**; the integration creates real
  `light` group entities from them, usable in automations, voice, and any dashboard.
- **LIFX-style card**: each row is a brightness slider, a dot toggles power, a chevron
  expands a group into its members, and an info button opens the entity's native
  more-info dialog for full color control.
- Collapsible **area → lamp → bulb** hierarchy, discovered from group membership.

## Installation

HACS custom repository (once released). Details to follow.

## License

[MIT](LICENSE)
