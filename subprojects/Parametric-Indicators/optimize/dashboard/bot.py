"""Telegram bot — long-polling, allowlist-guarded, shares control.py. Pure dispatch (handle_command,
allowed, new_champions) is unit-tested; the network loop run() is started only by __main__.

Security: token from TELEGRAM_BOT_TOKEN (env / gitignored dashboard.env, NEVER committed); only chat IDs in
TELEGRAM_ALLOWED_CHAT_IDS may issue commands — everyone else gets DENIED.
"""
from __future__ import annotations

import os
import time

from optimize.dashboard import control

DENIED = "⛔ not authorized"


def _allow_ids() -> set[int]:
    return {int(x) for x in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if x.strip()}


def allowed(chat_id: int) -> bool:
    return chat_id in _allow_ids()


def handle_command(text: str, chat_id: int) -> str:
    """Pure command dispatch → reply string. Allowlist enforced first."""
    if not allowed(chat_id):
        return DENIED
    cmd = (text or "").strip().split()[0] if (text or "").strip() else ""
    if cmd == "/status":
        s = control.status()
        rows = s.get("studies", [])
        return "\n".join(f"{x.get('tf','?')}: {x.get('complete', 0)} complete" for x in rows) or "no studies"
    if cmd == "/stop":
        return "paused ⏸" if control.stop().get("ok") else "stop failed"
    if cmd == "/resume":
        return "resumed ▶" if control.resume({}).get("ok") else "resume failed"
    if cmd == "/pull":
        p = control.build_bundle("lite", stamp=str(int(time.time())))
        return f"lite bundle ready: {p}"
    return "commands: /status /stop /resume /pull /pareto"


def new_champions(prev: dict, cur: dict) -> list[tuple[str, float]]:
    """(tf, best) pairs whose best fold P/L improved vs prev — drives push notifications."""
    out = []
    for tf, best in cur.items():
        if best > prev.get(tf, float("-inf")):
            out.append((tf, best))
    return out


def run():                                            # pragma: no cover (network loop)
    from telegram.ext import Application, MessageHandler, filters
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    async def on_msg(update, ctx):
        await update.message.reply_text(handle_command(update.message.text or "", update.effective_chat.id))

    app.add_handler(MessageHandler(filters.TEXT, on_msg))
    app.run_polling()


if __name__ == "__main__":                            # pragma: no cover
    run()
