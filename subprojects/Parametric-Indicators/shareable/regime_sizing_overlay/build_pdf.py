#!/usr/bin/env python3
"""Render WINNER_PLAYBOOK.md -> pageless PDF (Mermaid rendered, images embedded) + zip the bundle."""
import re, shutil, subprocess, sys, zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
MD = HERE / "WINNER_PLAYBOOK.md"
PDF = HERE / "WINNER_PLAYBOOK.pdf"
MERMAID = Path("/tmp/mermaid.min.js")
CSS = """body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:940px;margin:0 auto;
padding:30px 36px;color:#22303c;line-height:1.55;font-size:13.6px;background:#fff}
h1{font-size:26px;border-bottom:3px solid #4c78a8;padding-bottom:8px;margin-top:0}
h2{font-size:19px;margin-top:26px;border-bottom:1px solid #dde3e9;padding-bottom:5px}
h3{font-size:15px;margin-top:16px}
table{border-collapse:collapse;width:100%;margin:11px 0;font-size:12.3px}
th,td{border:1px solid #dde3e9;padding:6px 9px;text-align:left}
th{background:#f4f6f8;font-weight:600} tr:nth-child(even) td{background:#fafbfc}
code{background:#f4f6f8;padding:1px 5px;border-radius:3px;font-size:12px}
pre{background:#f7f9fa;border:1px solid #e3e8ed;border-radius:6px;padding:10px;overflow-x:auto;font-size:11.5px}
pre.mermaid{background:#fff;border:0;text-align:center}
img{max-width:100%;height:auto;border:1px solid #e3e8ed;border-radius:6px;margin:10px 0}
blockquote{border-left:4px solid #c77d0a;background:#fdf3e2;margin:14px 0;padding:12px 16px;color:#5b3c05}
hr{border:0;border-top:1px solid #e3e8ed;margin:22px 0}"""

def main():
    css = HERE / "_pb.css"; css.write_text(CSS)
    html = HERE / "_pb.html"
    for flags in (["--embed-resources","--standalone"], ["--self-contained"]):
        try:
            subprocess.run(["pandoc", MD.name, "-f","gfm","-t","html5",*flags,"-c",css.name,"-o",html.name],
                           cwd=HERE, check=True, capture_output=True); break
        except subprocess.CalledProcessError: continue
    t = html.read_text()
    # pandoc renders ```mermaid as <pre class="mermaid"><code>...</code></pre> (or sourceCode) -> unwrap for mermaid.js
    t = re.sub(r'<pre class="[^"]*mermaid[^"]*"><code[^>]*>(.*?)</code></pre>',
               lambda m: '<pre class="mermaid">' + re.sub(r'<[^>]+>','',m.group(1)).replace('&gt;','>').replace('&lt;','<').replace('&amp;','&') + '</pre>',
               t, flags=re.S)
    if MERMAID.exists():
        t = t.replace("</body>", f"<script>{MERMAID.read_text()}</script>"
                      "<script>mermaid.initialize({startOnLoad:true,theme:'neutral'});</script></body>")
    html.write_text(t)
    with sync_playwright() as p:
        try: b = p.chromium.launch(channel="chrome")
        except Exception: b = p.chromium.launch()
        pg = b.new_page(viewport={"width":1000,"height":1200})
        pg.goto(html.as_uri(), wait_until="networkidle"); pg.wait_for_timeout(2500)
        h = pg.evaluate("Math.ceil(document.documentElement.scrollHeight)")
        pg.pdf(path=str(PDF), width="1000px", height=f"{h+60}px", print_background=True,
               margin={"top":"0","bottom":"0","left":"0","right":"0"})
        b.close()
    html.unlink(missing_ok=True); css.unlink(missing_ok=True)
    print(f"  ✓ {PDF.name} ({PDF.stat().st_size//1024} KB, pageless)")
    z = HERE.parent / "regime_sizing_overlay_bundle.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(HERE.rglob("*")):
            if f.is_file() and f.name not in ("build_pdf.py",) and "__pycache__" not in str(f):
                zf.write(f, f"regime_sizing_overlay/{f.relative_to(HERE)}")
    print(f"  ✓ {z.name} ({z.stat().st_size//1024} KB)")
    print(f"ZIP={z}")

main()
