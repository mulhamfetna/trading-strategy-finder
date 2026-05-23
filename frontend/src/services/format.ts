/**
 * Shared number / currency formatters.
 *
 * Centralised so every panel renders P/L with the same conventions:
 *   - Exact zero is unsigned and neutral-coloured (BUG-005 family).
 *   - Positives get a leading `+`, negatives get `-`.
 *   - Thousands separator on dollar values.
 *
 * Use these everywhere instead of inline `toFixed` / template-string sign logic.
 */

const dollarFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const intFormatter = new Intl.NumberFormat('en-US');

/** Signed dollar amount: `+$1,234.50`, `-$1,234.50`, `$0.00`. */
export function formatDollar(n: number): string {
  if (n === 0) return '$0.00';
  const sign = n > 0 ? '+' : '-';
  return `${sign}$${dollarFormatter.format(Math.abs(n))}`;
}

/** Magnitude-only dollars: `-$1,234.50` for nonzero, `$0.00` for zero. */
export function formatDrawdown(magnitude: number): string {
  if (magnitude === 0) return '$0.00';
  return `-$${dollarFormatter.format(Math.abs(magnitude))}`;
}

/** Render undefined ratios as `N/A`. */
export function formatRatio(n: number | null | undefined, digits = 2): string {
  return n === null || n === undefined ? 'N/A' : n.toFixed(digits);
}

/** Sign-driven semantic color class. Returns undefined at zero. */
export function signColor(n: number): string | undefined {
  if (n > 0) return 'text-tv-green';
  if (n < 0) return 'text-tv-red';
  return undefined;
}

/** Integer with thousands separator. */
export function formatInt(n: number): string {
  return intFormatter.format(n);
}

/** Elapsed milliseconds → `"42 ms"` or `"3.21 s"` once over a second. */
export function formatElapsed(ms: number): string {
  if (ms < 1000) return `${intFormatter.format(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}
