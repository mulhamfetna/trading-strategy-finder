"""WS-AS instrument registry — the no-mix contract.

The ONLY place instrument identity (candle paths + box CSV + output token) lives.
Every instrument runs the *identical* frozen pipeline (same `BoxLookup` hour>=18 roll,
same weekly+monthly levels) — decisions D1/D2 = "follow NQ logic uniformly". So there
is no per-instrument rule, only per-instrument data location. This makes cross-instrument
mixing impossible by construction: a token resolves to exactly one candle dir + one box.

Paths are anchored at the repo root (…/trading). Candle files are `<prefix>_<TF>.csv`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_ALL = os.path.join(_REPO_ROOT, 'ALL_STOCKS')

TIMEFRAMES: List[str] = ['1m', '2m', '5m', '15m', '1h', '2h', '4h']
PRESETS: List[str] = ['full', '2025', '2026']


@dataclass(frozen=True)
class Instrument:
    token: str          # output token, used in filenames + delivery dir (e.g. "QQQ-ETH")
    candle_dir: str     # dir holding <prefix>_<TF>.csv
    candle_prefix: str  # filename prefix (e.g. "QQQ_ETH")
    box_csv: str        # the unified per-instrument box file (_full_data.csv)

    def candle_csv(self, tf: str) -> str:
        return os.path.join(self.candle_dir, f'{self.candle_prefix}_{tf}.csv')

    def delivery_name(self) -> str:
        return f'{self.token}_SIGNALS_DELIVERY'


def _cdir(*parts: str) -> str:
    return os.path.join(_ALL, 'CANDLES', *parts)


def _box(*parts: str) -> str:
    return os.path.join(_ALL, 'BOXS', *parts)


def _shifted_box(token: str) -> str:
    # Non-NQ instruments read the -1-workday-shifted box (written by onboard_stock.py) so the delivered
    # signals and the backtest use the same box. NQ is never shifted (frozen anchor).
    return os.path.join(os.path.dirname(__file__), 'shifted_boxes', f'{token}_full_data_shifted.csv')


REGISTRY: Dict[str, Instrument] = {
    'NQ': Instrument(
        token='NQ',
        candle_dir=_cdir('CME', 'NQ_Continuous_Data'), candle_prefix='NQ',
        box_csv=_box('CME', 'NQ', 'NQ_full_data.csv')),
    'ES': Instrument(
        token='ES',
        candle_dir=_cdir('CME', 'ES_Continuous_Data'), candle_prefix='ES',
        box_csv=_shifted_box('ES')),                 # shifted -1 workday (2026-07-06); raw box retired
    'GC': Instrument(
        token='GC',
        candle_dir=_cdir('COMEX', 'GC_Continuous_Data'), candle_prefix='GC',
        box_csv=_shifted_box('GC')),
    'SI': Instrument(
        token='SI',
        candle_dir=_cdir('COMEX', 'SI_Continuous_Data'), candle_prefix='SI',
        box_csv=_shifted_box('SI')),
    'HG': Instrument(
        token='HG',
        candle_dir=_cdir('COMEX', 'HG_Continuous_Data'), candle_prefix='HG',
        box_csv=_shifted_box('HG')),                 # Copper, COMEX full (pv 25,000); shifted -1 workday
    'CL': Instrument(
        token='CL',
        candle_dir=_cdir('NYMEX', 'CL_Continuous_Data'), candle_prefix='CL',
        box_csv=_shifted_box('CL')),                 # Crude Oil, NYMEX full (pv 1,000); shifted -1 workday
    'NG': Instrument(
        token='NG',
        candle_dir=_cdir('NYMEX', 'NG_Continuous_Data'), candle_prefix='NG',
        box_csv=_shifted_box('NG')),                 # Natural Gas, NYMEX full (pv 10,000); shifted -1 workday
    'RTY': Instrument(
        token='RTY',
        candle_dir=_cdir('CME', 'RTY_Continuous_Data'), candle_prefix='RTY',
        box_csv=_shifted_box('RTY')),
    'YM': Instrument(
        token='YM',
        candle_dir=_cdir('CME', 'YM_Continuous_Data'), candle_prefix='YM',
        box_csv=_shifted_box('YM')),
    'QQQ-RTH': Instrument(
        token='QQQ-RTH',
        candle_dir=_cdir('ETF', 'QQQ_Data', 'RTH'), candle_prefix='QQQ_RTH',
        box_csv=_box('ETF', 'RTH', 'QQQ', 'QQQ_full_data.csv')),
    'QQQ-ETH': Instrument(
        token='QQQ-ETH',
        candle_dir=_cdir('ETF', 'QQQ_Data', 'ETH'), candle_prefix='QQQ_ETH',
        box_csv=_box('ETF', 'ETH', 'QQQ', 'QQQ_full_data.csv')),
    'SQQQ-RTH': Instrument(
        token='SQQQ-RTH',
        candle_dir=_cdir('ETF', 'SQQQ_Data', 'RTH'), candle_prefix='SQQQ_RTH',
        box_csv=_box('ETF', 'RTH', 'SQQQ', 'SQQQ_full_data.csv')),
    'SQQQ-ETH': Instrument(
        token='SQQQ-ETH',
        candle_dir=_cdir('ETF', 'SQQQ_Data', 'ETH'), candle_prefix='SQQQ_ETH',
        box_csv=_box('ETF', 'ETH', 'SQQQ', 'SQQQ_full_data.csv')),
}

TOKENS: List[str] = list(REGISTRY.keys())
