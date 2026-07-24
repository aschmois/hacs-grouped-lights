import { describe, it, expect, vi, beforeEach } from 'vitest';
import './card';
import type { HassLike } from './types';

const STATES: Record<string, any> = {
  'light.room_lamps': { entity_id: 'light.room_lamps', state: 'on',
    attributes: { friendly_name: 'Room Lamps', brightness: 128, entity_id: ['light.floor_lamp', 'light.table_lamp_left'] } },
  'light.floor_lamp': { entity_id: 'light.floor_lamp', state: 'on',
    attributes: { friendly_name: 'Floor Lamp', brightness: 200, entity_id: ['light.bulb_1'] } },
  'light.bulb_1': { entity_id: 'light.bulb_1', state: 'on', attributes: { friendly_name: 'Bulb 1', brightness: 200 } },
  'light.table_lamp_left': { entity_id: 'light.table_lamp_left', state: 'off', attributes: { friendly_name: 'Table Lamp Left' } },
};

function mkHass(): HassLike & { callService: any } {
  return { states: STATES, callService: vi.fn().mockResolvedValue(undefined) };
}

async function mount(config: any, hass: HassLike) {
  const el = document.createElement('grouped-lights-card') as any;
  el.setConfig(config);
  el.hass = hass;
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

beforeEach(() => { document.body.innerHTML = ''; });

describe('grouped-lights-card', () => {
  it('setConfig requires an entity', () => {
    const el = document.createElement('grouped-lights-card') as any;
    expect(() => el.setConfig({ type: 'grouped-lights-card' })).toThrow();
  });

  it('renders a row per top-level member (collapsed by default)', async () => {
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, mkHass());
    const names = [...el.shadowRoot.querySelectorAll('.nm')].map((n: any) => n.textContent);
    // master header + two children; the group is collapsed so bulb_1 is hidden
    expect(names).toContain('Floor Lamp');
    expect(names).toContain('Table Lamp Left');
    expect(names).not.toContain('Bulb 1');
  });

  it('expands a group to reveal its children', async () => {
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, mkHass());
    const chev = el.shadowRoot.querySelector('[data-expand="light.floor_lamp"]');
    chev.click();
    await el.updateComplete;
    const names = [...el.shadowRoot.querySelectorAll('.nm')].map((n: any) => n.textContent);
    expect(names).toContain('Bulb 1');
  });

  it('toggles power via a service call', async () => {
    const hass = mkHass();
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, hass);
    const dot = el.shadowRoot.querySelector('[data-toggle="light.table_lamp_left"]');
    dot.click();
    expect(hass.callService).toHaveBeenCalledWith('light', 'turn_on', { entity_id: 'light.table_lamp_left' });
  });

  it('fires hass-more-info from the info button', async () => {
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, mkHass());
    const handler = vi.fn();
    el.addEventListener('hass-more-info', handler);
    el.shadowRoot.querySelector('[data-info="light.floor_lamp"]').click();
    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail).toEqual({ entityId: 'light.floor_lamp' });
  });

  it('renders each top-level row exactly once and the master has no expand chevron', async () => {
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, mkHass());
    const names = () => [...el.shadowRoot.querySelectorAll('.nm')].map((n: any) => n.textContent);
    expect(names().filter((n: string) => n === 'Floor Lamp')).toHaveLength(1);
    expect(names().filter((n: string) => n === 'Table Lamp Left')).toHaveLength(1);
    // The master (root) row is a header, not an expandable group: no chevron for it.
    expect(el.shadowRoot.querySelector('[data-expand="light.room_lamps"]')).toBeNull();

    // Expanding a deeper sub-group (Floor Lamp -> Bulb 1) must not duplicate the
    // top-level rows that render via render()'s explicit `root.children.map(...)`.
    el.shadowRoot.querySelector('[data-expand="light.floor_lamp"]').click();
    await el.updateComplete;
    expect(names().filter((n: string) => n === 'Floor Lamp')).toHaveLength(1);
    expect(names().filter((n: string) => n === 'Table Lamp Left')).toHaveLength(1);
    expect(names().filter((n: string) => n === 'Bulb 1')).toHaveLength(1);
  });

  it('ignores a pointerdown that targets a child control (does not set brightness)', async () => {
    const hass = mkHass();
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, hass);
    const dot = el.shadowRoot.querySelector('[data-toggle="light.floor_lamp"]');
    // jsdom doesn't implement a PointerEvent constructor; a plain Event with
    // type "pointerdown" is dispatched the same way a real PointerEvent would be
    // (listeners match on event.type, not the constructor), and the guard in
    // _onRowPointer returns before touching pointer-specific fields like clientX.
    dot.dispatchEvent(new Event('pointerdown', { bubbles: true }));
    const brightnessCalls = hass.callService.mock.calls.filter(
      (args: any[]) => args[2] && Object.prototype.hasOwnProperty.call(args[2], 'brightness_pct'),
    );
    expect(brightnessCalls).toHaveLength(0);
  });
});
