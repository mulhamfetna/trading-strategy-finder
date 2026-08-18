"""Feasibility probe: which of the 19 companies publish machine-readable release TIMES on their IR site?

Scrapes each company's press-release LISTING page once (not per event) and looks for either
<time datetime="..."> elements or JSON-LD datePublished. If a listing exposes times for all releases,
one fetch per company gives an independent minute-level cross-check for every event.
"""
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

SITES = {
    "AAPL":  "https://www.apple.com/newsroom/archive/",
    "MSFT":  "https://news.microsoft.com/category/press-releases/",
    "NVDA":  "https://nvidianews.nvidia.com/news",
    "AMZN":  "https://press.aboutamazon.com/press-release-archive",
    "GOOGL": "https://blog.google/press/",
    "META":  "https://investor.atmeta.com/investor-news/default.aspx",
    "AVGO":  "https://investors.broadcom.com/news-releases",
    "TSLA":  "https://ir.tesla.com/press",
    "MU":    "https://investors.micron.com/news-releases",
    "WMT":   "https://corporate.walmart.com/news/",
    "AMD":   "https://ir.amd.com/news-events/press-releases",
    "ASML":  "https://www.asml.com/en/news/press-releases",
    "INTC":  "https://www.intc.com/news-events/press-releases",
    "CSCO":  "https://investor.cisco.com/news/news-details/default.aspx",
    "AMAT":  "https://ir.appliedmaterials.com/press-releases",
    "COST":  "https://investor.costco.com/news-releases",
    "LRCX":  "https://investor.lamresearch.com/news-releases",
    "PLTR":  "https://investors.palantir.com/news-details",
    "NFLX":  "https://ir.netflix.net/investor-news-and-events/financial-releases/default.aspx",
}

TIME_TAG = re.compile(r'<time[^>]*datetime="([^"]{10,32})"', re.I)
JSONLD = re.compile(r'"date(?:Published|Modified)"\s*:\s*"([^"]{10,32})"', re.I)
WITH_CLOCK = re.compile(r"T\d{2}:\d{2}")

for tick, url in SITES.items():
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            html = r.read(600_000).decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"  {tick:<6} FAIL   {type(exc).__name__}")
        continue
    t = TIME_TAG.findall(html)
    j = JSONLD.findall(html)
    allts = t + j
    clocked = [x for x in allts if WITH_CLOCK.search(x)]
    verdict = "USABLE" if clocked else ("dates only" if allts else "no timestamps")
    sample = clocked[0] if clocked else (allts[0] if allts else "-")
    print(f"  {tick:<6} {verdict:<14} time-tags={len(t):<4} json-ld={len(j):<4} with-clock={len(clocked):<4} eg {sample}")
