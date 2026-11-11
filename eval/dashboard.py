#!/usr/bin/env python3
"""Render the results as one self-contained offline HTML dashboard.

The markup, styles and chart code live in eval/dashboard_assets/ and are shared
verbatim with the local Next.js viewer in dashboard-app/ - this script inlines
them into a single file that opens on an air-gapped machine with no server, no
CDN and no build step. Edit the assets, never a copy, so the two cannot drift.

    python eval/dashboard.py --out results/dashboard.html
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent / "dashboard_assets"


def load_payload(metrics: Path) -> dict:
    """metrics.json plus its sibling artefacts, as one object.

    The app's /api/data route builds the identical structure, so the renderer
    sees the same shape whichever way it is fed.
    """
    data = json.loads(metrics.read_text())
    here = metrics.parent

    infra = here / "infra.json"
    data["infra"] = json.loads(infra.read_text()) if infra.exists() else None

    data["thinking_ab"] = {
        f.stem.replace("thinking_ab_", ""): json.loads(f.read_text())
        for f in sorted(here.glob("thinking_ab_*.json"))
    }

    run = data.setdefault("run", {})
    meta = here / "run_meta.json"
    if meta.exists():
        run.update(json.loads(meta.read_text()))
    run.setdefault("model_short", "Qwen3.6-27B AWQ-4bit")
    run.setdefault("display", [])
    return data


def render(data: dict) -> str:
    body = (ASSETS / "body.html").read_text(encoding="utf-8")
    css = (ASSETS / "dashboard.css").read_text(encoding="utf-8")
    js = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    payload = json.dumps(data, separators=(",", ":"), default=str).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Few-shot labelling dashboard</title>
<style>
{css}
</style>
</head>
<body data-palette="#2a78d6,#eb6834">
{body}
<div id="tip"></div>
<script id="payload" type="application/json">{payload}</script>
<script>
{js}
renderDashboard(JSON.parse(document.getElementById("payload").textContent));
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metrics", type=Path, default=REPO / "results" / "metrics.json")
    ap.add_argument("--out", type=Path, default=REPO / "results" / "dashboard.html")
    args = ap.parse_args()

    html = render(load_payload(args.metrics))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"wrote {args.out}  ({args.out.stat().st_size/1024:.0f} KB, fully self-contained)")


if __name__ == "__main__":
    main()
