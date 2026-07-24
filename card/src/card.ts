import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HassLike, CardConfig, LightNode } from './types';
import { buildTree } from './tree';

@customElement('grouped-lights-card')
export class GroupedLightsCard extends LitElement {
  @property({ attribute: false }) public hass?: HassLike;
  @state() private _config?: CardConfig;
  @state() private _expanded = new Set<string>();

  public setConfig(config: CardConfig): void {
    if (!config || !config.entity) throw new Error('grouped-lights-card: "entity" is required');
    this._config = config;
  }
  public getCardSize(): number { return 4; }
  public static getStubConfig(): Partial<CardConfig> { return { entity: '' }; }
  public static getConfigElement(): HTMLElement { return document.createElement('grouped-lights-card-editor'); }

  private _svc(entityId: string, on: boolean): void {
    this.hass?.callService('light', on ? 'turn_on' : 'turn_off', { entity_id: entityId });
  }
  private _setBrightness(entityId: string, pct: number): void {
    const clamped = Math.max(0, Math.min(100, Math.round(pct)));
    this.hass?.callService('light', 'turn_on', { entity_id: entityId, brightness_pct: clamped });
  }
  private _moreInfo(entityId: string): void {
    this.dispatchEvent(new CustomEvent('hass-more-info', { detail: { entityId }, bubbles: true, composed: true }));
  }
  private _toggleExpand(entityId: string): void {
    const next = new Set(this._expanded);
    next.has(entityId) ? next.delete(entityId) : next.add(entityId);
    this._expanded = next;
  }
  private _onRowPointer(e: PointerEvent, node: LightNode): void {
    // Row-as-slider: a drag/click on the row body (not on a child control) sets
    // brightness_pct from the horizontal pointer position. Taps on the dot/chevron/
    // info controls are handled by their own @click listeners and must not also
    // move the brightness slider, so bail out here when the event originated there.
    if ((e.target as HTMLElement).closest('.dot,.chev,.info')) return;
    const row = e.currentTarget as HTMLElement;
    const rect = row.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    this._setBrightness(node.entity_id, pct);
  }

  private _row(node: LightNode, depth: number, expandable = true): unknown {
    const pct = node.on && node.brightness != null ? Math.round((node.brightness / 255) * 100) : (node.on ? 100 : 0);
    const st = node.on ? `On · ${pct}%` : 'Off';
    const expanded = expandable && this._expanded.has(node.entity_id);
    return html`
      <div class="row ${node.on ? 'on' : ''}" style="--depth:${depth}" @pointerdown=${(e: PointerEvent) => this._onRowPointer(e, node)}>
        <div class="fill" style="width:${node.on ? pct : 0}%"></div>
        ${node.isGroup && expandable
          ? html`<span class="chev" data-expand=${node.entity_id}
              @click=${(e: Event) => { e.stopPropagation(); this._toggleExpand(node.entity_id); }}>${expanded ? '▾' : '▸'}</span>`
          : html`<span class="chev spacer"></span>`}
        <span class="dot ${node.on ? 'on' : ''}" data-toggle=${node.entity_id}
          @click=${(e: Event) => { e.stopPropagation(); this._svc(node.entity_id, !node.on); }}></span>
        <div class="meta"><div class="nm">${node.name}</div><div class="st">${st}</div></div>
        <button class="info" data-info=${node.entity_id}
          @click=${(e: Event) => { e.stopPropagation(); this._moreInfo(node.entity_id); }}>ⓘ</button>
      </div>
      ${node.isGroup && expanded ? node.children.map((c) => this._row(c, depth + 1)) : nothing}
    `;
  }

  protected render(): unknown {
    if (!this.hass || !this._config?.entity) return nothing;
    const root = buildTree(this.hass, this._config.entity);
    if (!root) return html`<ha-card><div class="err">Entity ${this._config.entity} not found</div></ha-card>`;
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
      display: flex; align-items: center; gap: 10px; padding: 0 12px; overflow: hidden;
      margin-left: calc(var(--depth) * 14px); color: #eef1f6; touch-action: none; cursor: pointer; }
    .fill { position: absolute; inset: 0; background: rgba(255,183,101,.22); border-right: 2px solid var(--amber); z-index: 0; }
    .row > * { position: relative; z-index: 1; }
    .chev { width: 16px; text-align: center; color: #98a0ad; }
    .chev.spacer { visibility: hidden; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #5a616e; flex: none; }
    .dot.on { background: var(--amber); box-shadow: 0 0 8px var(--amber); }
    .meta { flex: 1; } .nm { font-size: 14.5px; font-weight: 560; } .st { font-size: 11.5px; color: #98a0ad; }
    .info { background: none; border: none; color: #98a0ad; font-size: 16px; cursor: pointer; }
    .err { padding: 12px; color: #ff8080; }
  `;
}

declare global { interface HTMLElementTagNameMap { 'grouped-lights-card': GroupedLightsCard } }
