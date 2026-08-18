"""WS-DEPLOY (#127): the owner-approved deployment components, built in ISOLATION.

⛔ This branch (`feat/ws-deploy-news-executor`) must NOT be merged without an explicit owner
instruction — the owner's approval (2026-08-16) is conditional on the full verification walk:
replay parity against the committed M3 evidence, qty linearity, monitor era-proofs, and the
server-side golden gate for the engine's qty hook.

Components:
  schedule.py          the release schedule: generator (from the TV calendar) + loader
  release_executor.py  the confirmed trade, exactly as pre-registered in #117 — replay + paper
  regime_monitor.py    rolling 24-CPI-event mean -> GO / STAND-DOWN (sticky), owner-cleared only
"""
