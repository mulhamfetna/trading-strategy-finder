/**
 * Lightweight-charts v5 series primitive — draws TradingView-style box
 * rectangles on the main price pane.
 *
 * Core problem: timeToCoordinate() only returns a valid x-coordinate for
 * EXACT bar timestamps in the series data. Any time between bars (weekends,
 * holidays, midnight gaps) returns null, causing boxes to vanish entirely.
 *
 * Fix: we keep a sorted list of bar timestamps (_barTimes). For each box we
 * find the nearest real bar within the box range and use that for the x
 * coordinate. Boxes that start before the chart use x=0; boxes that end
 * after the chart extend to x=W.
 */

import type { CanvasRenderingTarget2D } from 'fancy-canvas';
import type {
  IChartApiBase,
  ISeriesApi,
  ISeriesPrimitive,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  SeriesType,
  Time,
} from 'lightweight-charts';

export interface BoxRect {
  start_time: number;   // unix seconds (UTC)
  end_time: number;     // unix seconds (UTC)
  upper: number;        // price
  lower: number;        // price
  level: string;        // e.g. "W-RH"
  timeframe: 'weekly' | 'monthly';
  fill_color: string;   // rgba(…)
  border_color: string; // rgba(…)
}

// ---- binary search helpers -------------------------------------------------

/** Index of first element in sorted array where arr[i] >= val, or arr.length */
export function lowerBound(arr: number[], val: number): number {
  let lo = 0, hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (arr[mid] < val) lo = mid + 1; else hi = mid;
  }
  return lo;
}

// ---- box-to-bar snap (pure, unit-tested) -----------------------------------

/**
 * Pure helper: given a box's [start_time, end_time) window and the
 * sorted bar-time array, return the bar timestamps the renderer should
 * snap x1/x2 onto, or `null` if the box is entirely off-chart.
 *
 * `'extend'` means the box stretches past the chart edge — the renderer
 * maps it to a coordinate outside the visible area.
 *
 * Semantics: box.end_time is EXCLUSIVE (matches BoxLookup.get_box_rects
 * where `_end = Date + window_days`). A bar whose timestamp equals
 * end_time is the first bar AFTER the box and is correctly excluded.
 */
export interface BoxSnap {
  x1: number | 'extend';
  x2: number | 'extend';
}

export function snapBox(
  box: { start_time: number; end_time: number },
  barTimes: number[],
): BoxSnap | null {
  if (barTimes.length === 0) return null;
  const firstBar = barTimes[0];
  const lastBar = barTimes[barTimes.length - 1];

  let x1: number | 'extend';
  if (box.start_time <= firstBar) {
    x1 = 'extend';
  } else if (box.start_time > lastBar) {
    return null;
  } else {
    const idx = lowerBound(barTimes, box.start_time);
    x1 = barTimes[Math.min(idx, barTimes.length - 1)];
  }

  let x2: number | 'extend';
  if (box.end_time > lastBar) {
    x2 = 'extend';
  } else if (box.end_time <= firstBar) {
    return null;
  } else {
    const idx = lowerBound(barTimes, box.end_time) - 1;
    if (idx < 0) return null;
    x2 = barTimes[idx];
  }

  if (typeof x1 === 'number' && typeof x2 === 'number' && x1 >= x2) return null;
  return { x1, x2 };
}

// ---- renderer --------------------------------------------------------------

class BoxesRenderer implements IPrimitivePaneRenderer {
  constructor(
    private readonly _boxes: BoxRect[],
    private readonly _barTimes: number[],
    private readonly _chart: IChartApiBase<Time> | null,
    private readonly _series: ISeriesApi<SeriesType, Time> | null,
  ) {}

  draw(target: CanvasRenderingTarget2D): void {
    if (!this._chart || !this._series || this._boxes.length === 0) return;
    if (this._barTimes.length === 0) return;

    const timeScale = this._chart.timeScale();

    target.useMediaCoordinateSpace(({ context, mediaSize }) => {
      const W = mediaSize.width;
      const H = mediaSize.height;

      for (const box of this._boxes) {
        const snap = snapBox(box, this._barTimes);
        if (snap === null) continue;

        // Translate snap result to canvas x-coordinates.
        let x1: number;
        if (snap.x1 === 'extend') {
          x1 = -W;
        } else {
          const coord = timeScale.timeToCoordinate(snap.x1 as unknown as Time);
          if (coord === null) continue;
          x1 = coord;
        }

        let x2: number;
        if (snap.x2 === 'extend') {
          x2 = W * 2;
        } else {
          const coord = timeScale.timeToCoordinate(snap.x2 as unknown as Time);
          if (coord === null) continue;
          x2 = coord;
        }

        if (x1 >= x2) continue;              // degenerate (e.g. only 1 bar in range)

        // --- resolve y coordinates (prices) ---
        const y1Raw = this._series!.priceToCoordinate(box.upper);
        const y2Raw = this._series!.priceToCoordinate(box.lower);
        if (y1Raw === null && y2Raw === null) continue;
        const y1 = y1Raw ?? -H;
        const y2 = y2Raw ?? H * 2;

        const top    = Math.min(y1, y2);
        const height = Math.abs(y2 - y1);
        if (height < 1) continue;

        // Clip to visible canvas area
        const visLeft   = Math.max(x1, 0);
        const visTop    = Math.max(top, 0);
        const visRight  = Math.min(x2, W);
        const visBottom = Math.min(top + height, H);
        if (visRight <= visLeft || visBottom <= visTop) continue;

        context.save();

        // Semitransparent fill
        context.fillStyle = box.fill_color;
        context.fillRect(visLeft, visTop, visRight - visLeft, visBottom - visTop);

        // Border lines at upper (U) and lower (D) price edges
        context.strokeStyle = box.border_color;
        context.lineWidth = 1;
        if (box.timeframe === 'monthly') context.setLineDash([5, 3]);

        if (top >= -1 && top <= H + 1) {
          context.beginPath();
          context.moveTo(visLeft, top);
          context.lineTo(visRight, top);
          context.stroke();
        }

        const bottom = top + height;
        if (bottom >= -1 && bottom <= H + 1) {
          context.beginPath();
          context.moveTo(visLeft, bottom);
          context.lineTo(visRight, bottom);
          context.stroke();
        }

        // Level label
        if (visRight - visLeft > 20 && top + 12 > 0 && top < H) {
          context.setLineDash([]);
          context.font = 'bold 9px monospace';
          context.fillStyle = box.border_color;
          const labelY = Math.max(top + 11, visTop + 11);
          context.fillText(box.level, visLeft + 3, labelY);
        }

        context.restore();
      }
    });
  }
}

// ---- pane view -------------------------------------------------------------

class BoxesPaneView implements IPrimitivePaneView {
  private _getState: () => {
    boxes: BoxRect[];
    barTimes: number[];
    chart: IChartApiBase<Time> | null;
    series: ISeriesApi<SeriesType, Time> | null;
  };

  constructor(
    getState: () => {
      boxes: BoxRect[];
      barTimes: number[];
      chart: IChartApiBase<Time> | null;
      series: ISeriesApi<SeriesType, Time> | null;
    },
  ) {
    this._getState = getState;
  }

  renderer(): IPrimitivePaneRenderer {
    const { boxes, barTimes, chart, series } = this._getState();
    return new BoxesRenderer(boxes, barTimes, chart, series);
  }

  zOrder(): 'bottom' | 'normal' | 'top' {
    return 'bottom';
  }
}

// ---- primitive -------------------------------------------------------------

export class BoxesPrimitive implements ISeriesPrimitive<Time> {
  private _boxes: BoxRect[] = [];
  private _barTimes: number[] = [];
  private _chart: IChartApiBase<Time> | null = null;
  private _series: ISeriesApi<SeriesType, Time> | null = null;
  private _requestUpdate: (() => void) | null = null;
  private _paneView: BoxesPaneView;

  constructor() {
    this._paneView = new BoxesPaneView(() => ({
      boxes: this._boxes,
      barTimes: this._barTimes,
      chart: this._chart,
      series: this._series,
    }));
  }

  attached(params: {
    chart: IChartApiBase<Time>;
    series: ISeriesApi<SeriesType, Time>;
    requestUpdate: () => void;
  }): void {
    this._chart = params.chart;
    this._series = params.series;
    this._requestUpdate = params.requestUpdate;
  }

  detached(): void {
    this._chart = null;
    this._series = null;
    this._requestUpdate = null;
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this._paneView];
  }

  /** Call whenever candle data changes so box x-coordinates use real bar times. */
  setBarTimes(times: number[]): void {
    this._barTimes = times;
  }

  setBoxes(boxes: BoxRect[]): void {
    this._boxes = boxes;
    this._requestUpdate?.();
  }

  clear(): void {
    this._boxes = [];
    this._barTimes = [];
    this._requestUpdate?.();
  }
}
