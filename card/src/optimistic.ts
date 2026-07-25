import type { LightNode } from './types';

/** A change the user just made, shown immediately while HA catches up. */
export interface Pending {
  on: boolean;
  brightness: number | null; // 0-255
}

/** How far a live brightness may sit from the requested one and still count as settled. */
export const BRIGHTNESS_TOLERANCE = 12;

function forceSubtree(node: LightNode, pending: Pending): LightNode {
  return {
    ...node,
    on: pending.on,
    brightness: pending.on ? pending.brightness : null,
    children: node.children.map((c) => forceSubtree(c, pending)),
  };
}

function aggregate(node: LightNode, children: LightNode[]): LightNode {
  const on = children.some((c) => c.on);
  const lit = children.filter((c) => c.on && c.brightness != null);
  const brightness = lit.length
    ? Math.round(lit.reduce((sum, c) => sum + (c.brightness as number), 0) / lit.length)
    : null;
  return { ...node, on, brightness, children };
}

function walk(node: LightNode, pending: Map<string, Pending>): [LightNode, boolean] {
  const own = pending.get(node.entity_id);
  if (own) return [forceSubtree(node, own), true];

  let touched = false;
  const children = node.children.map((child) => {
    const [next, childTouched] = walk(child, pending);
    touched = touched || childTouched;
    return next;
  });
  if (!touched) return [node, false];
  // A descendant moved, so re-derive this group rather than trusting the group
  // entity's state, which HA has not recomputed yet.
  return [aggregate(node, children), true];
}

/**
 * Overlay pending changes on the live tree: the touched light and everything
 * under it take the requested value, and the groups above it are re-derived
 * from their children. Returns the original node when nothing is pending.
 */
export function applyPending(node: LightNode, pending: Map<string, Pending>): LightNode {
  if (pending.size === 0) return node;
  return walk(node, pending)[0];
}

/** True once the live state matches what was asked for — time to drop the override. */
export function isSettled(pending: Pending, live: { on: boolean; brightness: number | null }): boolean {
  if (pending.on !== live.on) return false;
  if (!pending.on || pending.brightness == null || live.brightness == null) return true;
  return Math.abs(pending.brightness - live.brightness) <= BRIGHTNESS_TOLERANCE;
}
