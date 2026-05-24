---
name: boxes_lowerBound
file: frontend/src/components/BoxesPrimitive.ts
signature: lowerBound(arr: number[], val: number) → number
responsibility: Binary search helper. Returns the index of the first element `>= val`, or `arr.length` if every element is strictly less. Used by snapBox to find the nearest real bar timestamp to a box's start / end time.
related: [[boxes_snapBox]]
---

# `lowerBound`

Standard `std::lower_bound` semantics, written longhand so it can be unit-tested directly.

## Implementation

```ts
export function lowerBound(arr: number[], val: number): number {
  let lo = 0, hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (arr[mid] < val) lo = mid + 1; else hi = mid;
  }
  return lo;
}
```

- `(lo + hi) >>> 1` instead of `Math.floor((lo + hi) / 2)` — unsigned right shift gives the same result for non-negative `lo + hi` and is marginally faster. Safe here because both indices are bounded by `arr.length`.
- Strict-less comparison (`<`, not `<=`) is what makes this `lower_bound`. The first index where `arr[i] >= val`.

## Pre-condition

`arr` must be sorted ascending. The caller — [[boxes_snapBox]] — always passes a sorted bar-time array (provided by [[chartpane_applyData]] which maps over candles in chronological order).

## Returns

- An integer in `[0, arr.length]`.
- `arr.length` means every element is `< val`.

The caller uses both ends — `0` means "all bars are at or after this time", `arr.length` means "no bar is at or after this time".
