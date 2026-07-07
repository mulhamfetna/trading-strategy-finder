# Trading Dashboard — Quick Guide

The **Unified Dashboard — Layer 1** is a web page for backtesting the box strategy on any
instrument + timeframe. It runs on the AMD server and is shared: anyone who can reach the
server can open it in a browser. **You don't install anything — you just open a URL.**

---

## 1. Open it (users)

Point your browser at the server on port **8200**:

| From | URL |
|------|-----|
| On the private network / VPN | **http://192.168.50.62:8200/** |
| Public IP (if allowed to you) | http://78.89.209.212:8200/ |
| Sitting on the server itself | http://localhost:8200/ |

> Recommended: use the **private / VPN** address. The dashboard has **no login** — anyone
> who can reach the URL can use it, so keep it on the private network / VPN, not the open
> internet.

If the page doesn't load, the service may be down — ask the admin to run `./dash.sh start`
(see §3).

---

## 2. Use it (the 30-second version)

1. **Instrument** (top-left dropdown) — pick NQ, ES, GC (Gold), SI (Silver), RTY (Russell), YM (Dow).
2. **Timeframe (primary)** — pick 4h / 2h / 1h / 15m / 5m / 2m.
   Each instrument+timeframe loads its **champion** (the best-found settings) automatically.
3. Click the green **▶ Run** button (top-right).
4. Read the results:
   - **L1 tab** — the main strategy. Cards show **Total P/L**, **Max Drawdown**, **Win rate**,
     **Profit Factor**, number of trades, plus the price / equity / drawdown charts.
   - **L2** and **Σ Combined** tabs — the second layer and the two combined; switch freely,
     no re-run needed.
5. **"✓ results match current settings"** in the header means what's on screen matches the
   settings. If you change any setting the header turns to a *dirty* state — click **Run** again.

**Tips**
- You can edit any setting (SL/TP, indicators, gate, etc.) and Run to experiment — it does
  **not** change anyone else's session or the saved champion; it's just your view.
- **Heavy timeframes (2m, 5m)** crunch a lot of data — a Run can take a few to ~30 seconds.
  That's normal. The server has the RAM for it; your laptop would not.
- To go back to the saved champion after editing, re-pick the instrument/timeframe (or click
  **Reset to selected**).

---

## 3. Run / refresh / stop it (admin — Mulham)

All from one script on the server: **`~/Mulham/wsg-i/dash.sh`**

```bash
ssh amd-trading                     # log into the server
cd ~/Mulham/wsg-i

./dash.sh start      # start it (no-op if already running)
./dash.sh status     # is it up? shows pid, URLs, and a health check
./dash.sh refresh    # RESTART to pick up code / champion changes  ← use this after edits
./dash.sh stop       # stop it
./dash.sh logs       # tail the live server log (Ctrl-C to exit the tail)
```

### When do I need `refresh`?
- A **browser refresh (F5) reloads only the page (frontend)** — enough after editing HTML/CSS.
- Any **backend change** (Python: `server.py`, engine, champion JSONs, new optimizer results)
  needs **`./dash.sh refresh`** to restart the server process. When in doubt, `refresh`.

### Robustness
- The dashboard runs under a small **supervisor**: it **survives you logging out** and
  **auto-restarts within ~2 s if it ever crashes**. You normally never need to touch it.
- Logs go to `~/Mulham/wsg-i/logs/dashboard.log`.
- To confirm it's listening on the network: `./dash.sh status` (should show `HTTP 200`).

---

## 4. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page won't load | `./dash.sh status`; if not running → `./dash.sh start` |
| Edited code but page looks the same | `./dash.sh refresh`, then hard-refresh the browser |
| A Run seems stuck | heavy TF (2m/5m) just takes longer; give it up to ~30 s |
| Red banner / error | copy the message and send to Mulham; check `./dash.sh logs` |
| Want it reachable off-VPN | that's a firewall/exposure decision — ask Mulham first (no auth on the app) |

---

*Server: AMD box (`dev@78.89.209.212`, private `192.168.50.62`). App lives at
`~/Mulham/wsg-i/Parametric-Indicators`, control script at `~/Mulham/wsg-i/dash.sh`.*
