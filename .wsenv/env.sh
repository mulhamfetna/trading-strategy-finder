#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────────────────────────
# ISOLATED ENVIRONMENT — workstream "legacy-18-baseline"
#
# SOURCE THIS BEFORE EVERY COMMAND:   source .wsenv/env.sh
#
# WHY EACH LINE EXISTS. Two agents run on this device at the same time. Everything below is a
# resource that is SHARED by default and would silently cross-contaminate the two workstreams.
# ─────────────────────────────────────────────────────────────────────────────────────────────────
export WS_ROOT="/mnt/data/projects/trading/legacy18"
export WS_NAME="legacy-18-baseline"

# 1. THE L1 DISK CACHE — the dangerous one.
#    optimize/l2/payload.py: _DISK_CACHE = Path(tempfile.gettempdir()) / "wsh_l1_cache"
#    Python's gettempdir() honours TMPDIR. Without this, BOTH workstreams read and write the same
#    cached L1 results. If either one touches the engine, indicators, or fills, the other silently
#    consumes poisoned P&L and every number it reports is wrong with no error.
#    NOTE ON LOCATION: this is /tmp/ws-legacy18, NOT a directory inside the worktree. pytest's
#    tmp_path fixture refuses a temp root it does not own, and the worktree is root-owned, which
#    produced 48 errors ("The temporary directory ... is not owned by the current user"). /tmp entries
#    we create are owned by us. Isolation is unaffected: the cache lands at
#    /tmp/ws-legacy18/wsh_l1_cache while the other workstream uses /tmp/wsh_l1_cache.
export TMPDIR="${TMPDIR_WS:-/tmp/ws-legacy18}"
mkdir -p "$TMPDIR"

# 2. OPTUNA STORAGE — force the worktree-local per-TF SQLite under
#    subprojects/Parametric-Indicators/optimize/studies/ (that path derives from __file__, so the
#    worktree already separates it). WSH_STORAGE_URL must stay UNSET, or studies land in the shared
#    Postgres and the two workstreams collide by study name.
unset WSH_STORAGE_URL
unset WSH_JOURNAL_DIR

# 3. STUDY-NAME PREFIX — belt and braces. Even in a shared backend, every study this workstream
#    creates is namespaced. ALWAYS pass --study-prefix "$WS_PREFIX<something>".
export WS_PREFIX="lg18_"

# 4. PYTHON — this workstream's own venv.
export WS_PY="$WS_ROOT/.venv/bin/python3"

# 5. DATA — read-only and SHARED on purpose. Price history is not workstream-specific and copying it
#    would waste GBs. NEVER WRITE HERE.
#
#    A git worktree checks out TRACKED files only. The price data (ALL_STOCKS/, Full_Canldes_Data/,
#    data/) is UNTRACKED and so exists ONLY in the main checkout. Left unset, roots.py falls back to
#    REPO_ROOT = this worktree, finds no data, and tests fail with a FileNotFoundError that reads
#    like a code bug. That is the #94 data-root trap arriving from a new direction.
#
#    roots.py precedence: WSH_DATA_ROOT > WSH_DATA_BASE > REPO_ROOT.
export WSH_DATA_ROOT="${WSH_DATA_ROOT:-/mnt/data/projects/trading}"
export WSH_DATA_BASE="$WSH_DATA_ROOT"
#    ⚠️ This couples you to the main checkout's PATH — but not to its branch, since the data is
#    untracked and does not change when that workstream switches branches. If it is ever moved,
#    update this line.
#
#    On the SERVER these must instead be:
#      WSH_DATA_BASE=/home/dev/Mulham/wsg-i  WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data
#    Only ~/Mulham/wsg-i has ALL_STOCKS; the wrong root produces ~32 FAKE regressions.

# 6. THREAD CAPS — so a run here cannot starve the other workstream.
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4

# 7. THE INDICATOR SET — the whole point of this workstream. The pre-expansion registry: 18 keys,
#    12 classic + 6 SMC, in registry order. Pass as --only-indicators "$WS_IND18".
export WS_IND18="ema_trend,sma_trend,macd,vwap,keltner,obv,cci,rsi,stochastic,mfi,bollinger,adx,structure_trend,order_block,fvg,ifvg,breaker,cisd"

echo "[$WS_NAME] env loaded"
echo "  root    : $WS_ROOT"
echo "  TMPDIR  : $TMPDIR   (isolated L1 cache)"
echo "  python  : $WS_PY"
echo "  prefix  : $WS_PREFIX"
echo "  18 inds : $(echo $WS_IND18 | tr ',' '\n' | wc -l) keys"
