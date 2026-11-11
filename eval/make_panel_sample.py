#!/usr/bin/env python3
"""Draw the Q1 sample for the Claude-vs-Qwen two-coder study.

Frame: every panel section with >= 2 first-pass Q1 labels, joined to its text
on (Volume, OrderCoded) exactly as setfit-classifier's parity scripts do, minus
the test volumes, the defect/quarantined volumes, empty or placeholder texts,
and every section the 24 few-shot exemplars were drawn from (matched by the
exemplar's UniqueKey, by whitespace-normalised text, and by containment for the
exemplars that are a long sub-span of a section). A seeded simple random draw
of N sections, clipped once at the batch runner's section limit so both coders
see identical input.

Two files, kept apart on purpose: sample.jsonl holds only what the models see
({"id", "text"}); sample_meta.parquet holds the coder labels, provenance and a
hash of the clipped text that the runners echo back, so a result row can always
be tied to the exact text it was labelled on.

    python eval/make_panel_sample.py            # 3,000 rows, seed 20261103
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "eval"))
from run_batch import MAX_SECTION_CHARS, text_hash  # noqa: E402  - one clipping rule, one hash

WORKSPACE = Path("/groups/brooksgrp/citizen_voice/workspace")
PANEL = WORKSPACE / "setfit-classifier/results/panel/firstpass_panel.parquet"
TRAINING = WORKSPACE / "training-dataset/training-set/output/final/training_dataset.parquet"
EXEMPLARS = [REPO / "q1_fewshot/examples.json", REPO / "q6_fewshot/examples.json"]
OUT_DIR = REPO / "results" / "q1_panel3k"

TEST_VOLUMES = (62, 91, 132)
# 95: held-out exam volume; 134: (Volume, OrderCoded) not unique across its two
# batches; 53/66/71: fresh volumes quarantined for the Q1 plan's final check.
EXCLUDE_VOLUMES = (95, 134, 53, 66, 71)
PLACEHOLDER_TEXTS = {"", "(blank)", "blank", "none", "n/a", "na"}
CONTAINMENT_MIN_CHARS = 200   # an exemplar this long found inside a section is that section
SEED = 20261103
N_ROWS = 3000


def normalise(text: str) -> str:
    """Whitespace-collapsed, quote-stripped text: the extractor collapsed runs of
    whitespace and sometimes kept a leading curly quote, so exact matching misses."""
    t = re.sub(r"\s+", " ", text or "").strip()
    return t.strip("\"“”'‘’ ").strip()


def exemplar_index(paths=EXEMPLARS) -> tuple[set[str], list[str]]:
    """(UniqueKeys, normalised texts) of every few-shot exemplar."""
    keys, texts = set(), []
    for p in paths:
        for e in json.loads(Path(p).read_text()):
            keys.add(str(e.get("unique_key", "")))
            texts.append(normalise(e["section_text"]))
    return keys, texts


def build_frame(panel: pd.DataFrame, td: pd.DataFrame, exemplars: tuple[set[str], list[str]],
                exclude=TEST_VOLUMES + EXCLUDE_VOLUMES, log=print) -> pd.DataFrame:
    """One row per eligible section: id (UniqueKey), text, provenance, coder labels."""
    ex_keys, ex_texts = exemplars
    p = panel[panel["Q1"].isin(["yes", "no"])].copy()
    p["volume"] = p["volume"].astype(int)
    p["order"] = p["order"].astype(int)
    units = (p.sort_values(["volume", "order", "coder"])
              .groupby(["volume", "order"])
              .agg(coders=("coder", list), labels=("Q1", list))
              .reset_index())
    units = units[units["coders"].str.len() >= 2]
    log(f"panel sections with >=2 Q1 labels: {len(units):,}")

    units = units[~units["volume"].isin(list(exclude))]
    log(f"after excluding volumes {sorted(exclude)}: {len(units):,}")

    t = td.copy()
    t["volume"] = t["Volume"].astype(int)
    t["order"] = pd.to_numeric(t["OrderCoded"], errors="coerce")
    t = (t.dropna(subset=["order"]).assign(order=lambda d: d["order"].astype(int))
          .drop_duplicates(["volume", "order"])
          [["volume", "order", "UniqueKey", "LawIdentifier", "Text"]])
    frame = units.merge(t, on=["volume", "order"], how="left")
    missing = int(frame["Text"].isna().sum())
    frame = frame[frame["Text"].notna()]
    log(f"text matched on (Volume, OrderCoded): {len(frame):,} ({missing} without a match dropped)")

    norm = frame["Text"].map(normalise)
    placeholder = norm.str.lower().isin(PLACEHOLDER_TEXTS)
    frame, norm = frame[~placeholder], norm[~placeholder]
    log(f"after dropping {int(placeholder.sum())} empty/placeholder texts: {len(frame):,}")

    by_key = frame["UniqueKey"].astype(str).isin(ex_keys)
    by_text = norm.isin(set(ex_texts))
    long_ex = [x for x in ex_texts if len(x) >= CONTAINMENT_MIN_CHARS]
    by_contain = norm.map(lambda s: any(x in s for x in long_ex))
    is_exemplar = by_key | by_text | by_contain
    frame = frame[~is_exemplar]
    log(f"after dropping {int(is_exemplar.sum())} exemplar sections "
        f"(by key {int(by_key.sum())}, by text {int(by_text.sum())}, by containment {int(by_contain.sum())}): "
        f"{len(frame):,}")

    frame = frame.rename(columns={"UniqueKey": "id", "LawIdentifier": "law", "Text": "text"})
    frame["coder_labels"] = frame["labels"].map(lambda ls: ["Yes" if l == "yes" else "No" for l in ls])
    frame["n_coders"] = frame["coders"].str.len()
    frame["n_yes"] = frame["coder_labels"].map(lambda ls: sum(l == "Yes" for l in ls))
    frame["any_yes"] = frame["n_yes"] > 0
    frame["unanimous_yes"] = frame["n_yes"] == frame["n_coders"]
    frame["chars"] = frame["text"].str.len()
    frame = frame.drop(columns=["labels"]).sort_values(["volume", "order"]).reset_index(drop=True)
    if frame["id"].duplicated().any():
        raise SystemExit("UniqueKey is not unique in the frame; refusing to continue")
    log(f"FRAME: {len(frame):,} sections, {frame['volume'].nunique()} volumes, "
        f"{frame['law'].nunique():,} laws, {int(frame['any_yes'].sum())} any-coder-Yes "
        f"({frame['any_yes'].mean():.1%}), {int(frame['unanimous_yes'].sum())} unanimous-Yes")
    return frame


def draw(frame: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Simple random sample without replacement, reproducible from the seed."""
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(len(frame), size=min(n, len(frame)), replace=False))
    return frame.iloc[idx].reset_index(drop=True)


def clip(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars and len(text) > max_chars:
        return text[:max_chars], True
    return text, False


def write_outputs(sample: pd.DataFrame, out_dir: Path, max_chars: int, log=print) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    clipped = sample["text"].map(lambda t: clip(t, max_chars))
    sample = sample.assign(text_model=clipped.str[0], section_clipped=clipped.str[1])
    sample["text_sha256"] = sample["text_model"].map(text_hash)
    with open(out_dir / "sample.jsonl", "w", encoding="utf-8") as fh:
        for row in sample.itertuples():
            fh.write(json.dumps({"id": row.id, "text": row.text_model}, ensure_ascii=False) + "\n")
    meta_cols = ["id", "volume", "order", "law", "chars", "section_clipped", "text_sha256", "n_coders",
                 "coders", "coder_labels", "n_yes", "any_yes", "unanimous_yes"]
    sample[meta_cols].to_parquet(out_dir / "sample_meta.parquet", index=False)
    log(f"SAMPLE: {len(sample):,} rows -> {out_dir / 'sample.jsonl'} + sample_meta.parquet; "
        f"{int(sample['section_clipped'].sum())} clipped at {max_chars:,} chars; "
        f"{int(sample['any_yes'].sum())} any-coder-Yes, {int(sample['unanimous_yes'].sum())} unanimous-Yes")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=N_ROWS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--max-section-chars", type=int, default=MAX_SECTION_CHARS)
    ap.add_argument("--panel", type=Path, default=PANEL)
    ap.add_argument("--training", type=Path, default=TRAINING)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--overwrite", action="store_true",
                    help="replace an existing sample (any results already labelled on it become unusable)")
    args = ap.parse_args()
    if (args.out_dir / "sample.jsonl").exists() and not args.overwrite:
        raise SystemExit(f"{args.out_dir / 'sample.jsonl'} exists; pass --overwrite to redraw "
                         "(results labelled on the old sample would no longer match)")

    panel = pd.read_parquet(args.panel)
    td = pd.read_parquet(args.training, columns=["Volume", "OrderCoded", "UniqueKey",
                                                 "LawIdentifier", "Text"])
    frame = build_frame(panel, td, exemplar_index())
    sample = draw(frame, args.n, args.seed)
    write_outputs(sample, args.out_dir, args.max_section_chars)
    # the reference label: the final reconciled answer, read from the latest workbooks
    import final_labels
    final_labels.annotate_results(args.out_dir)


if __name__ == "__main__":
    main()
