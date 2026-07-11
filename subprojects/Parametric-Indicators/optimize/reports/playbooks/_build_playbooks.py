"""Build 36 shareable per-market per-timeframe playbooks (pageless PDFs) on the server.

Inputs (all on the server under ~/Mulham/wsg-i):
  - playbook_metrics.json  : [{inst,tf, full:{cards,summary,params,split_ts}, oos2026:{...}}]  (dashboard truth)
  - Parametric-Indicators/optimize/results/wsh4_champions_full_<TOK>.json  (settings to load; NQ = base file)
  - snapshots/<INST>_<TF>.png  (full-page dashboard snapshot, embedded)
Output: ~/Mulham/wsg-i/playbooks/<INST>_<TF>_playbook.pdf  (one exact-height page each)

Each PDF: header+verdict · what-this-is · load-these-settings · how-it-trades (+Mermaid) · full tearsheet
(+embedded snapshot) · 2026 OOS · risk/when-NOT-to-trade · provenance+attribution.
"""
import base64, html, json, os, re, sys

BASE = os.path.expanduser("~/Mulham/wsg-i")
REPO = os.path.join(BASE, "Parametric-Indicators")
SNAPS = os.path.join(BASE, "snapshots")
OUTDIR = os.path.join(BASE, "playbooks")
os.makedirs(OUTDIR, exist_ok=True)

MERMAID_JS = "/home/dev/Mulham/wsg-i/mermaid.min.js"   # scp'd alongside

NAMES = {"NQ": "Nasdaq-100 (NQ)", "ES": "S&P 500 (ES)", "GC": "Gold (GC)",
         "SI": "Silver (SI)", "RTY": "Russell 2000 (RTY)", "YM": "Dow (YM)",
         "HG": "Copper (HG)", "CL": "Crude Oil (CL)", "NG": "Natural Gas (NG)"}
TF_LONG = {"4h": "4-hour", "2h": "2-hour", "1h": "1-hour", "15m": "15-minute", "5m": "5-minute", "2m": "2-minute"}

# optional args: [input_json] [slot_filter e.g. GC_4h]  (defaults: full metrics file, all slots)
_IN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "playbook_metrics.json")
_FILTER = sys.argv[2] if len(sys.argv) > 2 else None
metrics = json.load(open(_IN if os.path.isabs(_IN) else os.path.join(BASE, _IN)))
if _FILTER:
    metrics = [r for r in metrics if f"{r['inst']}_{r['tf']}" == _FILTER]
_champ_cache = {}
def champ(inst):
    if inst not in _champ_cache:
        fn = "wsh4_champions_full.json" if inst == "NQ" else f"wsh4_champions_full_{inst}.json"
        p = os.path.join(REPO, "optimize/results", fn)
        _champ_cache[inst] = json.load(open(p)) if os.path.exists(p) else {}
    return _champ_cache[inst]

def money(v):
    if v is None: return "—"
    return ("+" if v >= 0 else "−") + "$" + f"{abs(v):,.0f}"

def pct(v):
    return "—" if v is None else f"{v:.1f}%"

def r2(v):
    return "—" if v is None else f"{v:.2f}"

def data_uri(path):
    if not os.path.exists(path): return None
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def esc(x): return html.escape(str(x))


def fbox(rec):  # full-window on-screen truth
    return (rec.get("full") or {}).get("boxes", {})
def fsum(rec):  # full-window engine summary (detail)
    return (rec.get("full") or {}).get("summary", {})
def osum(rec):  # 2026 out-of-sample engine summary
    return (rec.get("oos2026") or {}).get("summary", {})


def verdict_for(rec):
    """Transparent, data-driven verdict + the plain reasons behind it.
    Headline from meta.boxes (on-screen truth); OOS from window=2026 meta.summary."""
    b, o = fbox(rec), osum(rec)
    fp, fdd, fw = b.get("pnl"), b.get("max_dd"), b.get("win")
    op = o.get("pnl")
    reasons = []
    rdd = (fp / fdd) if (fp and fdd) else None
    if fp is None or fp <= 0:
        return ("non-feasible", "✗", "#b3261e"), ["full-window P/L is not positive"], \
               dict(fp=fp, fdd=fdd, fw=fw, op=op, rdd=rdd)
    if op is not None and op < 0:
        reasons.append(f"loses money out-of-sample in 2026 ({money(op)})")
    elif op is not None and fdd and 0 <= op < 0.10 * fdd:
        # technically positive, but the 2026 profit is dwarfed by the drawdown you must sit through:
        # that is noise, not a tradeable edge. Say so rather than calling it "holds up".
        reasons.append(f"essentially flat out-of-sample in 2026 ({money(op)} against a "
                       f"${fdd:,.0f} drawdown) — no demonstrated edge on unseen data")
    if rdd is not None and rdd < 1:
        reasons.append(f"worst drawdown ({money(-fdd).replace('−','$')}) exceeds total profit — thin risk cushion")
    if fw is not None and fw < 35:
        reasons.append(f"low win rate ({fw:.0f}%) — profit rides on a few large winners")
    if not reasons:
        return ("deployable", "✓", "#1a7f37"), ["clears the risk bar; positive and holds out-of-sample"], \
               dict(fp=fp, fdd=fdd, fw=fw, op=op, rdd=rdd)
    severe = (op is not None and fdd and op < -0.5 * fdd)
    v = ("non-feasible", "✗", "#b3261e") if severe else ("caution", "⚠", "#b8860b")
    return v, reasons, dict(fp=fp, fdd=fdd, fw=fw, op=op, rdd=rdd)


def settings_for(rec):
    """Authoritative 'what to load': the exact params the UI sent (reproduces the on-screen number,
    incl. NQ's re-tuned default), supplemented by the champion JSON for any missing box field/indicators."""
    inst, tf = rec["inst"], rec["tf"]
    c = champ(inst).get(tf, {})
    jbox, jinds = c.get("box", {}), c.get("indicators", {})
    params = (rec.get("full") or {}).get("params", {}) or {}
    box = dict(jbox)  # start from JSON (has k, cap_1min, cooldown reliably)
    for k in ("sl_soft", "sl_hard", "tp", "gate_pct", "dd_limit", "cooldown", "flip", "k", "cap_1min"):
        if params.get(k) is not None:
            box[k] = params[k]
    pinds = params.get("indicators")
    inds = pinds if isinstance(pinds, dict) and pinds else jinds
    return box, inds


def settings_html(rec):
    box, inds = settings_for(rec)
    if not box:
        return "<p class='muted'>Champion settings not found in the registry for this slot.</p>"
    b = lambda k, d="—": box.get(k, d)
    rows = [
        ("Flip", "ON — trade the reversal of a failed box" if box.get("flip") else "OFF — trade the box direction"),
        ("Stop-loss (soft / hard)", f"{b('sl_soft')} / {b('sl_hard')} pts"),
        ("Take-profit", f"{b('tp')} pts"),
        ("Reward : risk (TP vs hard stop)", f"{(box.get('tp',0)/box.get('sl_hard',1)):.2f} : 1" if box.get("sl_hard") else "—"),
        ("Volatility gate", f"{b('gate_pct')}th percentile"),
        ("Confirms required (K)", f"{b('k')} indicators must agree"),
        ("Drawdown breaker", f"${b('dd_limit')}"),
        ("Cooldown", f"{b('cooldown')} bars"),
        ("1-min cap", f"{b('cap_1min')} bars"),
    ]
    tr = "".join(f"<tr><td>{esc(k)}</td><td class='mono'>{esc(v)}</td></tr>" for k, v in rows)
    ind_items = []
    for name, params in sorted(inds.items()):
        ps = ", ".join(f"{k}={v}" for k, v in params.items()) if params else "on"
        ind_items.append(f"<li><b>{esc(name)}</b><span class='mono'> — {esc(ps)}</span></li>")
    ind_html = ("<ul class='inds'>" + "".join(ind_items) + "</ul>") if ind_items else "<p class='muted'>none</p>"
    return (f"<table class='kv'>{tr}</table>"
            f"<div class='sub'>Indicators ({len(inds)})</div>{ind_html}")


def howitrades_mermaid(rec):
    tf = rec["tf"]
    box, _ = settings_for(rec)
    flip = "reversal of the failed box" if box.get("flip") else "box breakout direction"
    k = box.get("k", "K")
    return (
        "flowchart TD\n"
        f'  A["Box forms on the {TF_LONG.get(tf,tf)} frame"] --> B{{"Volatility gate<br/>above {box.get("gate_pct","?")}th pct?"}}\n'
        '  B -- no --> X["skip — too quiet"]\n'
        f'  B -- yes --> C{{"At least {k}<br/>indicators agree?"}}\n'
        '  C -- no --> X\n'
        f'  C -- yes --> D["ENTER — {flip}"]\n'
        f'  D --> E["Exit: take-profit {box.get("tp","?")} pts<br/>or stop {box.get("sl_hard","?")} pts"]\n'
        f'  E --> F["Drawdown breaker halts<br/>if losses hit ${box.get("dd_limit","?")}"]\n'
    )


def metric_table(m, title, detail=None, oos=False):
    """m = a boxes/summary dict with pnl/max_dd/win/pf/payoff/n_taken. detail = optional summary for
    avg-win/loss + hold-time rows. oos=True omits Worst drawdown (summary.max_dd is full-history, not
    window-scoped, so it would misleadingly show the whole-history DD against a single OOS year)."""
    m = m or {}
    dd = m.get("max_dd")
    rows = [("Net profit / loss", money(m.get("pnl")))]
    if not oos:
        rows.append(("Worst drawdown", "—" if dd is None else f"${dd:,.0f}"))
    rows += [
        ("Win rate", pct(m.get("win"))),
        ("Profit factor", r2(m.get("pf"))),
        ("Payoff (avg win / avg loss)", r2(m.get("payoff"))),
        ("Trades taken", m.get("n_taken", "—")),
    ]
    if detail:
        if detail.get("avg_win") is not None:
            rows.append(("Average winning trade", f"${detail['avg_win']:,.0f}"))
        if detail.get("avg_loss") is not None:
            rows.append(("Average losing trade", f"−${abs(detail['avg_loss']):,.0f}"))
        ph = (detail.get("position_hold_total") or {}).get("days")
        if ph is not None:
            rows.append(("Total time holding a position", f"{ph:.1f} days"))
    tr = "".join(f"<tr><td>{esc(k)}</td><td class='mono'>{esc(v if v is not None else '—')}</td></tr>" for k, v in rows)
    return f"<div class='sub'>{esc(title)}</div><table class='kv'>{tr}</table>"


PAGE_CSS = """
:root{--ink:#1a1d21;--muted:#6b7280;--line:#e5e7eb;--accent:#2e5cff;--bg:#ffffff;}
*{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}
.wrap{max-width:1000px;margin:0 auto;padding:38px 46px 54px;}
.badge{display:inline-block;padding:5px 13px;border-radius:999px;color:#fff;font-weight:700;font-size:13px;letter-spacing:.3px;}
h1{font-size:30px;margin:14px 0 2px;letter-spacing:-.4px;}
.tf{color:var(--muted);font-size:16px;margin:0 0 6px;}
h2{font-size:18px;margin:30px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--line);}
.sub{font-weight:700;font-size:14px;margin:16px 0 6px;color:#374151;}
p{margin:8px 0;} .muted{color:var(--muted);}
table.kv{border-collapse:collapse;width:100%;margin:4px 0 8px;}
table.kv td{border-bottom:1px solid var(--line);padding:7px 10px;vertical-align:top;}
table.kv td:first-child{color:#374151;width:46%;} .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13.5px;}
ul.inds{margin:4px 0;padding-left:20px;} ul.inds li{margin:2px 0;}
.hero{display:flex;gap:26px;flex-wrap:wrap;margin:14px 0 4px;}
.hero .stat{flex:1;min-width:150px;background:#f7f8fa;border:1px solid var(--line);border-radius:12px;padding:12px 14px;}
.hero .stat .n{font-size:24px;font-weight:800;letter-spacing:-.5px;} .hero .stat .l{color:var(--muted);font-size:12.5px;}
.snap{border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:10px 0;} .snap img{display:block;width:100%;}
.callout{border-left:4px solid var(--accent);background:#f4f7ff;padding:10px 14px;border-radius:0 8px 8px 0;margin:10px 0;}
.callout.warn{border-color:#b8860b;background:#fff9ec;} .callout.bad{border-color:#b3261e;background:#fdeeee;}
.mermaid{margin:8px 0;} .foot{margin-top:34px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;}
.oos{display:flex;gap:10px;flex-wrap:wrap;}
"""


def build_html(rec):
    inst, tf = rec["inst"], rec["tf"]
    b, fs, o = fbox(rec), fsum(rec), osum(rec)
    (vname, vicon, vcolor), reasons, m = verdict_for(rec)
    fp, fdd, op = m["fp"], m["fdd"], m["op"]
    verdict_label = {"deployable": "Deployable", "caution": "Caution", "non-feasible": "Non-feasible"}[vname]

    hero = ""
    for lbl, val in [("Full-window P/L", money(b.get("pnl"))),
                     ("Worst drawdown", "—" if fdd is None else f"${fdd:,.0f}"),
                     ("Win rate", pct(b.get("win"))), ("2026 out-of-sample", money(op))]:
        hero += f"<div class='stat'><div class='n'>{esc(val)}</div><div class='l'>{esc(lbl)}</div></div>"

    _sbox, _ = settings_for(rec)
    flip = _sbox.get("flip")
    what = (f"This playbook is the tuned box strategy for <b>{esc(NAMES.get(inst,inst))}</b> traded on the "
            f"<b>{TF_LONG.get(tf,tf)}</b> decision frame. On each {TF_LONG.get(tf,tf)} candle it forms a price "
            f"'box', and only enters when the market is active enough (volatility gate) and enough indicators "
            f"agree. It trades the <b>{'reversal of a box that fails' if flip else 'box breakout direction'}</b>, "
            f"then manages the position with a fixed take-profit / stop and a drawdown breaker. It is meant to be "
            f"loaded into the dashboard exactly as below and run — the numbers here are what the dashboard shows.")

    # 2026 verdict line
    ntr = o.get("n_taken")
    if op is None:
        oos_verdict = "Out-of-sample figure unavailable for this slot."
        oos_class = "warn"
    elif op > 0:
        oos_verdict = (f"<b>Holds up out-of-sample</b> — still profitable ({esc(money(op))}) across {esc(ntr)} trades "
                       f"on 2026 data the tuning never saw.")
        oos_class = ""
    elif op == 0:
        oos_verdict = "Flat out-of-sample in 2026 — neither gained nor lost."
        oos_class = "warn"
    else:
        oos_verdict = (f"<b>Loses money out-of-sample</b> ({esc(money(op))} across {esc(ntr)} trades) on 2026 data the "
                       f"tuning never saw — the full-window profit may be partly over-fit. Treat with caution.")
        oos_class = "bad"

    # risk section
    if vname == "deployable":
        risk = "<p>No blocking concerns: the champion reproduces on screen, clears the risk cushion, and stays positive out-of-sample. Standard position-sizing and the built-in drawdown breaker apply.</p>"
        rcls = ""
    else:
        items = "".join(f"<li>{esc(r)}</li>" for r in reasons)
        head = ("<b>Do not trade this combination.</b> " if vname == "non-feasible"
                else "<b>Trade only with caution</b> (or prefer a stronger timeframe for this market). ")
        risk = f"<p>{head}Reasons flagged from the data:</p><ul>{items}</ul>"
        rcls = "bad" if vname == "non-feasible" else "warn"

    snap = data_uri(os.path.join(SNAPS, f"{inst}_{tf}.png"))
    snap_html = (f"<div class='snap'><img src='{snap}'/></div>"
                 if snap else "<p class='muted'>Dashboard snapshot not found for this slot.</p>")

    _sts = (rec.get("full") or {}).get("split_ts")
    split = "in-sample through 2025 · out-of-sample 2026"  # split_ts is a raw unix ts; describe the split plainly
    body = f"""
    <div class='wrap'>
      <span class='badge' style='background:{vcolor}'>{vicon} {verdict_label}</span>
      <h1>{esc(NAMES.get(inst,inst))} — {TF_LONG.get(tf,tf)} playbook</h1>
      <p class='tf'>Box strategy champion · Layer&nbsp;1 · verified in the dashboard UI</p>
      <div class='hero'>{hero}</div>

      <h2>1 · What this is</h2>
      <p>{what}</p>

      <h2>2 · Load these settings</h2>
      <p class='muted'>In the dashboard: pick instrument <b>{esc(inst)}</b> → timeframe <b>{esc(tf)}</b> → set the values below → Run.</p>
      {settings_html(rec)}

      <h2>3 · How it trades</h2>
      <div class='mermaid'>{howitrades_mermaid(rec)}</div>

      <h2>4 · Complete tearsheet (full history)</h2>
      {metric_table(b, 'Full-window performance (exactly what the dashboard shows)', detail=fs)}
      {snap_html}

      <h2>5 · Out-of-sample check — 2026</h2>
      <div class='callout {oos_class}'>{oos_verdict}</div>
      {metric_table(o, '2026-only performance (held-out — the tuning never saw this year)', oos=True)}
      <p class='muted' style='font-size:12.5px'>Drawdown is reported on the full history only (the dashboard's drawdown figure is not split by year).</p>

      <h2>6 · Risk &amp; when NOT to trade</h2>
      <div class='callout {rcls}'>{risk}</div>

      <div class='foot'>
        Instrument {esc(inst)} · timeframe {esc(tf)} · champion source
        <span class='mono'>{esc('wsh4_champions_full' + ('' if inst=='NQ' else '_'+inst) + '.json')}</span> ·
        numbers captured from the live dashboard ({esc(split) or 'in-sample/OOS split at 2026'}) ·
        generated 2026-07-08.<br/>
        Mulham Fetna · contact@mulhamfetna.com · ORCID 0009-0006-4432-798X · github.com/mulhamfetna
      </div>
    </div>
    """
    return f"<!doctype html><meta charset='utf-8'><style>{PAGE_CSS}</style>{body}"


def main():
    from playwright.sync_api import sync_playwright
    mjs = open(MERMAID_JS).read() if os.path.exists(MERMAID_JS) else None
    done = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 1400}, device_scale_factor=2)
        for rec in metrics:
            inst, tf = rec["inst"], rec["tf"]
            page.set_content(build_html(rec), wait_until="load")
            if mjs:
                page.add_script_tag(content=mjs)
                page.evaluate("async () => { if (window.mermaid){ mermaid.initialize({startOnLoad:false,theme:'neutral'});"
                              " await mermaid.run({querySelector:'.mermaid'}); } }")
                page.wait_for_timeout(500)
            h = page.evaluate("() => document.body.scrollHeight")
            out = os.path.join(OUTDIR, f"{inst}_{tf}_playbook.pdf")
            page.pdf(path=out, width="1000px", height=f"{h+20}px", print_background=True,
                     margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
            done.append(out)
            print(f"{inst} {tf}: {os.path.basename(out)} ({h+20}px)", flush=True)
        browser.close()
    print(f"\nDONE: {len(done)} playbooks -> {OUTDIR}", flush=True)


if __name__ == "__main__":
    main()
