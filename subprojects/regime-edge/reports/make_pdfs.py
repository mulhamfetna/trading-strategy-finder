#!/usr/bin/env python3
"""Render the team-leader reports to PAGELESS PDFs (one continuous page, no page breaks) and bundle them
into a shareable zip. Images are embedded so the PDFs are self-contained.

Run:  python3 make_pdfs.py <out_dir>
"""
import shutil, subprocess, sys, zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
DOCS = ["MEGA_REPORT.md", "LATEST_CANDIDATE_WINNER.md"]
CSS = """
:root{color-scheme:light}
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:900px;margin:0 auto;
 padding:28px 34px;color:#22303c;line-height:1.55;font-size:14px;background:#fff}
h1{font-size:26px;border-bottom:3px solid #4c78a8;padding-bottom:8px;margin-top:0}
h2{font-size:19px;margin-top:26px;border-bottom:1px solid #dde3e9;padding-bottom:5px}
h3{font-size:15.5px;margin-top:18px}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:12.5px}
th,td{border:1px solid #dde3e9;padding:6px 9px;text-align:left}
th{background:#f4f6f8;font-weight:600}
tr:nth-child(even) td{background:#fafbfc}
code{background:#f4f6f8;padding:1px 5px;border-radius:3px;font-size:12px}
img{max-width:100%;height:auto;border:1px solid #e3e8ed;border-radius:6px;margin:10px 0}
blockquote{border-left:4px solid #c77d0a;background:#fdf3e2;margin:12px 0;padding:10px 14px;color:#5b3c05}
hr{border:0;border-top:1px solid #e3e8ed;margin:22px 0}
"""


def to_html(md: Path, css: Path) -> Path:
    out = md.with_suffix(".html")
    for flags in (["--embed-resources", "--standalone"], ["--self-contained"]):
        try:
            subprocess.run(["pandoc", md.name, "-f", "gfm", "-t", "html5", *flags,
                            "-c", css.name, "-o", out.name],
                           cwd=md.parent, check=True, capture_output=True)
            return out
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError(f"pandoc failed for {md}")


def to_pageless_pdf(html: Path, pdf: Path):
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome")      # reuse system Chrome (no browser download)
        except Exception:
            b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 980, "height": 1200})
        pg.goto(html.as_uri(), wait_until="networkidle")
        pg.wait_for_timeout(500)
        h = pg.evaluate("Math.ceil(document.documentElement.scrollHeight)")
        pg.pdf(path=str(pdf), width="980px", height=f"{h + 60}px", print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        b.close()


def main():
    out_dir = Path(sys.argv[1]).expanduser(); out_dir.mkdir(parents=True, exist_ok=True)
    css = HERE / "_report.css"; css.write_text(CSS)
    pdfs = []
    for name in DOCS:
        md = HERE / name
        if not md.exists():
            print(f"  !! missing {name}"); continue
        html = to_html(md, css)
        pdf = out_dir / (md.stem + ".pdf")
        to_pageless_pdf(html, pdf)
        html.unlink(missing_ok=True)
        print(f"  ✓ {pdf.name}  ({pdf.stat().st_size//1024} KB, pageless)")
        pdfs.append(pdf)
    css.unlink(missing_ok=True)
    zpath = out_dir / "regime_research_reports_2026-07-18.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in pdfs:
            z.write(f, f.name)
    print(f"  ✓ {zpath.name}  ({zpath.stat().st_size//1024} KB)")
    print(f"\nOUT_DIR={out_dir}")


if __name__ == "__main__":
    main()
