"""Derive the `best` (deployed, best-per-slot) bundle scripts from the proven eod1 ones."""
import pathlib

s = pathlib.Path("eod1_gen_bundle.py").read_text()
s = s.replace("playbooks_backtester_eod1", "playbooks_backtester_best")
s = s.replace('presets = json.load(open(f"{BASE}/presets_raw_eod1.json"))',
              'SRC_TXT = {"deployed": "incumbent (held — no challenger beat it out-of-sample)",\n'
              '           "eod1": "cold-start re-optimization with the end-of-day close FORCED",\n'
              '           "bolt-on": "incumbent + end-of-day close switched on (not re-tuned)"}\n\n'
              'presets = json.load(open(f"{BASE}/presets_raw_best.json"))')
s = s.replace('ver = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/eod1_verified.json")) if r.get("eod1")}',
              'met = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/playbook_metrics_best.json"))}')
s = s.replace('    m = ver.get((inst, tf))', '    m = met.get((inst, tf))')
s = s.replace('    f, o = m["eod1"]["full"], m["eod1"]["oos2026"]',
              '    f, o = m["full"]["boxes"], m["oos2026"]["boxes"]\n    src = m["source"]')
# the DEPLOYED set is best-per-slot: exit rules are MIXED by design (32 kept champions use none/bars)
s = s.replace('CAP_TXT = {"eod": "end-of-day exit (never holds overnight)",\n'
              '           "both": "max-hold {n} bars OR end-of-day — whichever fires first"}',
              'CAP_TXT = {"none": "no time cap", "bars": "max-hold {n} bars",\n'
              '           "eod": "end-of-day exit (never holds overnight)",\n'
              '           "both": "max-hold {n} bars OR end-of-day — whichever fires first"}')
s = s.replace('    if cm not in CAP_TXT:\n'
              '        raise SystemExit(f"{slot}: cap_mode={cm!r} — this set is supposed to close at the bell")',
              '    if cm not in CAP_TXT:\n        raise SystemExit(f"{slot}: unknown cap_mode={cm!r}")')
s = s.replace('             f"cold-start re-optimization with the end-of-day close FORCED{warn}")',
              '             f"{SRC_TXT[src]}{warn}")')
pathlib.Path("best_gen_bundle.py").write_text(s)

v = pathlib.Path("eod1_bundle_verify.py").read_text()
v = v.replace("playbooks_backtester_eod1", "playbooks_backtester_best")
v = v.replace("eod1_bundle_verify.json", "best_bundle_verify.json")
pathlib.Path("best_bundle_verify.py").write_text(v)

for f in ("best_gen_bundle.py", "best_bundle_verify.py"):
    import ast
    ast.parse(pathlib.Path(f).read_text())
    print(f"{f}: written, syntax OK")
