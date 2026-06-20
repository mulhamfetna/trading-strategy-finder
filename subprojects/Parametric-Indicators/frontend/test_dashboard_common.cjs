/* Node assertion harness for the PURE helpers in dashboard_common.js (no browser needed).
 * Run: node frontend/test_dashboard_common.cjs   (the IIFE guards its browser-global access so it
 * loads under node and exports DB via module.exports). */
const assert = require('assert');
const DB = require('./dashboard_common.js');

// boxFromLog — tag only when the combined box carries a layer (max-type); none otherwise
assert.strictEqual(DB.boxFromLog('+$100', { value: 100, layer: 'L1' }), '+$100 · L1');
assert.strictEqual(DB.boxFromLog('+$100', { value: 100, layer: 'L2' }), '+$100 · L2');
assert.strictEqual(DB.boxFromLog('+$100', { value: 100 }), '+$100');          // sum/recompute box → no tag
assert.strictEqual(DB.boxFromLog('72%', null), '72%');

// grayMarkers — returns a COPY; recolors grayed to muted; leaves input untouched
const mk = [{ time: 1, color: '#00c853' }, { time: 2, color: '#ff5252' }];
const g = DB.grayMarkers(mk, true);
assert.strictEqual(g[0].color, DB.TH.muted);
assert.strictEqual(g[1].color, DB.TH.muted);
assert.strictEqual(mk[0].color, '#00c853');                                    // input NOT mutated
assert.notStrictEqual(g[0], mk[0]);                                            // copy, not alias
const ng = DB.grayMarkers(mk, false);
assert.strictEqual(ng[0].color, '#00c853');                                    // not grayed → original color

// flatAreaSeries — one point per candle; flat across idle bars; steps at the layer's exits
const log = [
  { i: 0, time: 10, layer: 'L1', decision: 'nonentry', exit_time: null, pnl: 0 },
  { i: 1, time: 20, layer: 'L1', decision: 'entry', exit_time: 30, pnl: 50 },
  { i: 2, time: 30, layer: 'L1', decision: 'nonentry', exit_time: null, pnl: 0 },
  { i: 3, time: 40, layer: 'L1', decision: 'nonentry', exit_time: null, pnl: 0 },
];
const s = DB.flatAreaSeries(log, 'L1');
assert.strictEqual(s.length, 4);                                               // one per candle
assert.deepStrictEqual(s.map(p => p.value), [0, 0, 50, 50]);                    // flat → step at exit(30) → flat
const s2 = DB.flatAreaSeries(log, 'L2');                                        // no L2 trades → all flat at 0
assert.deepStrictEqual(s2.map(p => p.value), [0, 0, 0, 0]);

// grayLine — applies color in place, never hides
let applied = null;
const series = { applyOptions: o => (applied = o) };
DB.grayLine(series, true, '#abc');
assert.strictEqual(applied.color, DB.TH.muted);
DB.grayLine(series, false, '#abc');
assert.strictEqual(applied.color, '#abc');

console.log('dashboard_common pure-helper tests: all passed');
