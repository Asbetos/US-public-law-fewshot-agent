#!/usr/bin/env python3
"""Cache the true token length of every held-out section.

Section length in *characters* is a poor proxy for cost: statute text ranges
from ~1.1 to ~4.9 chars/token in this corpus (tables of figures and citations
versus prose), so a chars-based bucket mixes cheap and expensive rows. This
tokenises each section once with the served model's own tokenizer and caches the
result, so the cost charts can bucket on what the model actually processes.

Run with the serving venv (it has transformers); no GPU and no server needed:

    .venv-vllm/bin/python eval/tokenize_sections.py
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
csv.field_size_limit(10**9)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", default="/groups/brooksgrp/citizen_voice/models/"
                                           "cyankiwi__Qwen3.6-27B-AWQ-INT4")
    ap.add_argument("--out", type=Path, default=REPO / "results" / "section_tokens.json")
    args = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model_dir)

    src = REPO / "data" / "fewshot_q1q6" / "fewshot_q1q6_heldout.csv"
    with open(src, encoding="utf-8") as fh:
        rows = [(r["UniqueKey"], r["Text"]) for r in csv.DictReader(fh)]

    out = {}
    for i, (key, text) in enumerate(rows, 1):
        out[key] = len(tok(text)["input_ids"])
        if i % 400 == 0:
            print(f"  {i}/{len(rows)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out))
    vals = sorted(out.values())
    pct = lambda p: vals[int(p * (len(vals) - 1))]
    print(f"wrote {args.out}  ({len(out)} sections)")
    print(f"  section tokens: min {vals[0]}  p50 {pct(.5)}  p90 {pct(.9)}  "
          f"p99 {pct(.99)}  max {vals[-1]}")


if __name__ == "__main__":
    main()
