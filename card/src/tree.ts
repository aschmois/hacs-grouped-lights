import type { HassLike, HassEntity, LightNode } from './types';

export function friendlyName(e: HassEntity): string {
  const n = e.attributes?.friendly_name;
  return typeof n === 'string' && n ? n : e.entity_id;
}

export function memberIds(e: HassEntity | undefined): string[] {
  const m = e?.attributes?.entity_id;
  return Array.isArray(m) ? (m as string[]) : [];
}

function buildNode(hass: HassLike, entityId: string, seen: Set<string>): LightNode | null {
  const e = hass.states[entityId];
  if (!e) return null;
  const members = memberIds(e);
  const isGroup = members.length > 0;
  const nextSeen = new Set(seen).add(entityId);
  const children = members
    .filter((id) => !nextSeen.has(id))
    .map((id) => buildNode(hass, id, nextSeen))
    .filter((n): n is LightNode => n !== null);
  const brightness = typeof e.attributes?.brightness === 'number' ? e.attributes.brightness : null;
  // onoff-only lights (e.g. a group wrapping a wall switch) take taps, not drags.
  // Entities that don't report color modes are judged by whether they have ever
  // shown a brightness.
  const modes = e.attributes?.supported_color_modes;
  const dimmable = Array.isArray(modes) && modes.length
    ? modes.some((m: unknown) => m !== 'onoff')
    : brightness != null;
  return { entity_id: entityId, name: friendlyName(e), isGroup, on: e.state === 'on', brightness, dimmable, children };
}

export function buildTree(hass: HassLike, rootEntityId: string): LightNode | null {
  return buildNode(hass, rootEntityId, new Set());
}
