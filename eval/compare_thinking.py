#!/usr/bin/env python3
"""A/B the model's reasoning mode on the calibration slice.

Thinking mode was off for the main run: the few-shot prompt already asks for an
explicit Temptation/Resolution before the JSON, and native reasoning multiplies
output tokens (and so wall-clock) several-fold. This measures what that cost
would have bought, on identical rows.

The thinking-OFF side is read out of the main run rather than re-labelled -
the calibration ids are a subset of the test ids, so the answers already exist.

    python eval/compare_thinking.py --question q6
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(REPO / "eval"))
import score  # noqa: E402


def load(path: Path) -> pd.DataFrame:
    """Tolerant of a half-written final line: the runner may still be appending."""
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset="id", keep="last") if len(df) else df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--question", default="q6")
    ap.add_argument("--results-dir", type=Path, default=REPO / "results")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    q = args.question
    qdir = args.results_dir / q
    think = load(qdir / "calibration_think.jsonl")
    if think.empty:
        print(f"no thinking run at {qdir/'calibration_think.jsonl'} - skipping")
        return
    main_run = load(qdir / "raw.jsonl")
    if main_run.empty:
        print(f"no main run at {qdir/'raw.jsonl'} - skipping")
        return

    heldout = pd.read_parquet(REPO / "data" / "fewshot_q1q6" / "fewshot_q1q6_heldout.parquet")
    gold = dict(zip(heldout.UniqueKey.astype(str), heldout[q.upper()].map(score.norm)))

    ids = [i for i in think.id if i in set(main_run.id)]
    nothink = main_run[main_run.id.isin(ids)].set_index("id")
    think = think[think.id.isin(ids)].set_index("id")

    out = {"question": q, "rows": len(ids), "arms": {}}
    for name, df in (("thinking_off", nothink), ("thinking_on", think)):
        lab = df.get("label", pd.Series(dtype=object)).reindex(ids)
        keep = [i for i in ids if lab.get(i) in ("Yes", "No")]
        g = np.array([gold[i] for i in keep])
        p = np.array([lab[i] for i in keep])
        m = score.metrics_from_counts(score.counts(g, p))
        ct = df.get("completion_tokens", pd.Series(dtype=float)).reindex(ids)
        el = df.get("elapsed_s", pd.Series(dtype=float)).reindex(ids)
        out["arms"][name] = {
            **m,
            "parsed": len(keep), "of": len(ids),
            "mean_completion_tokens": float(ct.dropna().mean()) if ct.notna().any() else None,
            "median_latency_s": float(el.dropna().median()) if el.notna().any() else None,
        }

    a, b = out["arms"]["thinking_off"], out["arms"]["thinking_on"]
    out["delta"] = {
        "f1_yes": b["f1_yes"] - a["f1_yes"],
        "mcc": b["mcc"] - a["mcc"],
        "token_multiplier": ((b["mean_completion_tokens"] / a["mean_completion_tokens"])
                             if a["mean_completion_tokens"] else None),
    }
    dest = args.out or (args.results_dir / f"thinking_ab_{q}.json")
    dest.write_text(json.dumps(out, indent=2))

    print(f"\nThinking A/B on {q.upper()}, {out['rows']} identical rows")
    print(f"{'':<14}{'F1(Yes)':>9}{'MCC':>8}{'recall':>8}{'prec':>8}{'tokens':>9}{'sec':>7}")
    for name in ("thinking_off", "thinking_on"):
        m = out["arms"][name]
        print(f"{name:<14}{m['f1_yes']:>9.3f}{m['mcc']:>8.3f}{m['recall_yes']:>8.3f}"
              f"{m['precision_yes']:>8.3f}{(m['mean_completion_tokens'] or 0):>9.0f}"
              f"{(m['median_latency_s'] or 0):>7.1f}")
    d = out["delta"]
    print(f"{'delta':<14}{d['f1_yes']:>+9.3f}{d['mcc']:>+8.3f}"
          f"{'':>16}{(d['token_multiplier'] or 0):>8.1f}x")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
