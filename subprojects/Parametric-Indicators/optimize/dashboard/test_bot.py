"""Telegram bot tests (optimize/dashboard/bot.py) — allowlist + dispatch + champion-diff. No network."""
from __future__ import annotations

import os
import warnings

warnings.filterwarnings("ignore")
os.environ["TELEGRAM_ALLOWED_CHAT_IDS"] = "111,222"

from optimize.dashboard import bot


def test_allowlist():
    assert bot.allowed(111) and bot.allowed(222)
    assert not bot.allowed(999) and not bot.allowed(0)


def test_blocked_chat_denied():
    assert bot.handle_command("/stop", chat_id=999) == bot.DENIED


def test_status_dispatch(monkeypatch):
    monkeypatch.setattr(bot.control, "status", lambda: {"studies": [{"tf": "4h", "complete": 10}]})
    msg = bot.handle_command("/status", chat_id=111)
    assert "4h" in msg and "10" in msg


def test_stop_dispatch(monkeypatch):
    monkeypatch.setattr(bot.control, "stop", lambda: {"ok": True})
    assert "paused" in bot.handle_command("/stop", chat_id=111)


def test_resume_dispatch(monkeypatch):
    monkeypatch.setattr(bot.control, "resume", lambda cfg: {"ok": True})
    assert "resumed" in bot.handle_command("/resume", chat_id=222)


def test_unknown_command_help():
    assert "commands:" in bot.handle_command("/wat", chat_id=111)


def test_champion_change_detected():
    assert bot.new_champions({"4h": 33587.0}, {"4h": 35000.0}) == [("4h", 35000.0)]
    assert bot.new_champions({"4h": 35000.0}, {"4h": 35000.0}) == []
    assert bot.new_champions({}, {"2h": 100.0}) == [("2h", 100.0)]
