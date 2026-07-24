import { describe, it, expect } from 'vitest';
import { buildTree, memberIds, friendlyName } from './tree';
import type { HassLike } from './types';

function hass(states: Record<string, any>): HassLike {
  return { states, callService: async () => undefined };
}

const ROOM: Record<string, any> = {
  'light.room_lamps': { entity_id: 'light.room_lamps', state: 'on',
    attributes: { friendly_name: 'Room Lamps',
      entity_id: ['light.floor_lamp', 'light.table_lamp_left'] } },
  'light.floor_lamp': { entity_id: 'light.floor_lamp', state: 'on',
    attributes: { friendly_name: 'Floor Lamp', brightness: 200,
      entity_id: ['light.bulb_1', 'light.bulb_2'] } },
  'light.bulb_1': { entity_id: 'light.bulb_1', state: 'on', attributes: { friendly_name: 'Bulb 1', brightness: 200 } },
  'light.bulb_2': { entity_id: 'light.bulb_2', state: 'off', attributes: { friendly_name: 'Bulb 2' } },
  'light.table_lamp_left': { entity_id: 'light.table_lamp_left', state: 'off', attributes: { friendly_name: 'Table Lamp Left' } },
};

describe('buildTree', () => {
  it('builds the nested area -> lamp -> bulb tree', () => {
    const root = buildTree(hass(ROOM), 'light.room_lamps')!;
    expect(root.name).toBe('Room Lamps');
    expect(root.isGroup).toBe(true);
    expect(root.children.map((c) => c.entity_id)).toEqual(['light.floor_lamp', 'light.table_lamp_left']);
    const floor = root.children[0];
    expect(floor.isGroup).toBe(true);
    expect(floor.brightness).toBe(200);
    expect(floor.children.map((c) => c.entity_id)).toEqual(['light.bulb_1', 'light.bulb_2']);
    expect(floor.children[0].isGroup).toBe(false); // leaf bulb
    expect(root.children[1].isGroup).toBe(false);   // single-bulb lamp
  });

  it('marks on/off and brightness from state', () => {
    const root = buildTree(hass(ROOM), 'light.room_lamps')!;
    expect(root.on).toBe(true);
    expect(root.children[0].children[1].on).toBe(false); // bulb_2 off
    expect(root.children[0].children[1].brightness).toBeNull();
  });

  it('returns null for a missing root entity', () => {
    expect(buildTree(hass(ROOM), 'light.nope')).toBeNull();
  });

  it('guards against membership cycles', () => {
    const cyclic = { 'light.a': { entity_id: 'light.a', state: 'on', attributes: { entity_id: ['light.b'] } },
                     'light.b': { entity_id: 'light.b', state: 'on', attributes: { entity_id: ['light.a'] } } };
    const root = buildTree(hass(cyclic), 'light.a')!;
    expect(root.children[0].entity_id).toBe('light.b');
    expect(root.children[0].children).toEqual([]); // does not recurse back into light.a
  });

  it('memberIds/friendlyName helpers', () => {
    expect(memberIds(ROOM['light.floor_lamp'])).toEqual(['light.bulb_1', 'light.bulb_2']);
    expect(memberIds(ROOM['light.bulb_1'])).toEqual([]);
    expect(friendlyName(ROOM['light.bulb_2'])).toBe('Bulb 2');
    expect(friendlyName({ entity_id: 'light.x', state: 'on', attributes: {} })).toBe('light.x');
  });
});
