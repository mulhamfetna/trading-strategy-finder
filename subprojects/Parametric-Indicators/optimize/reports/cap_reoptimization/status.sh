#!/bin/bash
# One-screen status dashboard for whatever is running on the server. Fast (<2s), safe to call anytime.
#   ./status.sh            -> everything
#   ./status.sh campaign   -> just the 54-campaign progress
WSI=~/Mulham/wsg-i
now=$(date '+%H:%M:%S')

echo "════════════════════════════════════════════════════════════════════"
echo " SERVER STATUS  $now"
echo "════════════════════════════════════════════════════════════════════"

# ---- machine
load=$(uptime | sed 's/.*load average: //')
mem=$(free -g | awk 'NR==2{printf "%s/%s GB", $3, $2}')
echo " load: $load   mem: $mem   cores: $(nproc)"

# ---- what's running   (pipe through wc -l: `grep -c`/`pgrep -c` exit 1 on zero, and a `|| echo 0`
#      fallback then APPENDS a second 0, printing "0\n0" — which breaks the arithmetic below)
opt=$(pgrep -f 'python3 optimize/optimizer.py' 2>/dev/null | wc -l)
bench=$(pgrep -f 'bench_both.py' 2>/dev/null | wc -l)
echo " optimizer workers: $opt    benchmark: $bench"
echo

# ---- campaign progress
if [ -f "$WSI/cap_campaign.log" ]; then
    TOTAL=$(wc -l < "$WSI/caprun/jobs.txt" 2>/dev/null || echo 54)
    done_n=$(grep '^CHAMPION' "$WSI/cap_campaign.log" 2>/dev/null | wc -l)
    fail_n=$(grep '^FAILED'   "$WSI/cap_campaign.log" 2>/dev/null | wc -l)
    start=$(grep -m1 'started' "$WSI/cap_campaign.log" 2>/dev/null | grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}')

    echo " CAMPAIGN: $done_n/$TOTAL champions   ($fail_n failed)   started $start"
    if [ "$done_n" -gt 0 ] && [ -n "$start" ]; then
        s=$(date -d "$start" +%s); n=$(date +%s); el=$(( n - s ))
        rate=$(awk -v d="$done_n" -v e="$el" 'BEGIN{printf "%.2f", d/(e/3600)}')
        left=$(( TOTAL - done_n ))
        eta=$(awk -v l="$left" -v r="$rate" 'BEGIN{ if(r>0) printf "%.1f", l/r; else print "?" }')
        pct=$(awk -v d="$done_n" -v t="$TOTAL" 'BEGIN{printf "%.0f", 100*d/t}')
        # progress bar
        filled=$(( pct / 5 )); bar=""
        for i in $(seq 1 20); do [ $i -le $filled ] && bar="${bar}█" || bar="${bar}░"; done
        printf " [%s] %s%%   elapsed %dh%02dm   ETA ~%sh\n" "$bar" "$pct" $((el/3600)) $(((el%3600)/60)) "$eta"
    fi
    echo
    echo " in-flight:"
    for f in "$WSI"/caprun/*.log; do
        [ -f "$f" ] || continue
        grep -q '^__OK__' "$f" 2>/dev/null && continue
        name=$(basename "$f" .log)
        tr=$(grep -oE 'Trial [0-9]+' "$f" 2>/dev/null | tail -1 | grep -oE '[0-9]+')
        [ -n "$tr" ] && printf "   %-10s trial %5s / 5900  (%2d%%)\n" "$name" "$tr" $((tr*100/5900))
    done | head -22
    echo
    echo " last champions:"
    grep '^CHAMPION' "$WSI/cap_campaign.log" 2>/dev/null | tail -3 | cut -c1-110 | sed 's/^/   /'
fi

# ---- benchmark
if [ -f "$WSI/bench.log" ] && [ "$1" != "campaign" ]; then
    echo
    echo " BENCHMARK:"
    grep -E 'SPEEDUP|worker\(s\)|journal |postgres |projected|MATCH|passed|failed|ALLDONE' "$WSI/bench.log" 2>/dev/null | tail -8 | sed 's/^/   /'
fi
echo "════════════════════════════════════════════════════════════════════"
