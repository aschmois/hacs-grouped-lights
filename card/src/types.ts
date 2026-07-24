export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, any>;
}

export interface HassLike {
  states: Record<string, HassEntity | undefined>;
  callService(domain: string, service: string, data?: Record<string, unknown>): Promise<unknown>;
}

export interface CardConfig {
  type: string;
  entity?: string; // the root/master group light to render
  title?: string;  // optional heading; defaults to the root's friendly name
}

export interface LightNode {
  entity_id: string;
  name: string;
  isGroup: boolean;          // has an `entity_id` member attribute
  on: boolean;
  brightness: number | null; // 0-255, or null when off/unknown
  children: LightNode[];
}
