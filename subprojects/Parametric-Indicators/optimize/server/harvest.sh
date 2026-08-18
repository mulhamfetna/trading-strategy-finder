#!/usr/bin/env bash
# Bring home EVERYTHING the server has that git does not know about (#94, Layer 4).
#
# THE DEFECT THIS REPLACES. `remote_wsi.sh cmd_pull` brings results home from a hardcoded allow-list:
# `optimize/results/`, `logs/`, and the single filename `WS-I_RESULTS.md`. Anything written anywhere
# else is invisible to it. The string `WS-I_RESULTS_GC` appears ZERO times in that script, so when each
# new instrument was onboarded its report was written on the server and the return path never learned
# about it — NINE of ten per-instrument reports stranded. Same mechanism stranded GC-02's walk-forward
# scripts (bd8b229), issue #2's re-optimization (8e4f2cf) and the v5.1.0 closeout (06c9dc3).
#
# An allow-list has to be maintained, and it silently stops matching reality the moment it is not. So
# this asks git instead: everything untracked or modified, minus what git is deliberately ignoring.
# The list can only go stale if git itself does.
#
#   ./harvest.sh list     what would come back, with sizes (ALWAYS run this first)
#   ./harvest.sh pull     bring it into ../../../../../ (the local repo), preserving paths
#   ./harvest.sh diff     after pull: show what changed, for review before committing
set -euo pipefail
_HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "$_HERE/../../../meta-prophet/server/server.env"
LOCAL_REPO="$(cd "$_HERE/../../../.." && pwd)"
REMOTE_REPO="/home/dev/Mulham/code"
SSH_OPTS=(-p "$SRV_PORT" -i "$SRV_KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
          -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 -o ServerAliveInterval=30)
srv() { ssh "${SSH_OPTS[@]}" "${SRV_USER}@${SRV_HOST}" "$@"; }
RSYNC_E="ssh -p $SRV_PORT -i $SRV_KEY -o IdentitiesOnly=yes -o BatchMode=yes"
log() { printf '\033[1;36m[harvest]\033[0m %s\n' "$*"; }

# --others --modified: untracked plus changed. --exclude-standard honours .gitignore, so build output
# and caches do not come along. -z + NUL handling so filenames with spaces survive.
# REGULAR FILES ONLY, with sizes. git lists a fully-untracked path as one entry even when it is a
# symlink to somewhere else entirely — `subprojects/Parametric-Indicators/data` is exactly that, a link
# into a 38 GB data tree. Following it would drag the whole thing home. So: resolve to real files, skip
# symlinks and directories, and report bytes so the size guard has something to judge.
_remote_rows() {                    # emits: <bytes>\t<path>
  # `stat` reports the TYPE, so regular files can be kept and directories/symlinks dropped. That
  # matters: git lists a fully-untracked path as one entry even when it is a symlink into somewhere
  # else — `subprojects/Parametric-Indicators/data` is exactly that, a link into a 38 GB tree, and
  # following it would drag the whole thing home.
  #
  # Two earlier attempts failed, both silently, which is why this is tested against a live probe file:
  #   xargs sh -c 'test -f ...'   exits 123 as soon as one test fails, and `set -e` then killed the
  #                               whole command on the very symlink it was meant to skip.
  #   xargs find -type f          find wants PATHS BEFORE the expression; xargs appends them AFTER, so
  #                               find parsed them as expressions and matched nothing. It reported a
  #                               clean tree while a real untracked report sat there — the exact
  #                               failure mode this script exists to end.
  # Separator is '|', not '\t': a tab written as \t does not survive the quoting layers between here
  # and stat on the far side of ssh — it arrived as a literal backslash-t and every field split failed
  # (caught by the live probe, not by reading the code). Paths containing '|' are skipped loudly rather
  # than silently mis-parsed.
  srv "cd '$REMOTE_REPO' && git ls-files --others --modified --exclude-standard -z \
       | xargs -0 -r stat -c '%F|%s|%n' -- 2>/dev/null" \
    | awk -F'|' '
        $1 != "regular file" { next }
        NF != 3 { print "  !! skipped (path contains |): " $0 > "/dev/stderr"; next }
        { print $2 "\t" $3 }' || true
}

_remote_list() { _remote_rows | cut -f2- ; }

MAX_MB="${HARVEST_MAX_MB:-1024}"     # size guard; raise deliberately, never by accident

cmd_list() {
  log "asking git on the server what it does not track (NOT an allow-list)"
  local rows; rows="$(_remote_rows)"
  if [ -z "$rows" ]; then log "nothing to harvest — the server tree is clean"; return 0; fi
  printf '%s\n' "$rows" | awk -F'\t' '{printf "  %10.2f KB  %s\n", $1/1024, $2}'
  printf '%s\n' "$rows" | awk -F'\t' -v m="$MAX_MB" \
    '{n++; t+=$1} END {printf "\n  %d file(s), %.1f MB (guard: %s MB)\n", n, t/1048576, m}'
}

cmd_pull() {
  local rows; rows="$(_remote_rows)"
  if [ -z "$rows" ]; then log "nothing to harvest — the server tree is clean"; return 0; fi
  local mb; mb=$(printf '%s\n' "$rows" | awk -F'\t' '{t+=$1} END {printf "%.0f", t/1048576}')
  if [ "$mb" -gt "$MAX_MB" ]; then
    log "REFUSING: ${mb} MB exceeds the ${MAX_MB} MB guard."
    log "Run './harvest.sh list' and look at it. If it is genuinely wanted:"
    log "  HARVEST_MAX_MB=$((mb + 1)) ./harvest.sh pull"
    return 1
  fi
  local list; list="$(mktemp)"
  printf '%s\n' "$rows" | cut -f2- > "$list"
  local n; n=$(wc -l < "$list")
  log "pulling $n file(s), ${mb} MB, into $LOCAL_REPO (paths preserved)"
  rsync -az --info=stats1 --files-from="$list" -e "$RSYNC_E" \
        "${SRV_USER}@${SRV_HOST}:$REMOTE_REPO/" "$LOCAL_REPO/"
  rm -f "$list"
  log "done. NOTHING IS COMMITTED — run './harvest.sh diff' and review before you commit."
}

cmd_diff() { cd "$LOCAL_REPO" && git status --short && echo && git diff --stat; }

case "${1:-list}" in
  list) cmd_list ;;
  pull) cmd_pull ;;
  diff) cmd_diff ;;
  *) echo "usage: $0 {list|pull|diff}" >&2; exit 2 ;;
esac
