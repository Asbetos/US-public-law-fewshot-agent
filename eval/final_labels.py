#!/usr/bin/env python3
"""Attach the FINAL reconciled Q1 label to the two-coder study sample.

The team's definition (2026-11-10): a section is Q1 = Yes when every coder's
answer in the final workbook - the latest export of the volume's coding check,
after the coders have reconciled - is Yes, and No when every coder's answer is
No. A section whose coders still disagree in the final workbook counts as Yes
(the team's call: the final sheet should carry one label, so a split there is a
reconciliation slip); it is flagged "disputed". A section with a single coder's
answer takes that answer, flagged "single coder".

The answers come from the coder sheets of the latest workbook per volume (the
training-dataset build's `pick_latest`; the `agreement NNN` sheets carry only
agree/disagree flags, not answers). These are NOT the labels in
training_dataset.parquet, which keeps one coder's answer per section from the
workbooks current on 2026-08-04, nor the first-pass panel's labels, which are
each coder's independent answer before reconciliation.

Adds to sample_meta.parquet: final_q1 (Yes/No), final_q1_status (agreed /
disputed / single coder / missing), final_n_coders, final_answers ("yes|no").
Writes final_labels_sources.json (the workbook used per volume and the counts).

    python eval/final_labels.py           # annotate results/q1_panel3k/sample_meta.parquet
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = Path("/groups/brooksgrp/citizen_voice/workspace")
sys.path.insert(0, str(WORKSPACE / "training-dataset" / "scripts"))
sys.path.insert(0, str(WORKSPACE / "setfit-classifier" / "scripts"))
import steps123_stack_and_hash as S  # noqa: E402  pick_latest, CODED_DIR
import build_firstpass_panel as B  # noqa: E402  load_coder_sheets_relaxed, norm

RESULTS = REPO / "results" / "q1_panel3k"
FINAL_COLS = ["final_q1", "final_q1_status", "final_n_coders", "final_answers"]


def final_label(answers: list[str]) -> tuple[str | None, str]:
    """(label, status) for one section from its coders' final answers ("yes"/"no")."""
    if not answers:
        return None, "missing"
    if len(answers) == 1:
        return ("Yes" if answers[0] == "yes" else "No"), "single coder"
    kinds = set(answers)
    if kinds == {"yes"}:
        return "Yes", "agreed"
    if kinds == {"no"}:
        return "No", "agreed"
    return "Yes", "disputed"          # the team's rule for a split left in the final sheet


def final_answers(volumes, log=print) -> tuple[pd.DataFrame, dict[int, str]]:
    """One row per (volume, order, coder) with that coder's Q1 answer in the
    volume's latest workbook; plus the workbook name used per volume."""
    rows, files, other = [], {}, 0
    for vol in sorted({int(v) for v in volumes}):
        path = S.pick_latest(glob.glob(os.path.join(S.CODED_DIR, f"*Volume_{vol}_*.xlsx")))
        if path is None:
            raise SystemExit(f"no coded workbook for volume {vol}")
        files[vol] = os.path.basename(path)
        for coder, df in B.load_coder_sheets_relaxed(path).items():
            if "Q1" not in df.columns:
                continue
            d = df[df["OrderN"].notna()]
            for order, q1 in zip(d["OrderN"].astype(int), d["Q1"]):
                v = B.norm(q1)
                if v in ("yes", "no"):
                    rows.append((vol, int(order), coder, v))
                elif v and v != "(blank)":
                    other += 1
    if other:
        log(f"  note: {other} final-sheet Q1 answers were neither yes nor no and were ignored")
    ans = (pd.DataFrame(rows, columns=["volume", "order", "coder", "q1"])
             .drop_duplicates(["volume", "order", "coder"], keep="last"))
    return ans, files


def annotate(meta: pd.DataFrame, answers: pd.DataFrame) -> pd.DataFrame:
    """meta + the final-label columns, matched on (volume, order)."""
    grouped = (answers.sort_values("coder").groupby(["volume", "order"])["q1"]
                      .apply(list).rename("answers").reset_index())
    out = meta.drop(columns=[c for c in FINAL_COLS if c in meta.columns])
    out = out.merge(grouped, on=["volume", "order"], how="left")
    out["answers"] = out["answers"].map(lambda a: a if isinstance(a, list) else [])
    labels = out["answers"].map(final_label)
    out["final_q1"] = labels.str[0]
    out["final_q1_status"] = labels.str[1]
    out["final_n_coders"] = out["answers"].str.len().astype(int)
    out["final_answers"] = out["answers"].map("|".join)
    return out.drop(columns=["answers"])


def summary(meta: pd.DataFrame) -> dict:
    return {
        "n": int(len(meta)),
        "final_yes": int((meta["final_q1"] == "Yes").sum()),
        "final_no": int((meta["final_q1"] == "No").sum()),
        "status": meta["final_q1_status"].value_counts().to_dict(),
        "coders_per_section": {int(k): int(v) for k, v in
                               meta["final_n_coders"].value_counts().sort_index().items()},
        "disputed_sections": meta.loc[meta["final_q1_status"] == "disputed",
                                      ["volume", "order", "final_answers"]].to_dict("records"),
    }


def annotate_results(results: Path, log=print) -> dict:
    """Annotate results/<study>/sample_meta.parquet in place; returns the summary."""
    path = results / "sample_meta.parquet"
    meta = pd.read_parquet(path)
    answers, files = final_answers(meta["volume"].unique(), log=log)
    meta = annotate(meta, answers)
    meta.to_parquet(path, index=False)
    info = summary(meta)
    info["workbooks"] = {str(k): v for k, v in files.items()}
    (results / "final_labels_sources.json").write_text(json.dumps(info, indent=1, default=int))
    log(f"final labels: {info['final_yes']} Yes, {info['final_no']} No of {info['n']}; "
        f"status {info['status']}; coders per section {info['coders_per_section']}")
    return info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=RESULTS)
    args = ap.parse_args()
    annotate_results(args.results)
    print(f"wrote {args.results / 'sample_meta.parquet'} and final_labels_sources.json")


if __name__ == "__main__":
    main()
