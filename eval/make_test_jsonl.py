#!/usr/bin/env python3
"""Held-out test set -> the {"id", "text"} JSONL contract run_model.py defines.

Writes one file per question plus a calibration subsample used to measure
throughput (and to A/B thinking mode) before committing to the full run.

    python eval/make_test_jsonl.py --out-dir results
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATASET = REPO / "data" / "fewshot_q1q6"

csv.field_size_limit(10**9)  # statute sections blow past the default limit


def load_heldout() -> list[dict]:
    """Test rows, preferring parquet but falling back to the stdlib-readable CSV."""
    try:
        import pandas as pd

        return pd.read_parquet(DATASET / "fewshot_q1q6_heldout.parquet").to_dict("records")
    except Exception:
        with open(DATASET / "fewshot_q1q6_heldout.csv", newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))


def calibration_ids(rows: list[dict], question: str, n: int) -> set[str]:
    """A stratified slice: every positive is scarce, so take them proportionally.

    Deterministic - strided over the label-sorted rows, no RNG - so a repeat run
    scores the same subset and thinking-on/off stay directly comparable.
    """
    label = question.upper()
    yes = [r for r in rows if str(r.get(label, "")).strip() == "Yes"]
    no = [r for r in rows if str(r.get(label, "")).strip() == "No"]
    want_yes = max(1, round(n * len(yes) / max(1, len(yes) + len(no))))
    want_no = n - want_yes

    def stride(pool, k):
        if k >= len(pool):
            return pool
        step = len(pool) / k
        return [pool[int(i * step)] for i in range(k)]

    return {str(r["UniqueKey"]) for r in stride(yes, want_yes) + stride(no, want_no)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=REPO / "results")
    ap.add_argument("--calibration-n", type=int, default=150,
                    help="rows in the calibration subsample (default: %(default)s)")
    args = ap.parse_args()

    rows = load_heldout()
    print(f"loaded {len(rows)} held-out rows from {DATASET}")

    for question in ("q1", "q6"):
        qdir = args.out_dir / question
        qdir.mkdir(parents=True, exist_ok=True)
        calib = calibration_ids(rows, question, args.calibration_n)

        for name, keep in (("test", None), ("calibration", calib)):
            path = qdir / f"{name}.jsonl"
            n = 0
            with open(path, "w", encoding="utf-8") as out:
                for r in rows:
                    key = str(r["UniqueKey"])
                    if keep is not None and key not in keep:
                        continue
                    out.write(json.dumps({"id": key, "text": str(r["Text"])},
                                         ensure_ascii=False) + "\n")
                    n += 1
            gold = [str(r[question.upper()]).strip() for r in rows
                    if keep is None or str(r["UniqueKey"]) in keep]
            yes = sum(g == "Yes" for g in gold)
            print(f"  {path.relative_to(REPO)}: {n} rows ({yes} Yes, {n - yes} No)")


if __name__ == "__main__":
    main()
