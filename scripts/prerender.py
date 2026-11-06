#!/usr/bin/env python3
"""Bake the rendered English page into index.html so crawlers and link previews see real content.

Loads the site in headless Chrome (fresh profile, so English), copies the rendered <section>
elements, and writes them between the prerender markers inside <main>. The JavaScript still
re-renders everything on load, so Spanish and French visitors are unaffected.

    python3 scripts/prerender.py

Needs Google Chrome (macOS path below, or set CHROME). Run it after editing the text in `T`,
then commit index.html.
"""

import http.server
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
START, END = "<!-- prerender:start -->", "<!-- prerender:end -->"


def render_html() -> str:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *args: None
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as profile:
            result = subprocess.run(
                [CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={profile}",
                 "--lang=en-US", "--virtual-time-budget=5000", "--dump-dom", f"http://127.0.0.1:{port}/"],
                capture_output=True, text=True, timeout=120)
        server.shutdown()
    return result.stdout


def clean(sections: str) -> str:
    sections = re.sub(r' data-watch=""', "", sections)
    sections = re.sub(r'class="([^"]*)"', lambda m: 'class="%s"' % " ".join(c for c in m.group(1).split() if c != "in"), sections)
    return sections


def main():
    dom = render_html()
    main_html = re.search(r"<main[^>]*>(.*)</main>", dom, re.S)
    if not main_html:
        sys.exit("Chrome returned no <main>; is the path to Chrome right?")
    sections = "".join(re.findall(r"<section\b.*?</section>", main_html.group(1), re.S))
    if "Senior Data Engineer" not in sections or 'id="projects-grid"' not in sections:
        sys.exit("Rendered page looks incomplete; not writing index.html")

    path = ROOT / "index.html"
    source = path.read_text(encoding="utf-8")
    block = START + "\n" + clean(sections) + "\n    " + END
    if START in source:
        source = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, source, flags=re.S)
    else:
        existing = re.search(r"(    <section id=\"top\".*</section>\n)(?=  </main>)", source, re.S)
        if not existing:
            sys.exit("Could not find the sections to wrap")
        source = source.replace(existing.group(1), "    " + block + "\n")
    path.write_text(source, encoding="utf-8")
    print(f"index.html: {len(sections)} characters of pre-rendered sections")


if __name__ == "__main__":
    main()
