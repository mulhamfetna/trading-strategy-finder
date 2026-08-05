"""Do AMD's and Intel's own IR listing times agree with our EDGAR timestamps?

These two publish <time datetime="..."> for every release on one listing page, so a single fetch per
company yields many events. If they agree to the minute, that is the genuine independent minute-level
corroboration criterion C3 originally asked for — for these companies at least.
"""
import csv
import re
import urllib.request
from datetime import datetime

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
TABLE = ("/mnt/data/projects/trading/legacy18/subprojects/Parametric-Indicators/"
         "optimize/earnings/data/earnings_timestamps_FINAL.csv")

SITES = {
    "AMD":  "https://ir.amd.com/news-events/press-releases",
    "INTC": "https://www.intc.com/news-events/press-releases",
}
# The listings paginate; walk a few pages to reach back to 2024.
PAGE = {"AMD": "?page={}", "INTC": "?page={}"}
ROW = re.compile(r'<time[^>]*datetime="([0-9T:\-\+\.Z]{16,32})"[^>]*>(.*?)</time>(.*?)(?=<time|\Z)',
                 re.I | re.S)

with open(TABLE) as fh:
    rows = list(csv.DictReader(fh))

for tick, base in SITES.items():
    ours = {r["event_et"][:10]: r for r in rows if r["ticker"] == tick}
    scraped: dict[str, str] = {}
    for p in range(0, 8):
        url = base + (PAGE[tick].format(p) if p else "")
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as resp:
                html = resp.read(900_000).decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"  {tick} page {p}: {type(exc).__name__}")
            break
        found = re.findall(r'<time[^>]*datetime="([0-9T:\-\+\.Z]{16,32})"', html)
        for f in found:
            scraped.setdefault(f[:10], f)
        if not found:
            break

    print(f"\n=== {tick} ===")
    print(f"  scraped release timestamps : {len(scraped)}  (dates {min(scraped, default='-')} .. {max(scraped, default='-')})")
    print(f"  our earnings events        : {len(ours)}")
    hits = []
    for d, r in sorted(ours.items()):
        s = scraped.get(d)
        if not s:
            print(f"  {d}  ours={r['event_et'][11:]}   site=(no release listed that day)")
            continue
        st = datetime.fromisoformat(s.replace("Z", "+00:00").replace("+00:00", ""))
        ot = datetime.fromisoformat(r["event_et"])
        delta = (ot - st.replace(tzinfo=None)).total_seconds()
        hits.append(delta)
        flag = "  <-- >2 min apart" if abs(delta) > 120 else ""
        print(f"  {d}  ours={ot:%H:%M:%S}  site={st:%H:%M:%S}   delta={delta:+.0f}s{flag}")
    if hits:
        hits.sort()
        med = hits[len(hits) // 2]
        print(f"  matched {len(hits)}/{len(ours)} — median delta {med:+.0f}s, "
              f"within +-120s: {sum(1 for h in hits if abs(h) <= 120)}/{len(hits)}")
