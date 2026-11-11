#!/usr/bin/env python3
"""Verify no Q1/Q6 few-shot exemplar comes from the held-out test set.

The per-kit validators in q{1,6}_fewshot/extract_examples.py only guard
HELD_OUT_VOLUME = 95, so they miss whatever the current test set actually is.
This checks every exemplar the prompts really use against the live test split in
data/fewshot_q1q6/, on three independent layers - metadata can be wrong or
missing, so text is the authoritative one:

  A. volume     - exemplar's declared volume is a test volume
  B. unique_key - exemplar's key appears in the test set
  C. text       - exemplar's section text appears in the test set, exact
                  (whitespace-normalized) or as a containment either way.
                  Catches mislabeled volumes, keyless cards (vol 134's
                  "predates unique key?"), and boilerplate recurring across
                  volumes - the vector metadata cannot see.

Exit code 0 = clean, 1 = leakage found. Reads the parquet test set if pandas is
available, else the stdlib-readable CSV, so it runs in this repo's stdlib-only
environment too.

    python verify_no_test_leakage.py [-v]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
DATASET = REPO / "data" / "fewshot_q1q6"
HELDOUT_PARQUET = DATASET / "fewshot_q1q6_heldout.parquet"
HELDOUT_CSV = DATASET / "fewshot_q1q6_heldout.csv"

csv.field_size_limit(10**9)  # statute sections blow past the default limit


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def load_heldout() -> list[dict]:
    """Test-set rows as {Volume, UniqueKey, Text}. Prefers parquet, falls back to CSV."""
    try:
        import pandas as pd

        df = pd.read_parquet(HELDOUT_PARQUET, columns=["Volume", "UniqueKey", "Text"])
        return df.to_dict("records")
    except Exception:
        with open(HELDOUT_CSV, newline="", encoding="utf-8") as fh:
            return [
                {"Volume": r["Volume"], "UniqueKey": r["UniqueKey"], "Text": r["Text"]}
                for r in csv.DictReader(fh)
            ]


def load_excluded() -> dict[str, str]:
    """Test rows the build deliberately dropped, as {unique_key: reason}."""
    path = DATASET / "fewshot_q1q6_excluded_from_test.csv"
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as fh:
        return {
            r["UniqueKey"].strip(): f"deliberately excluded: {r.get('ExcludedBecause','')}"
            for r in csv.DictReader(fh)
        }


def check(verbose: bool = False) -> int:
    held = load_heldout()
    excluded = load_excluded()
    volumes = sorted({int(r["Volume"]) for r in held})
    keys = {str(r["UniqueKey"]).strip() for r in held}
    texts = {norm(r["Text"]) for r in held} - {""}
    # Longest-first so containment reports the most specific match.
    texts_sorted = sorted(texts, key=len, reverse=True)

    print(f"Test set: volumes {volumes}, {len(held)} rows "
          f"({len(keys)} keys, {len(texts)} distinct texts)")
    print(f"Source:   {DATASET}\n")

    total_leaks = 0
    for q in ("q1", "q6"):
        path = REPO / f"{q}_fewshot" / "examples.json"
        if not path.exists():
            print(f"{q.upper()}: {path} missing - SKIPPED\n")
            continue
        examples = json.loads(path.read_text(encoding="utf-8"))
        leaks, notes = [], []
        for ex in examples:
            # HARD = the answer is literally in the test set. Only these fail.
            hard = []
            key = str(ex.get("unique_key", "")).strip()
            if key and key in keys:
                hard.append("unique_key present in test set")
            body = norm(ex.get("section_text"))
            if body:
                if body in texts:
                    hard.append("section_text matches a test row exactly")
                else:
                    for t in texts_sorted:
                        if body in t:
                            hard.append("section_text is contained in a test row")
                            break
                        if t in body:
                            hard.append("section_text contains a whole test row")
                            break
            vol = str(ex.get("volume", "")).strip()
            same_volume = vol.isdigit() and int(vol) in volumes

            if hard:
                leaks.append((ex, hard))
            elif same_volume:
                # Same volume, but this exemplar's own row is not in the test
                # set - it was excluded. Sibling sections of the same volume are
                # unrelated statutes, so this is advisory, not a leak.
                notes.append((ex, excluded.get(key, "row not present in test set")))
            elif verbose:
                print(f"  ok   {ex.get('id'):<18} vol={vol:<5} {ex.get('label')}")

        if leaks:
            total_leaks += len(leaks)
            print(f"{q.upper()}: LEAK - {len(leaks)} of {len(examples)} exemplars are in the test set")
            for ex, hits in leaks:
                print(f"  !! {ex.get('id')}  (vol {ex.get('volume')}, {ex.get('label')})")
                print(f"     key: {ex.get('unique_key')}")
                for h in hits:
                    print(f"     - {h}")
                print(f"     text: {norm(ex.get('section_text'))[:110]}...")
        else:
            print(f"{q.upper()}: CLEAN - 0 of {len(examples)} exemplars are in the test set")
        for ex, why in notes:
            print(f"  note  {ex.get('id')} is from test volume {ex.get('volume')}, "
                  f"but its row is not in the test set ({why})")
        print()

    if total_leaks:
        print(f"RESULT: {total_leaks} leaking exemplar(s). Either drop the colliding test "
              f"row(s) (rebuild the dataset) or replace the exemplar (SME-authored).")
        return 1
    print("RESULT: clean - no exemplar in either prompt appears in the test set.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true", help="also list clean exemplars")
    sys.exit(check(ap.parse_args().verbose))
