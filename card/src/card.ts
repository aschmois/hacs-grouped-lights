import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HassLike, CardConfig, LightNode } from './types';
import { buildTree } from './tree';
import { applyPending, isSettled, type Pending } from './optimistic';

/** Don't hold an unconfirmed value forever if HA never reports it back. */
export const PENDING_TIMEOUT_MS = 5000;
/** Cap on how often a drag talks to HA; the UI itself follows the finger. */
export const SEND_INTERVAL_MS = 150;

@customElement('grouped-lights-card')
export class GroupedLightsCard extends LitElement {
  @property({ attribute: false }) public hass?: HassLike;
  @state() private _config?: CardConfig;
  @state() private _expanded = new Set<string>();
  /** Changes made locally, shown at once instead of waiting for the bulbs. */
  @state() private _pending = new Map<string, Pending>();
  @state() private _dragging: string | null = null;

  private _drag: { entityId: string; row: HTMLElement } | null = null;
  private _lastSend = 0;
  private _timers = new Map<string, ReturnType<typeof setTimeout>>();
  private _shown = new Set<string>();

  public setConfig(config: CardConfig): void {
    if (!config || !config.entity) throw new Error('grouped-lights-card: "entity" is required');
    this._config = config;
  }
  public getCardSize(): number { return 4; }
  public static getStubConfig(): Partial<CardConfig> { return { entity: '' }; }
  public static getConfigElement(): HTMLElement { return document.createElement('grouped-lights-card-editor'); }

  public disconnectedCallback(): void {
    super.disconnectedCallback();
    this._timers.forEach((t) => clearTimeout(t));
    this._timers.clear();
  }

  protected shouldUpdate(changed: PropertyValues): boolean {
    if (!changed.has('hass') || changed.size > 1) return true;
    const old = changed.get('hass') as HassLike | undefined;
    if (!old || !this.hass || this._shown.size === 0) return true;
    // HA hands every card a new `hass` on any state change anywhere in the
    // instance. Re-render only when a light this card actually shows moved.
    return [...this._shown].some((id) => old.states[id] !== this.hass!.states[id]);
  }

  protected willUpdate(changed: PropertyValues): void {
    if (!changed.has('hass') || !this.hass || this._pending.size === 0) return;
    for (const [id, pending] of this._pending) {
      const live = this.hass.states[id];
      if (!live) continue;
      const brightness = typeof live.attributes?.brightness === 'number' ? live.attributes.brightness : null;
      if (isSettled(pending, { on: live.state === 'on', brightness })) this._clearPending(id);
    }
  }

  private _setPending(entityId: string, pending: Pending): void {
    const next = new Map(this._pending);
    next.set(entityId, pending);
    this._pending = next;
    clearTimeout(this._timers.get(entityId));
    this._timers.set(entityId, setTimeout(() => this._clearPending(entityId), PENDING_TIMEOUT_MS));
  }

  private _clearPending(entityId: string): void {
    clearTimeout(this._timers.get(entityId));
    this._timers.delete(entityId);
    if (!this._pending.has(entityId)) return;
    const next = new Map(this._pending);
    next.delete(entityId);
    this._pending = next;
  }

  private _toggle(node: LightNode): void {
    const on = !node.on;
    this._setPending(node.entity_id, { on, brightness: on ? node.brightness ?? 255 : null });
    this.hass?.callService('light', on ? 'turn_on' : 'turn_off', { entity_id: node.entity_id });
  }

  private _setBrightness(entityId: string, pct: number, send: boolean): void {
    if (!Number.isFinite(pct)) return;
    const clamped = Math.max(0, Math.min(100, Math.round(pct)));
    this._setPending(entityId, { on: clamped > 0, brightness: Math.round((clamped / 100) * 255) });
    const now = Date.now();
    if (!send && now - this._lastSend < SEND_INTERVAL_MS) return;
    this._lastSend = now;
    if (clamped === 0) this.hass?.callService('light', 'turn_off', { entity_id: entityId });
    else this.hass?.callService('light', 'turn_on', { entity_id: entityId, brightness_pct: clamped });
  }

  private _moreInfo(entityId: string): void {
    this.dispatchEvent(new CustomEvent('hass-more-info', { detail: { entityId }, bubbles: true, composed: true }));
  }
  private _toggleExpand(entityId: string): void {
    const next = new Set(this._expanded);
    next.has(entityId) ? next.delete(entityId) : next.add(entityId);
    this._expanded = next;
  }

  private _pct(e: PointerEvent, row: HTMLElement): number {
    const rect = row.getBoundingClientRect();
    return rect.width ? ((e.clientX - rect.left) / rect.width) * 100 : NaN;
  }

  private _onRowDown(e: PointerEvent, node: LightNode): void {
    // Row-as-slider: dragging across the row body sets brightness from the
    // horizontal pointer position. Taps on the dot/chevron/info controls have
    // their own @click listeners and must not also move the slider.
    if ((e.target as HTMLElement).closest('.dot,.chev,.info')) return;
    const row = e.currentTarget as HTMLElement;
    row.setPointerCapture?.(e.pointerId);
    this._drag = { entityId: node.entity_id, row };
    this._dragging = node.entity_id;
    this._setBrightness(node.entity_id, this._pct(e, row), true);
  }

  private _onRowMove(e: PointerEvent): void {
    if (!this._drag) return;
    // Throttled toward HA, unthrottled on screen: the fill tracks the finger.
    this._setBrightness(this._drag.entityId, this._pct(e, this._drag.row), false);
  }

  private _onRowUp(e: PointerEvent): void {
    const drag = this._drag;
    if (!drag) return;
    this._drag = null;
    this._dragging = null;
    drag.row.releasePointerCapture?.(e.pointerId);
    this._setBrightness(drag.entityId, this._pct(e, drag.row), true);
  }

  private _row(node: LightNode, depth: number, expandable = true): unknown {
    const pct = node.on && node.brightness != null ? Math.round((node.brightness / 255) * 100) : (node.on ? 100 : 0);
    const st = node.on ? `On · ${pct}%` : 'Off';
    const expanded = expandable && this._expanded.has(node.entity_id);
    return html`
      <div class="row ${node.on ? 'on' : ''} ${this._dragging === node.entity_id ? 'dragging' : ''}"
        style="--depth:${depth}"
        @pointerdown=${(e: PointerEvent) => this._onRowDown(e, node)}
        @pointermove=${(e: PointerEvent) => this._onRowMove(e)}
        @pointerup=${(e: PointerEvent) => this._onRowUp(e)}
        @pointercancel=${(e: PointerEvent) => this._onRowUp(e)}>
        ${node.on && pct > 0 ? html`<div class="fill" style="width:${pct}%"></div>` : nothing}
        ${node.isGroup && expandable
          ? html`<button class="chev" data-expand=${node.entity_id}
              @click=${(e: Event) => { e.stopPropagation(); this._toggleExpand(node.entity_id); }}>${expanded ? '▾' : '▸'}</button>`
          : html`<span class="chev spacer"></span>`}
        <button class="dot ${node.on ? 'on' : ''}" data-toggle=${node.entity_id}
          @click=${(e: Event) => { e.stopPropagation(); this._toggle(node); }}></button>
        <div class="meta"><div class="nm">${node.name}</div><div class="st">${st}</div></div>
        <button class="info" data-info=${node.entity_id}
          @click=${(e: Event) => { e.stopPropagation(); this._moreInfo(node.entity_id); }}>ⓘ</button>
      </div>
      ${node.isGroup && expanded ? node.children.map((c) => this._row(c, depth + 1)) : nothing}
    `;
  }

  private _collect(node: LightNode, into: Set<string>): void {
    into.add(node.entity_id);
    node.children.forEach((c) => this._collect(c, into));
  }

  protected render(): unknown {
    if (!this.hass || !this._config?.entity) return nothing;
    const live = buildTree(this.hass, this._config.entity);
    if (!live) return html`<ha-card><div class="err">Entity ${this._config.entity} not found</div></ha-card>`;
    this._shown = new Set();
    this._collect(live, this._shown);
    const root = applyPending(live, this._pending);
    const title = this._config.title ?? root.name;
    return html`<ha-card>
      <div class="head">${title}</div>
      ${this._row(root, 0, false)}
      ${root.children.map((c) => this._row(c, 1))}
    </ha-card>`;
  }

  static styles = css`
    ha-card { padding: 10px; --amber: #ffb765; }
    .head { font-size: 18px; font-weight: 650; padding: 6px 8px 10px; }
    .row { position: relative; height: 50px; border-radius: 12px; margin: 6px 0; background: #2a2f39;
      display: flex; align-items: center; gap: 6px; padding: 0 8px 0 4px; overflow: hidden;
      margin-left: calc(var(--depth) * 14px); color: #eef1f6; touch-action: none; cursor: pointer;
      user-select: none; -webkit-user-select: none; }
    /* The fill is the brightness bar behind the row. It must stay out of the
       flex flow: ".row > *" below has the same specificity, so excluding .fill
       there is what keeps "position: absolute" from being overridden. */
    .fill { position: absolute; top: 0; bottom: 0; left: 0; background: rgba(255,183,101,.22);
      border-right: 2px solid var(--amber); z-index: 0; pointer-events: none;
      transition: width 140ms ease-out; }
    /* While dragging, the fill must sit exactly under the finger — no easing. */
    .row.dragging .fill { transition: none; }
    .row > *:not(.fill) { position: relative; z-index: 1; }
    /* Controls are 32px hit targets around much smaller glyphs, so a tap lands
       on the control instead of the row's brightness slider. */
    .chev, .dot, .info { flex: none; width: 32px; height: 32px; padding: 0; border: none;
      background: none; color: #98a0ad; cursor: pointer; display: grid; place-items: center; }
    .chev { font-size: 13px; }
    .chev.spacer { visibility: hidden; }
    .dot::before { content: ''; width: 12px; height: 12px; border-radius: 50%; background: #5a616e;
      transition: background 120ms ease, box-shadow 120ms ease, transform 120ms ease; }
    .dot.on::before { background: var(--amber); box-shadow: 0 0 8px var(--amber); }
    .dot:active::before { transform: scale(.8); }
    .info { font-size: 16px; border-radius: 50%; transition: background 120ms ease; }
    .info:active { background: rgba(255,255,255,.12); }
    /* min-width:0 lets the label shrink inside the flex row instead of forcing
       the row wider than the card. */
    .meta { flex: 1; min-width: 0; }
    .nm, .st { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .nm { font-size: 14.5px; font-weight: 560; } .st { font-size: 11.5px; color: #98a0ad; }
    .err { padding: 12px; color: #ff8080; }
  `;
}

declare global { interface HTMLElementTagNameMap { 'grouped-lights-card': GroupedLightsCard } }
