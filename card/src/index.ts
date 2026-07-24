import './card';
import './editor';
(window as unknown as { customCards?: unknown[] }).customCards ??= [];
(window as unknown as { customCards: unknown[] }).customCards.push({
  type: 'grouped-lights-card',
  name: 'Grouped Lights Card',
  description: 'Collapsible area → lamp → bulb light control with per-level brightness.',
  preview: true,
});
