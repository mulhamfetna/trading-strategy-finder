# Box-strategy champions — forced end-of-day set (2026-07-13)

54 trading strategies: **9 markets × 6 timeframes**. Every one **closes at the end of the trading day** and
never holds a position overnight.

## What's in here

| folder | what it is |
|---|---|
| `playbooks/` | one PDF per champion (54) — what it trades, the exact settings, full tearsheet, 2026 out-of-sample, and when NOT to trade it |
| `backtester/` | a standalone, self-contained backtester. It reproduces every number in every playbook, to the dollar, without the main repo |
| `backtester/champions/` | the 54 champion files (JSON) — the strategies themselves |
| `MEGA_REPORT.md` | the three-way comparison: are these actually better than the champions already deployed? |

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
* `MEGA_REPORT.md` says, slot by slot, whether the forced-bell-close champion actually beats the one already
  deployed. For many slots **it does not** — read it before switching anything.

---
Mulham Fetna · contact@mulhamfetna.com · ORCID 0009-0006-4432-798X · github.com/mulhamfetna
