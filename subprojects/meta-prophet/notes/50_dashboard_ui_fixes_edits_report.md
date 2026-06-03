---
name: dashboard-ui-fixes-edits-report
description: Change report (where/when/why/how) for three WS-G standalone dashboard UI fixes — max-drawdown card forced red, real browser-width responsiveness (fixed a latent lightweight-charts c.container resize bug), and a show/hide settings-panel toggle. Commit 0b5ef95. Presentation-only; engine/backend untouched. Companion to notes/47 + notes/48.
type: reference
---

# Edits Report — dashboard UI fixes (commit `0b5ef95`)

Change log for three UI fixes on the standalone app `subprojects/wsg-strategy/frontend/index.html`:
exactly **when**, **where**, **why**, and **how**. Follows the format of notes/47 + notes/48.

---

## WHEN
- **Commit:** `0b5ef95` — "fix(wsg-strategy): UI — red max-DD card, real width responsiveness, settings toggle"
- **Date:** 2026-06-03 17:28 (+03:00) · **Author:** Mulham Fetna · **Pushed:** `origin/dev`
- **Scope:** 1 file, +23 / −4 lines (`frontend/index.html`). **Presentation-only** — no engine,
  backend, strategy, or payload change.

## WHY (one sentence)
The max-drawdown card was colored **green** whenever it sat under the dd_cap reference (reading as
"good", when a drawdown is always a loss); the charts **looked width-locked** because a latent bug
left them frozen at their initial pixel width; and there was **no way to reclaim the screen** taken
by the settings panel.

## HOW (the three changes)

### 1. Max-drawdown card always red
```diff
- card('$'+Math.round(S.max_dd).toLocaleString(),'max drawdown',S.max_dd<=(P.dd_cap||1e9)?'pos':'neg')+
+ card('$'+Math.round(S.max_dd).toLocaleString(),'max drawdown','neg')+
```
Max drawdown is a loss magnitude, so it is unconditionally red (`neg`). (The underwater chart
already plots it negative; this just makes the headline card consistent.)

### 2. Real browser-width responsiveness — fixed a latent resize bug
**Root cause:** the resize handler called `c.container.clientWidth`, but lightweight-charts v4 does
**not** expose `.container` on the chart object → `undefined` → the handler silently no-op'd, so
every chart stayed at the width it had at first paint and the layout looked hardcoded.
**Fix:** track each chart's container element and refit via a `ResizeObserver` on `<main>` (fires on
window resize **and** on the settings-panel toggle):
```diff
- const mk=(id,h)=>LightweightCharts.createChart(document.getElementById(id),{...,width:...clientWidth,height:h});
- const priceC=mk('price',430),...; const charts=[priceC,...];
- window.addEventListener('resize',()=>charts.forEach(c=>c.applyOptions({width:c.container.clientWidth})));
+ const charts=[], ctns=[];
+ const mk=(id,h)=>{const el=...; const c=createChart(el,{...,width:el.clientWidth,height:h}); charts.push(c); ctns.push(el); return c;};
+ const priceC=mk('price',430),...;
+ function fitCharts(){ charts.forEach((c,i)=>{ const w=ctns[i].clientWidth; if(w>0) c.applyOptions({width:w}); }); }
+ window.addEventListener('resize', fitCharts);
+ if(window.ResizeObserver){ new ResizeObserver(fitCharts).observe(document.querySelector('main')); }
```
The flex layout (`body`→`.body`→`main flex:1`) was already fluid; only the charts weren't following
it. Nothing is hardcoded now.

### 3. Show/hide settings-panel toggle
- Header button: `<button class="ghost" id="toggle">⚙ Hide settings</button>` (+ `.ghost` CSS).
- CSS: `body.no-settings aside { display:none; }`.
- JS: toggles `body.no-settings`, swaps the label (`Hide`/`Show settings`), and `requestAnimationFrame(fitCharts)`
  as a fallback if `ResizeObserver` is unavailable. Hiding the panel widens `<main>`, and the
  observer refits the charts to fill the freed width.

## WHERE
| File | What changed | ± |
|---|---|---|
| `wsg-strategy/frontend/index.html` | (1) max-DD card → `neg`; (2) container-tracked `mk()` + `fitCharts()` + ResizeObserver; (3) `.ghost` button + `body.no-settings` rule + toggle handler | +23 / −4 |

**Not touched:** `strategy.py`, `server.py`, `config.py`, the verified engine, the payload shape.

## VERIFICATION
- Served HTML (server reads the file fresh per GET — no restart needed) contains all three edits:
  the `body.no-settings aside` rule, the `#toggle` button, `card(... 'max drawdown','neg')`, the
  `ResizeObserver(fitCharts)` wiring, and the `charts=[], ctns=[]` container tracking.
- Inline-script delimiter balance: braces 111/111, parens 259/259, brackets 44/44 — all matched.
- Live engine unaffected: post-reload runs still return **+$7,735 / $3,670 / 66 trades**.

## RESULT
| | before | after |
|---|---|---|
| max-drawdown card | green when ≤ cap (reads "good") | **always red** |
| chart width on resize/maximize | frozen at first-paint width (looked hardcoded) | **tracks browser width** (window + panel toggle) |
| settings panel | always visible, no way to reclaim space | **toggle to hide/show**; charts reflow to fill |

## One-paragraph summary (baby)
Three cosmetic dashboard fixes on 2026-06-03 (commit `0b5ef95`): the "max drawdown" number is now
always red (it's a loss, so green was misleading); the charts now grow and shrink with the browser
window instead of being stuck at one size — they were frozen because the old resize code looked for
a property the charting library doesn't have, so it quietly did nothing; and there's a new button to
hide the left settings panel, which lets the charts spread across the full width. Nothing about the
strategy, the math, or the results changed — only how the page looks.

## Cross-references
- `notes/47` — global-high-water-mark breaker fix. `notes/48` — no-silent-fallback hardening.
- `notes/49` — why max DD ($3,670) exceeds the breaker trigger (the metric this red card now shows).
- App: `subprojects/wsg-strategy/` (`python3 server.py` → http://localhost:8200/).
