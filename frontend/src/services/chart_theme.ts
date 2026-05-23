/**
 * Centralised colour palette for the Lightweight Charts canvas.
 *
 * LWC accepts hex strings (not Tailwind classes), so the chart can't
 * read `tv-*` tokens at runtime — but it CAN import from one module
 * that mirrors them. Keep these values in sync with the `tv` palette
 * in `frontend/tailwind.config.js`.
 *
 * Adding a new colour: add it here AND in `tailwind.config.js` so
 * everything stays consistent between the chart and the rest of the
 * UI.
 */

export const CHART_THEME = {
  // Layout
  bg:           '#131722',  // mirrors tv-bg
  text:         '#d1d4dc',  // mirrors tv-text
  border:       '#363a45',  // mirrors tv-border (grid + scale borders)
  muted:        '#787b86',  // mirrors tv-muted

  // Bull / Bear
  bull:         '#00c853',  // mirrors tv-green — up bar / long marker / win
  bear:         '#ff5252',  // mirrors tv-red — down bar / short marker / loss

  // Tinted variants (suffix `44` = ~27% alpha, `88` = ~53% alpha)
  bullTinted:   '#00c85344',  // volume bar on up close
  bearTinted:   '#ff525244',  // volume bar on down close
  bullThreshold:'#00c85388',  // RSI 30 line
  bearThreshold:'#ff525288',  // RSI 70 line

  // Indicator series
  emaFast:      '#f7931a',
  emaSlow:      '#2962ff',  // mirrors tv-blue
  rsi:          '#9c27b0',
} as const;
