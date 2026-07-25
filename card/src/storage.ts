/**
 * Which rows are open is remembered per root entity, in the browser, so a
 * dashboard comes back the way it was left. Every accessor is defensive:
 * storage can be disabled or full, and the card must still work without it.
 */
const PREFIX = 'grouped-lights-card';

export function storageKey(rootEntityId: string): string {
  return `${PREFIX}:${rootEntityId}`;
}

function store(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null; // blocked by the browser (private mode, third-party cookies off)
  }
}

export function loadExpanded(key: string): Set<string> {
  try {
    const raw = store()?.getItem(key);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((v): v is string => typeof v === 'string'));
  } catch {
    return new Set(); // unreadable or corrupt: start collapsed
  }
}

export function saveExpanded(key: string, expanded: Set<string>): void {
  try {
    store()?.setItem(key, JSON.stringify([...expanded]));
  } catch {
    /* not persisting is fine; the card still works for this session */
  }
}
