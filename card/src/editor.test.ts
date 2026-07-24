import { describe, it, expect, vi, beforeEach } from 'vitest';
import './editor';

async function mount() {
  const el = document.createElement('grouped-lights-card-editor') as any;
  el.setConfig({ type: 'grouped-lights-card', entity: 'light.room_lamps' });
  el.hass = { states: {}, callService: async () => undefined };
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

beforeEach(() => { document.body.innerHTML = ''; });

describe('grouped-lights-card-editor', () => {
  it('renders an entity selector and a title field', async () => {
    const el = await mount();
    const selectors = el.shadowRoot.querySelectorAll('ha-selector');
    expect(selectors.length).toBe(2);
  });

  it('emits config-changed when a field changes', async () => {
    const el = await mount();
    const handler = vi.fn();
    el.addEventListener('config-changed', handler);
    const entitySel = el.shadowRoot.querySelector('ha-selector');
    entitySel.dispatchEvent(new CustomEvent('value-changed', { detail: { value: 'light.other' } }));
    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail.config.entity).toBe('light.other');
  });
});
