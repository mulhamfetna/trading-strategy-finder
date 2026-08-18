# Box-strategy champions — deployed set (2026-07-14)

54 trading strategies: **9 markets x 6 timeframes**. This is the set actually running on the dashboard.

## What's in here

| folder | what it is |
|---|---|
| `playbooks/` | one PDF per champion (54) — what it trades, the exact settings, full tearsheet, 2026 out-of-sample, and when NOT to trade it |
| `backtester/` | a standalone backtester. It reproduces every number in every playbook, to the dollar, without the main repo |
| `backtester/champions/` | the 54 champion files (JSON) — the strategies themselves |
| `MEGA_REPORT.md` | how each slot was chosen, and the three-way comparison behind it |

## Run it

```bash
cd backtester
pip install -r requirements.txt
python backtest.py --champion champions/NQ_4h.json --data <your data dir>
```

## Read this before trading any of it

* The **2026** column is the only honest one. Every strategy here was *chosen* by a search that read the
  in-sample data, so its in-sample profit flatters it by construction.
* Slots that lose money are **included and flagged**, not removed.
* Exit rules differ by slot on purpose — see `MEGA_REPORT.md`.

---
Mulham Fetna · contact@mulhamfetna.com · ORCID 0009-0006-4432-798X · github.com/mulhamfetna
