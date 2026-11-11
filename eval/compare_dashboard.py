#!/usr/bin/env python3
"""Render the Q1 two-coder study as one self-contained offline HTML dashboard.

Inlines the shared stylesheet (eval/dashboard_assets/dashboard.css), the study's
own markup and renderer (eval/compare_assets/) and the data: comparison.json,
the Claude run manifest, Qwen serving facts, the labelling passes from the run
logs, and the sections where the models differ from each other or from the
final label. Opens anywhere with no server, no CDN, no build step.

    python eval/compare_dashboard.py --out results/q1_panel3k/dashboard.html
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results" / "q1_panel3k"
SHARED_CSS = REPO / "eval" / "dashboard_assets" / "dashboard.css"
ASSETS = REPO / "eval" / "compare_assets"
VLLM_LOG = Path("/groups/brooksgrp/citizen_voice/models/vllm_server.log")


def qwen_meta(log: Path) -> dict:
    out = {}
    if log.exists():
        text = log.read_text(errors="ignore")
        hits = re.findall(r"Prefix cache hit rate: ([0-9.]+)%", text)
        if hits:
            out["prefix_cache_hit_rate_pct"] = hits[-1]
        m = re.search(r"model:\s+(\S+)", text)
        if m:
            out["model"] = Path(m.group(1)).name.replace("__", "/")
    return out


def read_rows(path: Path) -> list[dict]:
    """A results CSV as dicts, with the numeric columns typed (empty -> None)."""
    rows = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            for k in ("Claude confidence", "Qwen confidence", "Qwen P(Yes)", "chars", "Volume"):
                if row.get(k) not in (None, ""):
                    try:
                        row[k] = float(row[k]) if "." in row[k] or "e" in row[k] else int(row[k])
                    except ValueError:
                        pass
                else:
                    row[k] = None
            rows.append(row)
    return rows


DONE_RE = re.compile(r"done in ([0-9.]+)m: (\d+) ok, (\d+) errors -> (\S+)")


def run_passes(results: Path) -> dict:
    """Each labelling pass the runner logged ("done in Xm: a ok, b errors -> file"),
    in order, grouped by the output file it wrote."""
    out: dict = {}
    for log in ("qwen_run.log", "qwen_queue.log", "claude_run.log"):
        p = results / log
        if not p.exists():
            continue
        for m in DONE_RE.finditer(p.read_text(errors="ignore")):
            out.setdefault(Path(m.group(4)).name, []).append(
                {"minutes": float(m.group(1)), "ok": int(m.group(2)), "errors": int(m.group(3))})
    return out


def load_payload(results: Path) -> dict:
    comparison = json.loads((results / "comparison.json").read_text())
    manifest = results / "claude_raw_manifest.json"
    return {
        "comparison": comparison,
        "claude_manifest": json.loads(manifest.read_text()) if manifest.exists() else {},
        "qwen_meta": qwen_meta(VLLM_LOG),
        "runs": run_passes(results),
        "disagreements": read_rows(results / "disagreements.csv"),
        "final_errors": read_rows(results / "final_label_disagreements.csv"),
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# Study-specific additions to the shared stylesheet (same tokens, so both themes follow).
EXTRA_CSS = """
.err .quote { white-space: normal; max-height: 260px; }
.hidden { display: none !important; }
.kv { font-size: 12.5px; line-height: 1.5; }
.kv dt, .kv dd { font-size: 12.5px; }
.kv + .subhead, .kv + .kv { margin-top: 12px; }
.subhead { font-size: 12px; font-weight: 620; color: var(--text-secondary); margin: 4px 0 6px; }
.lede { margin: -6px 0 12px; color: var(--text-secondary); font-size: 12.5px; max-width: 860px; line-height: 1.55; }
.status { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.status .pill { text-transform: none; letter-spacing: 0; font-weight: 560; font-size: 11.5px;
                color: var(--text-secondary); border-color: var(--hairline); display: inline-flex;
                align-items: center; gap: 6px; padding: 3px 9px; }
.status .pill.muted { color: var(--text-muted); }
.findings { display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 12px; }
.finding { background: var(--surface-1); border: 1px solid var(--hairline); border-radius: 12px;
           padding: 14px 16px 12px; font-size: 13px; line-height: 1.55; color: var(--text-secondary); }
.finding h3 { font-size: 14px; font-weight: 630; color: var(--text-primary); margin: 0 0 6px;
              display: flex; gap: 9px; align-items: baseline; }
.finding .num { font-size: 11px; font-weight: 680; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.finding p { margin: 0 0 6px; }
.finding a { font-size: 12px; color: var(--text-secondary); }
.defs { display: flex; flex-direction: column; gap: 9px; }
.defs .def { border-top: 1px solid var(--hairline); padding-top: 8px; font-size: 12.5px; line-height: 1.5;
             color: var(--text-secondary); }
.defs .def:first-child { border-top: 0; padding-top: 0; }
.defs .term { color: var(--text-primary); font-weight: 630; }
.defs .rule { color: var(--text-secondary); }
.defs .calc { display: inline-block; margin: 3px 0; padding: 1px 7px; border-radius: 5px; background: var(--surface-2);
              color: var(--text-primary); font-variant-numeric: tabular-nums; }
.matrix { display: grid; grid-template-columns: minmax(84px, auto) 1fr 1fr minmax(52px, auto); gap: 4px;
          align-items: stretch; max-width: 540px; }
.matrix .mh { font-size: 11.5px; color: var(--text-secondary); text-align: center; padding: 4px 2px; }
.matrix .ml { font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; }
.matrix .mc { border-radius: 6px; padding: 10px 8px; text-align: center; outline-offset: 2px; }
.matrix .mv { font-size: 21px; font-weight: 640; color: var(--text-primary); font-variant-numeric: tabular-nums; }
.matrix .mcap { font-size: 11.5px; font-weight: 620; color: var(--text-primary); }
.matrix .msh { font-size: 11px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.matrix .on-dark .mv, .matrix .on-dark .mcap { color: #fff; }
.matrix .on-dark .msh { color: rgba(255, 255, 255, .85); }
.matrix .mt { font-size: 12.5px; color: var(--text-secondary); display: flex; align-items: center;
              justify-content: center; font-variant-numeric: tabular-nums; }
.tv-wrap { overflow-x: auto; }
.grid2 > .card, .findings > .finding { min-width: 0; }
.caveats { color: var(--text-secondary); font-size: 13px; line-height: 1.6; max-width: 860px; padding-left: 20px; }
@media (max-width: 720px) {
  .viz-root { padding: 20px 16px 48px; }
  .grid2, .findings { grid-template-columns: minmax(0, 1fr); }
  header.page { flex-wrap: wrap; }
  .hero-fig .val { font-size: 40px; }
  .filters input { min-width: 0; width: 100%; }
  .kv { grid-template-columns: 1fr; gap: 0 0; }
  .kv dd { margin-bottom: 6px; }
}
"""


# A claude.ai artifact is wrapped in its own document skeleton and composited over
# the viewer's theme: the colour tokens must also live on :root, the page needs an
# explicit background, and the side gutter clears a phone's safe areas.
ARTIFACT_CSS = """
.viz-root { padding-block: 32px 64px; padding-left: max(28px, env(safe-area-inset-left, 0px));
            padding-right: max(28px, env(safe-area-inset-right, 0px)); }
@media (max-width: 720px) {
  .viz-root { padding-block: 20px 48px; padding-left: max(16px, env(safe-area-inset-left, 0px));
              padding-right: max(16px, env(safe-area-inset-right, 0px)); }
}
"""


def artifact_css(css: str) -> str:
    """The shared stylesheet with its three token blocks also applied to :root."""
    css = css.replace(".viz-root {", ":root, .viz-root {", 1)
    css = css.replace(':root:where(:not([data-theme="light"])) .viz-root {',
                      ':root:not([data-theme="light"]), :root:not([data-theme="light"]) .viz-root {')
    return css.replace(':root[data-theme="dark"] .viz-root {',
                       ':root[data-theme="dark"], :root[data-theme="dark"] .viz-root {')


def render(data: dict, artifact: bool = False) -> str:
    css = SHARED_CSS.read_text(encoding="utf-8")
    body = (ASSETS / "body.html").read_text(encoding="utf-8")
    js = (ASSETS / "compare.js").read_text(encoding="utf-8")
    payload = json.dumps(data, separators=(",", ":"), default=str,
                         allow_nan=False).replace("</", "<\\/")
    if artifact:
        return f"""<title>Q1 two-coder study</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{artifact_css(css)}
{EXTRA_CSS}
{ARTIFACT_CSS}
</style>
{body}
<div id="tip"></div>
<script id="payload" type="application/json">{payload}</script>
<script>
{js}
renderComparison(JSON.parse(document.getElementById("payload").textContent));
</script>
"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Q1 two-coder study</title>
<meta name="description" content="Claude Opus 5.5 and Qwen3.6-27B as two coders of Q1 participation on 3,000 double-coded statute sections: each against the final reconciled label, what each measure means, where the answers go wrong, prompt layout, confidence and reasons.">
<style>
{css}
{EXTRA_CSS}
</style>
</head>
<body data-palette="#2a78d6,#eb6834">
{body}
<div id="tip"></div>
<script id="payload" type="application/json">{payload}</script>
<script>
{js}
renderComparison(JSON.parse(document.getElementById("payload").textContent));
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--artifact", action="store_true",
                    help="write the page body for a claude.ai artifact (no document wrapper)")
    args = ap.parse_args()
    out = args.out or args.results / "dashboard.html"
    out.write_text(render(load_payload(args.results), artifact=args.artifact), encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size/1024:.0f} KB, fully self-contained)")


if __name__ == "__main__":
    main()
