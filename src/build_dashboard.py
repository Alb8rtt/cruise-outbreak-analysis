"""Assemble cruise_dashboard.html from its parts.

The page is shipped as one self-contained file so it works offline and from a
file:// URL. This script stitches the head, body, the figures from
analysis_results.json, and the chart script into that single file.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(__file__).resolve().parent


def main():
    results = ROOT / "analysis_results.json"
    if not results.exists():
        raise SystemExit("run src/analysis.py first, it writes analysis_results.json")

    data = json.loads(results.read_text())
    blob = "const DATA = " + json.dumps(data, separators=(",", ":")) + ";"

    parts = [
        (SRC / "page_head.html").read_text(),
        (SRC / "page_body.html").read_text(),
        "<script>", blob, "</scr" + "ipt>",
        "<script>", (SRC / "page_script.js").read_text(), "</scr" + "ipt>",
        "</body></html>",
    ]
    out = ROOT / "cruise_dashboard.html"
    html = "\n".join(parts)
    out.write_text(html)
    print(f"wrote {out}  ({len(html):,} bytes, {len(data['scatter'])} scatter points)")


if __name__ == "__main__":
    main()
