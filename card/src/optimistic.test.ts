import { describe, it, expect } from 'vitest';
import { applyPending, isSettled, type Pending } from './optimistic';
import type { LightNode } from './types';

const leaf = (id: string, on: boolean, brightness: number | null = null): LightNode =>
  ({ entity_id: id, name: id, isGroup: false, on, brightness, children: [] });

const group = (id: string, on: boolean, brightness: number | null, children: LightNode[]): LightNode =>
  ({ entity_id: id, name: id, isGroup: true, on, brightness, children });

const tree = () =>
  group('light.area', true, 200, [
    group('light.lamp', true, 200, [leaf('light.bulb_1', true, 200), leaf('light.bulb_2', true, 200)]),
    leaf('light.side', false),
  ]);

describe('applyPending', () => {
  it('returns the tree untouched when nothing is pending', () => {
    const t = tree();
    expect(applyPending(t, new Map())).toBe(t);
  });

  it('pushes a change down to every light under the one that was touched', () => {
    const pending = new Map<string, Pending>([['light.lamp', { on: false, brightness: null }]]);
    const out = applyPending(tree(), pending);
    const lamp = out.children[0];
    expect(lamp.on).toBe(false);
    expect(lamp.children.every((c) => !c.on)).toBe(true);
  });

  it('re-derives the groups above it instead of trusting their stale state', () => {
    // The area entity still reads "on" in HA; with its only lit branch turned
    // off, the card must show it off immediately.
    const pending = new Map<string, Pending>([['light.lamp', { on: false, brightness: null }]]);
    expect(applyPending(tree(), pending).on).toBe(false);
  });

  it('averages the brightness of the lights still on', () => {
    const pending = new Map<string, Pending>([['light.bulb_1', { on: true, brightness: 100 }]]);
    const out = applyPending(tree(), pending);
    expect(out.children[0].brightness).toBe(150); // (100 + 200) / 2
    expect(out.brightness).toBe(150);
  });

  it('leaves branches without a pending change alone', () => {
    const t = tree();
    const pending = new Map<string, Pending>([['light.bulb_1', { on: false, brightness: null }]]);
    expect(applyPending(t, pending).children[1]).toBe(t.children[1]);
  });
});

describe('isSettled', () => {
  it('needs the power state to match', () => {
    expect(isSettled({ on: true, brightness: 200 }, { on: false, brightness: null })).toBe(false);
  });
  it('accepts a brightness that is close enough', () => {
    expect(isSettled({ on: true, brightness: 200 }, { on: true, brightness: 194 })).toBe(true);
    expect(isSettled({ on: true, brightness: 200 }, { on: true, brightness: 150 })).toBe(false);
  });
  it('ignores brightness once off', () => {
    expect(isSettled({ on: false, brightness: null }, { on: false, brightness: 200 })).toBe(true);
  });
});
