import './card';
import './editor';
(window as unknown as { customCards?: unknown[] }).customCards ??= [];
(window as unknown as { customCards: unknown[] }).customCards.push({
  type: 'grouped-lights-card',
  name: 'Grouped Lights Card',
  description: 'LIFX-style collapsible control for an area’s grouped lights.',
  preview: true,
});
