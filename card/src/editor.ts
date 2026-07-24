import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { HassLike, CardConfig } from './types';

@customElement('grouped-lights-card-editor')
export class GroupedLightsCardEditor extends LitElement {
  @property({ attribute: false }) public hass?: HassLike;
  @state() private _config: CardConfig = { type: 'grouped-lights-card' };

  public setConfig(config: CardConfig): void { this._config = { ...config }; }

  private _set(field: keyof CardConfig, value: unknown): void {
    this._config = { ...this._config, [field]: value };
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config: this._config }, bubbles: true, composed: true,
    }));
  }

  protected render(): unknown {
    const entitySelector = { entity: { domain: 'light' } };
    return html`<div class="f">
      <ha-selector .hass=${this.hass} .selector=${entitySelector} label="Master light group"
        .value=${this._config.entity ?? ''}
        @value-changed=${(e: any) => this._set('entity', e.detail.value)}></ha-selector>
      <ha-selector .hass=${this.hass} .selector=${{ text: {} }} label="Title (optional)"
        .value=${this._config.title ?? ''}
        @value-changed=${(e: any) => this._set('title', e.detail.value)}></ha-selector>
    </div>`;
  }

  static styles = css`.f { display: flex; flex-direction: column; gap: 16px; padding: 8px 0; }`;
}

declare global { interface HTMLElementTagNameMap { 'grouped-lights-card-editor': GroupedLightsCardEditor } }
