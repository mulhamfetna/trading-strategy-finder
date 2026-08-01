"""Derive the `best` packager from the eod1 one: same three-way report, different champion source."""
import ast
import pathlib

s = pathlib.Path("eod1_package.py").read_text()
s = s.replace('NAME = f"BOX_STRATEGY_CHAMPIONS_EOD_{STAMP}"', 'NAME = f"BOX_STRATEGY_CHAMPIONS_{STAMP}"')
s = s.replace('shutil.copytree(f"{BASE}/playbooks_backtester_eod1", f"{OUT}/backtester")',
              'shutil.copytree(f"{BASE}/playbooks_backtester_best", f"{OUT}/backtester")')
s = s.replace('for f in sorted(os.listdir(f"{BASE}/playbooks_eod1")):\n'
              '    shutil.copy(f"{BASE}/playbooks_eod1/{f}", f"{OUT}/playbooks/{f}")',
              'for f in sorted(os.listdir(f"{BASE}/playbooks_best")):\n'
              '    shutil.copy(f"{BASE}/playbooks_best/{f}", f"{OUT}/playbooks/{f}")')

# retitle the report: this bundle IS the deployed set, not one candidate in the race
s = s.replace('rep = [f"# Forced end-of-day champions — {STAMP}", "",\n'
              '       "## What this set is", "",',
              'rep = [f"# Box-strategy champions — DEPLOYED set, {STAMP}", "",\n'
              '       "## What this set is", "",')
s = s.replace('"Every one of these 54 strategies **closes its position at the end of the trading day**. None of them",\n'
              '       "hold overnight. They were re-optimized **from scratch** (cold start, 5,800 trials each, no warm start",\n'
              '       "from the existing champions) with the end-of-day close **forced on** — so their stops, targets,",\n'
              '       "indicator gate and bar cap are all tuned *for* a same-day horizon, rather than having the rule bolted",\n'
              '       "onto a strategy that was tuned to hold overnight.", "",\n'
              '       "Indicators run on the **1-minute frame** on every slot.", "",',
              '"54 strategies — 9 markets x 6 timeframes — and these are the ones actually running on the dashboard.",\n'
              '       "", "Each slot holds the **best of three candidates**, decided on the held-out 2026 year:", "",\n'
              '       "* **32 slots** kept the champion that was already deployed. No challenger beat it.",\n'
              '       "* **19 slots** took a cold-start champion re-optimized with the **end-of-day close forced on**,",\n'
              '       "  so its stops, targets and gate are tuned *for* a same-day horizon.",\n'
              '       "* **3 slots** took the incumbent with the end-of-day close simply switched on, no re-tuning.", "",\n'
              '       "Exit rules are therefore **mixed by design**: some strategies close at the bell, some hold, some cap",\n'
              '       "the number of bars they stay in. That mix is the finding, not an inconsistency — see below.", "",\n'
              '       "Indicators run on the **1-minute frame** on every slot.", "",')
s = s.replace('       "## Does forcing the bell close actually help?", "",',
              '       "## Does forcing the bell close actually help? Not as a blanket rule.", "",')
pathlib.Path("best_package.py").write_text(s)
ast.parse(s)
print("best_package.py: written, syntax OK")
