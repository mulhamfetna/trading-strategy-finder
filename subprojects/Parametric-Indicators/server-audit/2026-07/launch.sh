#!/usr/bin/env bash
pkill -9 -f optimize/optimizer.py >/dev/null 2>&1 || true
sleep 2
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE='/home/dev/Mulham/wsg-i' WSG_DATA_ROOT='/home/dev/Mulham/wsg-i/data' WSH_STORAGE_URL='postgresql://wsh:b4246c04d257332a4eb3d282d64ff0dd@127.0.0.1:55432/wsh' WSI_INSTRUMENT='NQ'
[ -z "$WSH_STORAGE_URL" ] && [ -f '/home/dev/Mulham/wsg-i/pg.env' ] && { set -a; . '/home/dev/Mulham/wsg-i/pg.env'; set +a; }
cd '/home/dev/Mulham/wsg-i/Parametric-Indicators'; mkdir -p optimize/studies '/home/dev/Mulham/wsg-i/logs'
for pair in 15m:5 ; do
  tf=${pair%%:*}; w=${pair##*:}
  python3 -c "import optuna,sqlite3,os; n='wsh4_${tf}'; per='optimize/studies/wsh_${tf}.db'; sh='optimize/studies/wsh.db'; h=lambda d:(os.path.exists(d) and n in [r[0] for r in sqlite3.connect(d).execute('SELECT study_name FROM studies')]); db=(sh if (not os.path.exists(per) and h(sh)) else per); url=(os.environ.get('WSH_STORAGE_URL') or 'sqlite:///'+db); optuna.create_study(study_name=n, storage=url, directions=['maximize','maximize','maximize'], load_if_exists=True); print('study',n,'ready (', 'postgres' if url.startswith('postgres') else 'sqlite', ')')"
  for i in $(seq 1 $w); do setsid bash '/home/dev/Mulham/wsg-i/worker.sh' "$tf" </dev/null >> "/home/dev/Mulham/wsg-i/logs/${tf}.log" 2>&1 & done
  echo "$tf: $w setsid workers → target 10 (independent, watchdog/respawn, idempotent)"
done
# NO wait — each worker is its own setsid session and persists independently; the launcher exits here.
