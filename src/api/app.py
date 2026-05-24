"""FastAPI app entry point. Phase A of the FastAPI + Vue migration.

Run locally:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

The frontend (phase B) will hit these endpoints. CORS is permissive in
dev so a Vue Vite dev server at localhost:5173 can talk to us.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from dataclasses import asdict
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.schemas import (
    BoxBacktestRequest,
    Candle,
    CandlesRange,
    CandlesResponse,
    Metrics,
)
from src.exceptions import ConfigurationError, MissingDataFileError
from src.data.loader import load_data
from src.data.splitter import filter_by_date_range
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy, BoxStrategyParams


app = FastAPI(
    title="NQ Trading Dashboard API",
    description=(
        "Backend for the FastAPI + Vue dashboard. Wraps the existing "
        "Strategy/Backtester pipeline (iter 7) behind REST endpoints."
    ),
    version="2.0.0-dev",
)

# ---- No-fallback rule: exception handlers (see docs/CODING_RULES.md) ----

@app.exception_handler(ConfigurationError)
async def _handle_configuration_error(request: Request, exc: ConfigurationError) -> JSONResponse:
    """Map internal ConfigurationError to a 422 JSON body. The structured
    `code` / `message` / `system_status` shape matches what SSE workers
    emit as `event: error` so frontend clients see one consistent
    contract regardless of transport."""
    return JSONResponse(status_code=422, content=exc.to_payload())


@app.exception_handler(RequestValidationError)
async def _handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Wrap Pydantic ValidationError with system status. The no-fallback
    rule makes every request field required; missing/wrong-type fields
    surface here as a 422 with the list of validation errors plus the
    request path + body the caller actually sent."""
    body: Any
    try:
        body = await request.json()
    except Exception:
        body = None
    return JSONResponse(
        status_code=422,
        content={
            'code': 'request-validation-error',
            'message': 'One or more required fields are missing or invalid.',
            'system_status': {
                'path': str(request.url.path),
                'method': request.method,
                'errors': [
                    {'loc': list(e['loc']), 'msg': e['msg'], 'type': e['type']}
                    for e in exc.errors()
                ],
                'received_body': body,
            },
        },
    )


# CORS: dev allows the local Vite server only; override via env for prod.
_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        'TRADING_DASH_ALLOW_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# BUG-022: cap uploads to prevent OOM/disk-fill via /api/upload-data-file.
# 200 MB is well above the largest active CSV (~135 MB for 1min historical).
MAX_UPLOAD_BYTES = 200 * 1024 * 1024


# ---- helpers ---------------------------------------------------------

def _load_and_filter(
    data_path: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Shared load + date-range filter. Raises ConfigurationError /
    HTTPException with structured detail on failure."""
    if not os.path.exists(data_path):
        raise MissingDataFileError(data_path, role='candles')

    try:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid date format; use YYYY-MM-DD")

    if start_ts > end_ts:
        raise HTTPException(
            status_code=400,
            detail=f"start ({start}) is after end ({end})",
        )

    try:
        df = load_data(data_path)
    except MissingDataFileError:
        raise
    except Exception as exc:  # noqa: BLE001 - we surface message to caller
        raise HTTPException(status_code=500, detail=f"failed to load {data_path}: {exc}")

    df = filter_by_date_range(df, start=start, end=end)
    return df.reset_index(drop=True)


def _candles_from_df(df: pd.DataFrame) -> List[Candle]:
    """Convert an OHLCV DataFrame to a list of Candle models.

    BUG-016: if Date is a parsed `Timestamp` and a separate Time column
    exists, `astype(str)` on Date yields `"YYYY-MM-DD HH:MM:SS"`, and
    concatenating with Time produces the BUG-003 corruption pattern
    `"YYYY-MM-DD 00:00:00THH:MM:SS"`. Normalise via dt.strftime so the
    output always matches `^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}$`.
    """
    if len(df) == 0:
        return []
    # No-fallback rule: every column the chart needs must be present in the
    # input CSV; we do not silently substitute zero / NaN for missing OHLCV.
    required_cols = ('Open', 'High', 'Low', 'Close', 'Volume')
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ConfigurationError(
            f'Candle data missing required columns: {missing}.',
            code='missing-candle-columns',
            system_status={
                'missing_columns': missing,
                'available_columns': list(df.columns),
                'required_columns': list(required_cols),
                'hint': 'The 4h data CSV must carry Open/High/Low/Close/Volume columns.',
            },
        )
    timestamps: List[str]
    if 'Date' in df.columns and 'Time' in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df['Date']):
            dates = df['Date'].dt.strftime('%Y-%m-%d')
        else:
            dates = df['Date'].astype(str).str.slice(0, 10)
        times = df['Time'].astype(str)
        timestamps = [f"{d}T{t}" for d, t in zip(dates, times)]
    elif 'Date' in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df['Date']):
            timestamps = df['Date'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()
        else:
            timestamps = df['Date'].astype(str).tolist()
    elif 'timestamps' in df.columns:
        timestamps = df['timestamps'].astype(str).tolist()
    else:
        timestamps = [str(i) for i in range(len(df))]

    return [
        Candle(
            t=timestamps[i],
            o=float(df.iloc[i]['Open']),
            h=float(df.iloc[i]['High']),
            l=float(df.iloc[i]['Low']),
            c=float(df.iloc[i]['Close']),
            v=int(df.iloc[i]['Volume']),
        )
        for i in range(len(df))
    ]


# ---- endpoints -------------------------------------------------------

@app.get("/api/candles", response_model=CandlesResponse)
def get_candles(
    start: str = Query(..., description="Inclusive YYYY-MM-DD."),
    end: str = Query(..., description="Inclusive YYYY-MM-DD."),
    data_path: str = Query(..., description="Path to OHLCV CSV (required)."),
) -> CandlesResponse:
    df = _load_and_filter(data_path, start=start, end=end)
    candles = _candles_from_df(df)
    return CandlesResponse(
        candles=candles,
        count=len(candles),
        range=CandlesRange(start=start, end=end),
    )


@app.get("/api/health")
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "version": app.version}


@app.get("/api/boxes")
def get_boxes(
    start: str = Query(..., description="Start date YYYY-MM-DD."),
    end: str = Query(..., description="End date YYYY-MM-DD."),
    box_data_path: str = Query(..., description="Unified box CSV path (required)."),
    tick_threshold: float = Query(..., description="Points margin past edge before firing."),
) -> dict:
    """Return all box-level rectangles active in [start, end] for chart rendering."""
    bl = BoxLookup(
        unified_path=box_data_path,
        tick_threshold=tick_threshold,
    )
    rects = bl.get_box_rects(start, end)
    return {"boxes": rects}


@app.get("/api/data-files")
def list_data_files() -> dict:
    """Return the names of all .csv files in the project root directory."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    files = sorted(
        f for f in os.listdir(root)
        if f.lower().endswith('.csv') and os.path.isfile(os.path.join(root, f))
    )
    return {"files": files}


@app.post("/api/upload-data-file")
async def upload_data_file(file: UploadFile = File(...)) -> dict:
    """Accept a CSV upload, save it to the project root, return its path.

    BUG-022: caps the upload at MAX_UPLOAD_BYTES and streams in chunks
    instead of `await file.read()` so a multi-GB upload can't exhaust
    server memory. `basename` strips any traversal segments.
    """
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")
    safe_name = os.path.basename(file.filename)
    if not safe_name or safe_name in ('.', '..'):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dest = os.path.join(root, safe_name)
    # Defence-in-depth: resolved path must stay under repo root.
    if os.path.commonpath([os.path.realpath(dest), os.path.realpath(root)]) != os.path.realpath(root):
        raise HTTPException(status_code=400, detail="Invalid destination path.")

    written = 0
    CHUNK = 1024 * 1024  # 1 MB
    try:
        with open(dest, 'wb') as fh:
            while True:
                chunk = await file.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    fh.close()
                    os.remove(dest)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Upload exceeds {MAX_UPLOAD_BYTES} bytes.",
                    )
                fh.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        if os.path.exists(dest):
            os.remove(dest)
        raise HTTPException(status_code=500, detail=f"upload failed: {exc}")
    return {"path": safe_name, "bytes": written}


# ---- SSE helpers ------------------------------------------------------

_SENTINEL_DONE = object()


def _sse_format(event_type: str, data: Any) -> str:
    """Format a single Server-Sent Events frame."""
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _box_metrics(trades: List[Dict]) -> Dict[str, Any]:
    """Build a metrics dict for the box strategy trades.

    `profit_factor` and `sharpe_ratio` are `None` when undefined (no
    losses for PF, no variance / <2 trades for Sharpe) — the frontend
    renders "N/A" in that case. See BUG-011 in
    docs/bug-checklist-revision-history.md.
    """
    n = len(trades)
    if n == 0:
        return {
            'total_profit': 0.0,
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': None,
            'avg_profit': 0.0,
            'avg_loss': 0.0,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'expected_value': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': None,
            'wins': 0,
            'losses': 0,
        }
    wins = [t for t in trades if t['profit_dollars'] > 0]
    losses = [t for t in trades if t['profit_dollars'] <= 0]
    gross_profit = sum(t['profit_dollars'] for t in wins)
    gross_loss = sum(t['profit_dollars'] for t in losses)
    total_profit = gross_profit + gross_loss
    avg_profit = (gross_profit / len(wins)) if wins else 0.0
    avg_loss = (gross_loss / len(losses)) if losses else 0.0
    # Equity curve for drawdown + Sharpe
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    returns: List[float] = []
    for t in trades:
        equity += t['profit_dollars']
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
        returns.append(t['profit_dollars'])
    # Sharpe: mean / std of trade-level returns (no annualization here).
    # Undefined when n < 2 or all returns identical (std == 0).
    mean_r = sum(returns) / len(returns)
    if n < 2:
        sharpe: Optional[float] = None
    else:
        var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        std = var ** 0.5
        sharpe = (mean_r / std) if std > 0 else None
    # Profit factor: gross_profit / |gross_loss|. Undefined when no losses.
    profit_factor: Optional[float] = (
        (gross_profit / abs(gross_loss)) if gross_loss < 0 else None
    )
    return {
        'total_profit': total_profit,
        'total_trades': n,
        'win_rate': len(wins) / n * 100.0,
        'profit_factor': profit_factor,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'expected_value': mean_r,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'wins': len(wins),
        'losses': len(losses),
    }


def _trade_to_jsonable(trade: Dict) -> Dict:
    """Coerce numpy / pandas scalar types in the trade dict to plain Python types.

    ScalingStrategy and BoxStrategy both produce a `legs` array and an
    `avg_entry_price`. The 1-1-2 engine fills 3 legs; the box engine fills
    1 leg (or 1 big-candle leg). All known numeric fields are coerced
    explicitly; anything extra (box_signal, legs, ...) is passed through.
    """
    out: Dict = {
        'entry_idx': int(trade['entry_idx']),
        'exit_idx': int(trade['exit_idx']),
        'direction': trade['direction'],
        # Candle-grounded display prices (guaranteed to appear in the OHLC
        # of the corresponding bar). Distinct from the algorithm-effective
        # avg_entry_price / exit_price (SL-TP threshold line) which remain
        # below for PnL transparency.
        'entry_signal_price': float(trade['entry_signal_price']),
        'exit_close': float(trade['exit_close']),
        'avg_entry_price': float(trade['avg_entry_price']),
        'exit_price': float(trade['exit_price']),
        'contracts': int(trade['contracts']),
        'profit_points': float(trade['profit_points']),
        'profit_dollars': float(trade['profit_dollars']),
        'exit_reason': trade['exit_reason'],
        # Direct access — every trade the engine emits carries `legs`.
        # No silent fallback to []; if missing it indicates an engine bug.
        'legs': trade['legs'],
    }
    known = set(out.keys())
    for k, v in trade.items():
        if k not in known:
            out[k] = v
    return out


# ---- /api/backtest/box (master strategy, SSE-streamed) ----

def _box_event_stream(req: BoxBacktestRequest) -> Iterator[str]:
    """SSE stream for the master-strategy backtest."""
    start_wall = time.perf_counter()

    if not os.path.exists(req.data_path):
        yield _sse_format('error', MissingDataFileError(
            req.data_path, role='4h-candles'
        ).to_payload())
        return

    try:
        df = load_data(req.data_path)
    except ConfigurationError as exc:
        yield _sse_format('error', exc.to_payload())
        return
    except Exception as exc:  # noqa: BLE001
        yield _sse_format('error', {
            'code': 'data-load-failed',
            'message': f'failed to load {req.data_path}: {exc}',
            'system_status': {
                'data_path': req.data_path,
                'exception_type': type(exc).__name__,
            },
        })
        return

    if req.start and req.end:
        try:
            df = filter_by_date_range(df, start=req.start, end=req.end)
        except Exception as exc:  # noqa: BLE001
            yield _sse_format('error', {'detail': f'date filter failed: {exc}'})
            return

    if len(df) == 0:
        yield _sse_format('error', {'detail': 'no candles in the requested range'})
        return

    df = df.reset_index(drop=True)

    # Validate box files exist and construct BoxLookup. ConfigurationError /
    # MissingDataFileError propagate as structured SSE error frames.
    try:
        box_lookup = BoxLookup(
            unified_path=req.box_data_path,
            tick_threshold=req.params.box_tick_threshold,
        )
    except ConfigurationError as exc:
        yield _sse_format('error', exc.to_payload())
        return
    except Exception as exc:  # noqa: BLE001
        yield _sse_format('error', {
            'code': 'box-data-load-failed',
            'message': f'failed to load box data: {exc}',
            'system_status': {
                'box_data_path': req.box_data_path,
                'exception_type': type(exc).__name__,
            },
        })
        return

    q: "queue.Queue[Any]" = queue.Queue(maxsize=512)

    # BoxStrategyParams needs every dataclass field including the box CSV
    # path — the Pydantic model carries the params block (sizing, SL, TP)
    # and the BoxBacktestRequest carries the path.
    params_dict = {
        **req.params.model_dump(),
        'box_data_path': req.box_data_path,
    }
    strat = BoxStrategy(params=BoxStrategyParams(**params_dict), box_lookup=box_lookup)

    # Pre-compute box rects for the chart overlay
    # BUG-017: surface failures as a non-fatal warning instead of swallowing.
    box_rects: List[Dict] = []
    try:
        range_start = req.start or str(df['Date'].iloc[0])[:10]
        range_end   = req.end   or str(df['Date'].iloc[-1])[:10]
        box_rects = box_lookup.get_box_rects(range_start, range_end)
    except Exception as exc:
        yield _sse_format('warning', {
            'stage': 'box_rects_precompute',
            'message': f'box-rect overlay disabled ({exc}); trades still computed.',
        })

    progress_every = max(1, len(df) // 100)
    last_emitted_idx = [-progress_every]

    def on_progress(event: Dict) -> None:
        idx = event['current_idx']
        if (
            idx - last_emitted_idx[0] >= progress_every
            or idx == event['total'] - 1
        ):
            q.put(('progress', event))
            last_emitted_idx[0] = idx

    def worker():
        try:
            trades, _state = strat.backtest(df, on_progress=on_progress)
            elapsed_ms = int((time.perf_counter() - start_wall) * 1000)
            candles = _candles_from_df(df)
            metrics = Metrics.model_validate(_box_metrics(trades)).model_dump()
            complete_payload = {
                'metrics': metrics,
                'trades': [_trade_to_jsonable(t) for t in trades],
                'candles': [c.model_dump() for c in candles],
                'elapsed_ms': elapsed_ms,
                'boxes': box_rects,
            }
            q.put(('complete', complete_payload))
        except ConfigurationError as exc:
            # Structured error: ship the full system_status payload.
            q.put(('error', exc.to_payload()))
        except Exception as exc:  # noqa: BLE001
            q.put(('error', {
                'code': 'backtest-failed',
                'message': f'backtest failed: {exc}',
                'system_status': {'exception_type': type(exc).__name__},
                # Back-compat with older clients reading `detail`.
                'detail': f'backtest failed: {exc}',
            }))
        finally:
            q.put(_SENTINEL_DONE)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = q.get()
        if item is _SENTINEL_DONE:
            break
        event_type, data = item
        yield _sse_format(event_type, data)


@app.post("/api/backtest/box")
def post_box_backtest(req: BoxBacktestRequest):
    """Run the master strategy backtest as an SSE stream.

    Master strategy = 1-1-2 execution framework + TradingView Box
    directional oracle (see docs/MASTER_STRATEGY_GUIDE.md).
    """
    return StreamingResponse(
        _box_event_stream(req),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
