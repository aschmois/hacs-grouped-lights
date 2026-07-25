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

/**
 * Mounts the card and, by default, opens the area row — the card now starts
 * fully collapsed, and most tests here are about what the rows do once shown.
 */
async function mount(config: any, hass: HassLike, { expandRoot = true } = {}) {
  const el = document.createElement('grouped-lights-card') as any;
  el.setConfig(config);
  el.hass = hass;
  document.body.appendChild(el);
  await el.updateComplete;
  if (expandRoot) {
    const chev = el.shadowRoot.querySelector(`[data-expand="${config.entity}"]`);
    if (chev) { chev.click(); await el.updateComplete; }
  }
  return el;
}

beforeEach(() => { document.body.innerHTML = ''; localStorage.clear(); });

describe('grouped-lights-card', () => {
  it('setConfig requires an entity', () => {
    const el = document.createElement('grouped-lights-card') as any;
    expect(() => el.setConfig({ type: 'grouped-lights-card' })).toThrow();
  });

  it('renders a row per top-level member, its sub-groups still closed', async () => {
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, mkHass());
    const names = [...el.shadowRoot.querySelectorAll('.nm')].map((n: any) => n.textContent);
    // area row + its two children; Floor Lamp is closed, so bulb_1 stays hidden
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

  it('renders each row exactly once, at every expansion level', async () => {
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, mkHass());
    const names = () => [...el.shadowRoot.querySelectorAll('.nm')].map((n: any) => n.textContent);
    expect(names().filter((n: string) => n === 'Floor Lamp')).toHaveLength(1);
    expect(names().filter((n: string) => n === 'Table Lamp Left')).toHaveLength(1);

    el.shadowRoot.querySelector('[data-expand="light.floor_lamp"]').click();
    await el.updateComplete;
    expect(names().filter((n: string) => n === 'Floor Lamp')).toHaveLength(1);
    expect(names().filter((n: string) => n === 'Table Lamp Left')).toHaveLength(1);
    expect(names().filter((n: string) => n === 'Bulb 1')).toHaveLength(1);
  });

  it('starts collapsed down to the area row, and expands from there', async () => {
    const config = { type: 'grouped-lights-card', entity: 'light.room_lamps' };
    const el = await mount(config, mkHass(), { expandRoot: false });
    const names = () => [...el.shadowRoot.querySelectorAll('.nm')].map((n: any) => n.textContent);
    expect(names()).toEqual(['Room Lamps']);

    const master = () => el.shadowRoot.querySelector('[data-expand="light.room_lamps"]');
    expect(master()).not.toBeNull();
    master().click();
    await el.updateComplete;
    expect(names()).toEqual(['Room Lamps', 'Floor Lamp', 'Table Lamp Left']);

    master().click();
    await el.updateComplete;
    expect(names()).toEqual(['Room Lamps']);
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

describe('brightness fill layout', () => {
  it('renders a fill sized to brightness for an on row, and none when off', async () => {
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, mkHass());
    const rows = [...el.shadowRoot.querySelectorAll('.row')];
    const fillOf = (row: Element) => row.querySelector('.fill') as HTMLElement | null;

    // master (brightness 128/255 -> 50%) has a fill; the off row has none, so its
    // border cannot paint a sliver at the left edge of the row.
    expect(fillOf(rows[0])!.style.width).toBe('50%');
    const offRow = rows.find((r) => r.querySelector('.nm')!.textContent === 'Table Lamp Left')!;
    expect(fillOf(offRow)).toBeNull();
  });

  it('keeps the fill out of the flex flow', async () => {
    // ".fill" and ".row > *" have equal specificity, so a bare ".row > *" rule
    // would win on order and override position:absolute — which pushed every
    // control to the right of the fill. The :not() is what prevents that.
    const css = (customElements.get('grouped-lights-card') as any).styles.cssText as string;
    expect(css).toContain('.row > *:not(.fill)');
    expect(css).not.toMatch(/\.row > \*\s*\{/);
  });
});

describe('responsiveness', () => {
  const rowFor = (el: any, name: string) =>
    [...el.shadowRoot.querySelectorAll('.row')].find(
      (r: any) => r.querySelector('.nm').textContent === name,
    ) as HTMLElement;
  const statusOf = (el: any, name: string) => rowFor(el, name).querySelector('.st')!.textContent;

  const withState = (hass: any, id: string, state: string, brightness: number | null) => ({
    ...hass,
    states: {
      ...hass.states,
      [id]: { entity_id: id, state, attributes: { friendly_name: hass.states[id].attributes.friendly_name,
        ...(brightness != null ? { brightness } : {}) } },
    },
  });

  const pointer = (type: string, clientX: number) =>
    Object.assign(new Event(type, { bubbles: true }), { clientX, pointerId: 1 });

  const stubWidth = (row: HTMLElement, width: number) => {
    row.getBoundingClientRect = () => ({ left: 0, width, top: 0, height: 50, right: width,
      bottom: 50, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
  };

  it('flips a row the instant it is tapped, without waiting for HA', async () => {
    const hass = mkHass();
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, hass);
    expect(statusOf(el, 'Table Lamp Left')).toBe('Off');

    el.shadowRoot.querySelector('[data-toggle="light.table_lamp_left"]').click();
    await el.updateComplete;

    expect(statusOf(el, 'Table Lamp Left')).toContain('On');
    // Nothing came back from HA — the row moved purely on the local override.
    expect(hass.states['light.table_lamp_left'].state).toBe('off');
  });

  it('re-derives the groups above the light that was tapped', async () => {
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, mkHass());
    // Floor Lamp is the master's only lit branch; switching it off must show the
    // master off too, even though HA still reports the group as on.
    el.shadowRoot.querySelector('[data-toggle="light.floor_lamp"]').click();
    await el.updateComplete;
    expect(statusOf(el, 'Room Lamps')).toBe('Off');
  });

  it('hands control back to HA once the reported state matches', async () => {
    const hass = mkHass();
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, hass);
    el.shadowRoot.querySelector('[data-toggle="light.table_lamp_left"]').click();
    await el.updateComplete;

    el.hass = withState(hass, 'light.table_lamp_left', 'on', 255); // HA confirms
    await el.updateComplete;
    el.hass = withState(hass, 'light.table_lamp_left', 'off', null); // and it goes off again
    await el.updateComplete;

    expect(statusOf(el, 'Table Lamp Left')).toBe('Off');
  });

  it('tracks a drag on screen while rate-limiting the service calls', async () => {
    const hass = mkHass();
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, hass);
    const row = rowFor(el, 'Floor Lamp');
    stubWidth(row, 200);
    const brightnessCalls = () => hass.callService.mock.calls.filter(
      (args: any[]) => args[2] && 'brightness_pct' in args[2]);

    row.dispatchEvent(pointer('pointerdown', 100));
    await el.updateComplete;
    expect(statusOf(el, 'Floor Lamp')).toBe('On · 50%');
    expect(brightnessCalls()).toHaveLength(1);

    row.dispatchEvent(pointer('pointermove', 150));
    await el.updateComplete;
    // The row follows the finger immediately; HA is not called again this soon.
    expect(statusOf(el, 'Floor Lamp')).toBe('On · 75%');
    expect(brightnessCalls()).toHaveLength(1);

    row.dispatchEvent(pointer('pointerup', 150));
    expect(brightnessCalls()).toHaveLength(2);
    expect(brightnessCalls()[1][2]).toEqual({ entity_id: 'light.floor_lamp', brightness_pct: 75 });
  });

  it('skips re-rendering when an entity it does not show changes', async () => {
    const hass = mkHass();
    const el = await mount({ type: 'grouped-lights-card', entity: 'light.room_lamps' }, hass);
    const render = vi.spyOn(el as any, 'render');

    el.hass = { ...hass, states: { ...hass.states,
      'sensor.elsewhere': { entity_id: 'sensor.elsewhere', state: '42', attributes: {} } } };
    await el.updateComplete;
    expect(render).not.toHaveBeenCalled();

    el.hass = withState(hass, 'light.bulb_1', 'on', 10);
    await el.updateComplete;
    expect(render).toHaveBeenCalled();
  });
});

describe('remembering what is open', () => {
  const CONFIG = { type: 'grouped-lights-card', entity: 'light.room_lamps' };
  const names = (el: any) => [...el.shadowRoot.querySelectorAll('.nm')].map((n: any) => n.textContent);

  it('restores the open rows — including how deep — on a fresh card', async () => {
    const first = await mount(CONFIG, mkHass());          // opens the area row
    first.shadowRoot.querySelector('[data-expand="light.floor_lamp"]').click();
    await first.updateComplete;
    expect(names(first)).toEqual(['Room Lamps', 'Floor Lamp', 'Bulb 1', 'Table Lamp Left']);

    document.body.innerHTML = '';
    const second = await mount(CONFIG, mkHass(), { expandRoot: false });
    expect(names(second)).toEqual(['Room Lamps', 'Floor Lamp', 'Bulb 1', 'Table Lamp Left']);
  });

  it('remembers a collapse too', async () => {
    const first = await mount(CONFIG, mkHass());
    first.shadowRoot.querySelector('[data-expand="light.room_lamps"]').click(); // collapse again
    await first.updateComplete;

    document.body.innerHTML = '';
    const second = await mount(CONFIG, mkHass(), { expandRoot: false });
    expect(names(second)).toEqual(['Room Lamps']);
  });

  it('keeps each area separate', async () => {
    await mount(CONFIG, mkHass());
    const other = await mount(
      { type: 'grouped-lights-card', entity: 'light.floor_lamp' }, mkHass(), { expandRoot: false });
    expect(names(other)).toEqual(['Floor Lamp']);
  });

  it('starts collapsed when the stored value is unusable', async () => {
    localStorage.setItem('grouped-lights-card:light.room_lamps', '{not json');
    const el = await mount(CONFIG, mkHass(), { expandRoot: false });
    expect(names(el)).toEqual(['Room Lamps']);
  });
});
