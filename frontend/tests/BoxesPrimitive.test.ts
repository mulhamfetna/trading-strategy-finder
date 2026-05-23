/**
 * BoxesPrimitive helpers — pure unit tests.
 *
 * BUG-024: the bar-time snapping logic added when boxes broke had zero
 * tests. This file locks in:
 *   - lowerBound binary search (edge cases)
 *   - snapBox behavior for boxes that predate/extend the chart,
 *     and for the LWC-specific "Saturday gap" case (no candle at the
 *     box's recorded start_time because NQ futures don't trade
 *     weekends, and the -2 day shift puts many box starts on Saturday).
 *
 * Semantics reminder: box.end_time is EXCLUSIVE (matches
 * BoxLookup.get_box_rects in src/strategy/box_lookup.py).
 */

import { describe, it, expect } from 'vitest';
import { lowerBound, snapBox } from '../src/components/BoxesPrimitive';

describe('lowerBound', () => {
  it('returns 0 for a value below all elements', () => {
    expect(lowerBound([10, 20, 30], 5)).toBe(0);
  });

  it('returns arr.length for a value above all elements', () => {
    expect(lowerBound([10, 20, 30], 99)).toBe(3);
  });

  it('returns the exact index when the value equals an element', () => {
    expect(lowerBound([10, 20, 30], 20)).toBe(1);
  });

  it('returns the insertion index between elements', () => {
    expect(lowerBound([10, 20, 30], 15)).toBe(1);
    expect(lowerBound([10, 20, 30], 25)).toBe(2);
  });

  it('handles empty input', () => {
    expect(lowerBound([], 42)).toBe(0);
  });
});

describe('snapBox', () => {
  // 4h bars Mon-Fri (UTC seconds), no weekend bars
  const monday = 1704067200;     // 2024-01-01 00:00
  const tuesday = monday + 86400;
  const wednesday = monday + 86400 * 2;
  const thursday = monday + 86400 * 3;
  const friday = monday + 86400 * 4;
  const saturday = monday + 86400 * 5;
  const sunday = monday + 86400 * 6;
  const bars = [monday, tuesday, wednesday, thursday, friday];

  it('returns null on empty bar-times array', () => {
    expect(snapBox({ start_time: monday, end_time: friday }, [])).toBeNull();
  });

  it('snaps both edges to exact bars when box spans interior', () => {
    const snap = snapBox({ start_time: tuesday, end_time: friday }, bars);
    expect(snap).toEqual({ x1: tuesday, x2: thursday });
    // end_time=friday is EXCLUSIVE, so x2 is the last bar BEFORE friday
  });

  // The canonical bug scenario: box's recorded start_time falls on a
  // Saturday (no bar) because of the -2 day shift; we must snap forward
  // to the next real bar after the weekend gap.
  it('snaps a box starting in a weekend gap forward to the next real bar', () => {
    // Week 1 Thu/Fri, then Week 2 Mon/Tue/Wed — a real Sat/Sun gap
    const w2Monday = monday + 86400 * 7;
    const w2Tuesday = w2Monday + 86400;
    const w2Wednesday = w2Monday + 86400 * 2;
    const gapBars = [thursday, friday, w2Monday, w2Tuesday, w2Wednesday];
    const snap = snapBox(
      { start_time: saturday, end_time: w2Wednesday },
      gapBars,
    );
    expect(snap).not.toBeNull();
    // start_time=saturday → next real bar is w2Monday
    expect(snap?.x1).toBe(w2Monday);
    // end_time=w2Wednesday exclusive → last in-box bar is w2Tuesday
    expect(snap?.x2).toBe(w2Tuesday);
  });

  it('returns "extend" for x1 when box predates the first bar', () => {
    const snap = snapBox({ start_time: monday - 86400, end_time: thursday }, bars);
    expect(snap?.x1).toBe('extend');
    expect(snap?.x2).toBe(wednesday); // end=thursday exclusive → x2=wednesday
  });

  it('returns "extend" for x2 when box extends past the last bar', () => {
    const snap = snapBox({ start_time: tuesday, end_time: sunday }, bars);
    expect(snap?.x1).toBe(tuesday);
    expect(snap?.x2).toBe('extend');
  });

  it('returns null when box ends before the first bar', () => {
    expect(
      snapBox({ start_time: monday - 86400 * 2, end_time: monday - 86400 }, bars),
    ).toBeNull();
  });

  it('returns null when box starts after the last bar', () => {
    expect(
      snapBox({ start_time: saturday, end_time: sunday }, bars),
    ).toBeNull();
  });

  it('treats end_time as exclusive — bar at end_time is excluded', () => {
    // Box that ends exactly at thursday → last in-box bar is wednesday.
    const snap = snapBox({ start_time: monday, end_time: thursday }, bars);
    expect(snap?.x2).toBe(wednesday);
  });

  it('returns null when start_time exactly equals end_time (zero width)', () => {
    expect(snapBox({ start_time: tuesday, end_time: tuesday }, bars)).toBeNull();
  });
});
