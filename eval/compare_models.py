#!/usr/bin/env python3
"""Compare the two model coders (Claude, Qwen) with each other and with the human
labels on the Q1 panel sample, and write the study's deliverables.

The reference label is the FINAL reconciled label (eval/final_labels.py: Yes when
every coder's answer in the final workbook is Yes; the few sections still split
there count as Yes and are flagged). The coders' first answers, before
reconciliation, are used only in a separate secondary section (each model in a
coder's seat, scored against the other coder); the two are never mixed.

Reads results/q1_panel3k/{sample_meta.parquet, claude_raw.jsonl, qwen_raw.jsonl}
(plus claude_repeat.jsonl and qwen_flat300.jsonl when present) and writes, in the
same directory:
  comparison.json        every number in the report, with bootstrap intervals
  q1_two_coder_sheet.csv (+ .xlsx) one row per section, the models as coders
  disagreements.csv      sections where the two models differ, both reasonings
  final_label_disagreements.csv  sections where a model differs from the final
                         label or gave no answer, with its reasoning
  <model>_output.jsonl   each model's answer per sampled section (latest attempt)
  REPORT.md              the tables, in prose order

Each model is analysed as soon as its own run exists; the model-vs-model parts
fill in once both have run.

Agreement statistics reuse setfit-classifier's parity code (`_stats`, the
coder-replacement `endpoint_a`), so kappa/AC1 here are computed exactly as in
the project's other reports. Intervals are law-clustered bootstraps stratified
by volume (laws are the unit of correlated coding).

    python eval/compare_models.py                      # defaults
    python eval/compare_models.py --n-boot 200         # quick look
"""
from __future__ import annotations

import argparse
import collections
import importlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results" / "q1_panel3k"
PARITY_SCRIPTS = Path("/groups/brooksgrp/citizen_voice/workspace/setfit-classifier/scripts")
sys.path.insert(0, str(PARITY_SCRIPTS))
sys.path.insert(0, str(REPO))
parity = importlib.import_module("parity_full_panel")   # _stats, endpoint_a
from run_model import parse_reply  # noqa: E402  - the runners' parser, one behaviour

CLAUDE, QWEN = "claude", "qwen"
ARMS = {CLAUDE: "claude_raw.jsonl", QWEN: "qwen_raw.jsonl"}
# Bins that keep apart the values models actually state (Qwen: 0.7/0.8/0.9/0.95/1.0)
CONF_BINS = [0.0, 0.7, 0.8, 0.9, 0.95, 1.0, 1.0000001]
CONF_BIN_LABELS = ["below 0.70", "0.70-0.79", "0.80-0.89", "0.90-0.94", "0.95-0.99", "1.00"]
TRIAGE_CUTS = (1.0, 0.95, 0.9)          # "send for review everything stated below this"
P_YES_BANDS = [0.0, 0.001, 0.01, 0.1, 0.5, 0.9, 0.99, 1.0000001]
P_YES_BAND_LABELS = ["below 0.001", "0.001-0.01", "0.01-0.1", "0.1-0.5", "0.5-0.9", "0.9-0.99",
                     "0.99 and above"]
# Words that name a participation mechanism in the definition; a crude flag for
# "the passage the model quoted mentions one", not a classifier.
TRIGGER_RE = re.compile(r"consult|comment|hearing|cooperat|coordinat|concur|rulemaking|section 553",
                        re.IGNORECASE)
# Runner errors that only mean "the parser could not read the reply"; such rows
# are re-read from the saved reply (fail-closed errors are never re-read).
PARSE_ERRORS = ("no valid ```json answer block in reply",
                "no structured output and no valid ```json answer block in reply")
N_BOOT = 2000
SEED = 0


# ------------------------------------------------------------------ loading
def read_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass                       # a torn final line from a live writer
    return pd.DataFrame(rows)


def reparse(df: pd.DataFrame) -> pd.DataFrame:
    """Rows a runner could not parse whose saved reply today's parser reads (e.g.
    the bare JSON object without its fence): the answer is recovered from the
    reply rather than by asking the model again, and the row is flagged
    `reparsed`. P(Yes) stays empty for them (the token log-probs were not kept)."""
    df = df.copy()
    df["reparsed"] = False
    if "error" not in df or "raw_reply" not in df:
        return df
    for col in ("label", "quoted_span", "justification", "confidence", "confidence_invalid"):
        if col not in df:
            df[col] = None
        df[col] = df[col].astype(object)
    for i in df.index[df["error"].isin(PARSE_ERRORS)]:
        reply = df.at[i, "raw_reply"]
        parsed = parse_reply(reply, confidence=True) if isinstance(reply, str) else None
        if parsed:
            for k, v in parsed.items():
                df.at[i, k] = v
            df.at[i, "error"] = np.nan
            df.at[i, "reparsed"] = True
    return df


def load_arm(path: Path) -> pd.DataFrame:
    """Latest row per id (a resumed run appends repairs after failures). The
    spend over every row in the file, superseded attempts included, is kept in
    df.attrs so the reported cost is what the run actually cost."""
    df = read_jsonl(path)
    if df.empty:
        return df
    df = reparse(df)
    df["ok"] = df["error"].isna() if "error" in df else True
    attempts = df.groupby("id").size()
    attrs = {"rows_in_file": int(len(df)),
             "cost_all_rows_usd": float(pd.to_numeric(df["cost_usd"], errors="coerce").sum())
             if "cost_usd" in df else None}
    df = (df.assign(_n=np.arange(len(df)))
            .sort_values(["ok", "_n"]).drop_duplicates("id", keep="last")
            .drop(columns="_n").set_index("id"))
    df["attempts"] = attempts.reindex(df.index).astype(int)
    for col in ("label", "confidence", "confidence_invalid", "justification", "quoted_span",
                "p_yes", "p_yes_censored", "raw_reply", "error", "cost_usd", "output_tokens",
                "thinking_tokens", "cache_read_tokens", "elapsed_s", "text_sha256"):
        if col not in df:
            df[col] = np.nan
    df.attrs.update(attrs)
    return df


def build_units(meta: pd.DataFrame, arms: dict[str, pd.DataFrame]) -> list[dict]:
    """One dict per sampled section with coder labels and both models' answers.
    A result row whose text hash differs from the sample's is a result for a
    different text (the sample was redrawn under the same ids): refuse to mix."""
    units, mismatched = [], []
    for m in meta.itertuples(index=False):
        for name, df in arms.items():
            if m.id in df.index and hasattr(m, "text_sha256"):
                got = df.loc[m.id].get("text_sha256")
                if isinstance(got, str) and got != m.text_sha256:
                    mismatched.append((name, m.id))
    if mismatched:
        raise SystemExit(f"{len(mismatched)} result rows were labelled on a different text than the "
                         f"current sample (first: {mismatched[:3]}); redraw or relabel before comparing")
    for m in meta.itertuples(index=False):
        final = getattr(m, "final_q1", None)
        u = dict(key=m.id, volume=int(m.volume), order=int(m.order), law=str(m.law),
                 chars=int(m.chars), clipped=bool(m.section_clipped),
                 coders=[1 if l == "Yes" else 0 for l in m.coder_labels],
                 coder_names=list(m.coders), n_coders=int(m.n_coders),
                 any_yes=bool(m.any_yes), unanimous_yes=bool(m.unanimous_yes),
                 unanimous_no=(int(m.n_yes) == 0),
                 final=(int(final == "Yes") if final in ("Yes", "No") else None),
                 final_status=str(getattr(m, "final_q1_status", "") or ""))
        for name, df in arms.items():
            row = df.loc[m.id] if m.id in df.index else None
            lab = row["label"] if row is not None and row.get("label") in ("Yes", "No") else None
            u[name] = None if lab is None else int(lab == "Yes")
            u[f"{name}_ran"] = row is not None          # asked; u[name] None then = no answer
            u[f"{name}_conf"] = (float(row["confidence"]) if row is not None
                                 and pd.notna(row.get("confidence")) else None)
            u[f"{name}_just"] = str(row.get("justification") or "") if row is not None else ""
            u[f"{name}_span"] = str(row.get("quoted_span") or "") if row is not None else ""
            if name == QWEN:
                u["p_yes"] = (float(row["p_yes"]) if row is not None and pd.notna(row.get("p_yes"))
                              else None)
        units.append(u)
    return units


# ------------------------------------------------------------------ statistics
def _cm(units, a: str, b: str) -> dict:
    cm = {}
    for u in units:
        cm[(u[a], u[b])] = cm.get((u[a], u[b]), 0.0) + 1.0
    return cm


def pair_stats(units, a: str = CLAUDE, b: str = QWEN) -> dict:
    """Agreement between two binary fields over complete cases."""
    s = parity._stats(_cm(units, a, b))
    nan = float("nan")
    out = {"n": int(s["n"]), "agreement": s["po"], "kappa": s["kappa"], "ac1": s["ac1"],
           f"yes_rate_{a}": s.get("row_yes", nan), f"yes_rate_{b}": s.get("col_yes", nan)}
    out["yes_rate_ratio"] = (s["row_yes"] / s["col_yes"]) if s.get("col_yes") else nan
    return out


def cluster_boot(units, fn, n_boot: int, seed: int,
                 keys=("agreement", "kappa", "ac1", "yes_rate_ratio")) -> dict:
    """Percentile intervals from a law-clustered bootstrap stratified by volume."""
    rng = np.random.default_rng(seed)
    by: dict = {}
    for u in units:
        by.setdefault((u["volume"], u["law"]), []).append(u)
    strata: dict = {}
    for k in by:
        strata.setdefault(k[0], []).append(k)
    draws = {k: [] for k in keys}
    for _ in range(n_boot):
        draw = []
        for ks in strata.values():
            draw += [ks[i] for i in rng.choice(len(ks), len(ks), replace=True)]
        r = fn([u for k in draw for u in by[k]])
        for k in keys:
            draws[k].append(r.get(k, np.nan))
    out = {}
    for k, v in draws.items():
        a = np.asarray(v, float)
        a = a[np.isfinite(a)]
        out[k] = ({"lo": float(np.percentile(a, 2.5)), "hi": float(np.percentile(a, 97.5))}
                  if len(a) else {"lo": None, "hi": None})
    return out


def complete(units, *fields):
    return [u for u in units if all(u.get(f) is not None for f in fields)]


def rate_matched_qwen(units, target_rate: float) -> list[dict]:
    """Qwen relabelled by cutting P(Yes) at the quantile that gives `target_rate`."""
    us = [u for u in units if u.get("p_yes") is not None]
    if not us:
        return []
    thr = float(np.quantile([u["p_yes"] for u in us], 1 - target_rate))
    return [dict(u, qwen_rm=int(u["p_yes"] >= thr), rm_threshold=thr) for u in us]


def final_stats(units, field: str) -> dict:
    """One model against the final reconciled label."""
    s = pair_stats(units, field, "final")
    pos = [u for u in units if u["final"] == 1]
    neg = [u for u in units if u["final"] == 0]
    said_yes = [u for u in units if u[field] == 1]
    s["hit_rate"] = _share(pos, field, 1)              # final-Yes sections the model also calls Yes
    s["false_alarm_rate"] = _share(neg, field, 1)      # final-No sections the model calls Yes
    s["precision"] = float(np.mean([u["final"] == 1 for u in said_yes])) if said_yes else float("nan")
    s["n_final_yes"], s["n_final_no"], s["n_model_yes"] = len(pos), len(neg), len(said_yes)
    return s


def vs_final(units, field: str, n_boot: int, seed: int) -> dict:
    """The headline comparison: the model against the final reconciled label, with
    the 2x2 table and law-clustered intervals."""
    us = complete(units, field, "final")
    out = final_stats(us, field)
    out["table"] = {f"{k[0]},{k[1]}": v for k, v in _cm(us, field, "final").items()}
    out["n_disputed"] = sum(u["final_status"] == "disputed" for u in us)
    out["disputed_model_yes"] = sum(u["final_status"] == "disputed" and u[field] == 1 for u in us)
    out["ci"] = cluster_boot(us, lambda b: final_stats(b, field), n_boot, seed,
                             keys=("agreement", "kappa", "ac1", "hit_rate", "false_alarm_rate",
                                   "precision", "yes_rate_ratio")) if us else {}
    return out


def vs_coders(units, field: str, n_boot: int, seed: int) -> dict:
    """Coder replacement (endpoint A) plus the plain hit / false-alarm picture."""
    us = complete(units, field)
    ea = parity.endpoint_a(us, field=field)
    ci = parity._boot(us, lambda b: parity.endpoint_a(b, field=field),
                      lambda u: (u["volume"], u["law"]), n_boot, seed,
                      stratify_by=lambda u: u["volume"])
    unan_yes = [u for u in us if u["unanimous_yes"]]
    unan_no = [u for u in us if u["unanimous_no"]]
    any_yes = [u for u in us if u["any_yes"]]
    coder_rate = float(np.mean([np.mean(u["coders"]) for u in us]))
    model_rate = float(np.mean([u[field] for u in us]))
    return {
        "n": len(us),
        "kappa_vs_reference_coder": ea["model"]["kappa"],
        "kappa_coder_vs_coder": ea["human"]["kappa"],
        "delta_kappa": ea["delta_kappa"], "delta_kappa_ci": ci["delta_kappa"],
        "delta_ac1": ea["delta_ac1"], "delta_ac1_ci": ci["delta_ac1"],
        "delta_agreement": ea["delta_po"], "delta_agreement_ci": ci["delta_po"],
        "agreement_vs_reference_coder": ea["model"]["po"],
        "agreement_coder_vs_coder": ea["human"]["po"],
        "yes_rate_model": model_rate, "yes_rate_coders": coder_rate,
        "yes_rate_ratio": model_rate / coder_rate if coder_rate else None,
        "hit_rate_unanimous_yes": _share(unan_yes, field, 1),
        "false_alarm_rate_unanimous_no": _share(unan_no, field, 1),
        "hit_rate_any_coder_yes": _share(any_yes, field, 1),
        "n_unanimous_yes": len(unan_yes), "n_unanimous_no": len(unan_no), "n_any_yes": len(any_yes),
    }


def _share(us, field, value) -> float | None:
    return float(np.mean([u[field] == value for u in us])) if us else None


def _match(us, field) -> float | None:
    """Share of sections where the model's label equals the final label."""
    g = [u for u in us if u.get("final") is not None and u.get(field) is not None]
    return float(np.mean([u[field] == u["final"] for u in g])) if g else None


def slices(units) -> dict:
    us = complete(units, CLAUDE, QWEN)
    qs = np.quantile([u["chars"] for u in us], [0.25, 0.5, 0.75]) if us else [0, 0, 0]

    def band(c):
        return ("Q1 shortest" if c <= qs[0] else "Q2" if c <= qs[1] else "Q3" if c <= qs[2]
                else "Q4 longest")

    def summarise(group):
        finals = [u["final"] for u in group if u["final"] is not None]
        return {"n": len(group), "agreement": float(np.mean([u[CLAUDE] == u[QWEN] for u in group])),
                "yes_rate_claude": float(np.mean([u[CLAUDE] for u in group])),
                "yes_rate_qwen": float(np.mean([u[QWEN] for u in group])),
                "final_yes_rate": float(np.mean(finals)) if finals else None,
                "claude_matches_final": _match(group, CLAUDE),
                "qwen_matches_final": _match(group, QWEN)}

    out = {"length_quartile_bounds_chars": [float(q) for q in qs]}
    for name, keyfn in (("by_volume", lambda u: str(u["volume"])),
                        ("by_length_quartile", lambda u: band(u["chars"])),
                        ("by_n_coders", lambda u: f"{u['n_coders']} coders")):
        groups: dict = {}
        for u in us:
            groups.setdefault(keyfn(u), []).append(u)
        out[name] = {k: summarise(g) for k, g in sorted(groups.items())}
    return out


def graded_view(units) -> dict:
    """Where Qwen's P(Yes) sits for the sections Claude calls Yes vs No."""
    us = [u for u in complete(units, CLAUDE) if u.get("p_yes") is not None]
    out = {}
    for lab, name in ((1, "claude_yes"), (0, "claude_no")):
        p = np.array([u["p_yes"] for u in us if u[CLAUDE] == lab])
        if not len(p):
            continue
        out[name] = {"n": int(len(p)),
                     "p_yes_quantiles": {q: float(np.quantile(p, q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
                     "share_p_yes_below_0.1": float(np.mean(p < 0.1)),
                     "share_p_yes_0.1_to_0.9": float(np.mean((p >= 0.1) & (p <= 0.9))),
                     "share_p_yes_above_0.9": float(np.mean(p > 0.9))}
    return out


# ------------------------------------------------------------------ one model at a time
def outcome(u, field: str) -> str:
    """One section's result for one model against the final label, in plain words."""
    if u.get(field) is None:
        return "no answer" if u.get(f"{field}_ran") else "not run"
    if u.get("final") is None:
        return "no final label"
    return {(1, 1): "caught", (0, 1): "missed", (1, 0): "false alarm",
            (0, 0): "correct No"}[(u[field], u["final"])]


def outcome_counts(group, field: str) -> dict:
    """Caught / missed / false alarm / correct No / no answer over a group, plus the
    share of answered sections that match the final label."""
    k = collections.Counter(outcome(u, field) for u in group)
    answered = k["caught"] + k["missed"] + k["false alarm"] + k["correct No"]
    return {"n": len(group), "answered": answered, "final_yes": sum(u["final"] == 1 for u in group),
            "caught": k["caught"], "missed": k["missed"], "false_alarms": k["false alarm"],
            "correct_no": k["correct No"], "no_answer": k["no answer"],
            "disagreements": k["missed"] + k["false alarm"],
            "match": (k["caught"] + k["correct No"]) / answered if answered else None}


def length_view(units, field: str) -> dict:
    """Outcomes by section length. The quarters are cut on the whole sample, so
    every model is split at the same lengths."""
    qs = [float(q) for q in np.quantile([u["chars"] for u in units], [0.25, 0.5, 0.75])]
    names = ["shortest quarter", "second quarter", "third quarter", "longest quarter"]
    ranges = [f"up to {qs[0]:,.0f} chars", f"{qs[0]:,.0f}-{qs[1]:,.0f} chars",
              f"{qs[1]:,.0f}-{qs[2]:,.0f} chars", f"over {qs[2]:,.0f} chars"]

    def band(c):
        return 0 if c <= qs[0] else 1 if c <= qs[1] else 2 if c <= qs[2] else 3

    out = {"bounds_chars": qs, "bands": []}
    for b in range(4):
        g = [u for u in units if band(u["chars"]) == b]
        d = outcome_counts(g, field)
        d.update(band=names[b], chars=ranges[b],
                 share_disagree=d["disagreements"] / d["answered"] if d["answered"] else None)
        out["bands"].append(d)
    return out


def trigger_view(units, field: str) -> dict:
    """How often the passage a model quoted names a participation mechanism
    (TRIGGER_RE), by outcome: a crude flag for "saw the words and reasoned them
    away" (misses) and "followed the words literally" (false alarms)."""
    out = {}
    for kind in ("caught", "missed", "false alarm", "correct No"):
        g = [u for u in units if outcome(u, field) == kind]
        out[kind] = {"n": len(g),
                     "quote_names_mechanism": sum(bool(TRIGGER_RE.search(u[f"{field}_span"])) for u in g)}
    return out


def retry_history(path: Path, meta: pd.DataFrame) -> tuple[dict, list]:
    """How a model's answers were reached: sections that failed on the first try,
    the attempt that rescued them, those still unanswered (with their final
    labels), and each attempt's reply limit as seen on the replies that hit it.
    Returns the summary and the rescued ids."""
    raw = read_jsonl(path)
    if raw.empty or "error" not in raw:
        return {}, []
    raw = reparse(raw)
    raw["attempt"] = raw.groupby("id").cumcount() + 1
    m = meta.set_index("id")
    final = m["final_q1"] if "final_q1" in m else pd.Series(dtype=object)
    first_fail, rescued_ids, unanswered = [], [], []
    rescued = collections.Counter()
    kinds = collections.Counter()
    for i, g in raw.groupby("id", sort=False):
        errs = g["error"].notna().tolist()
        if not errs[0]:
            continue
        first_fail.append(i)
        kinds[str(g["error"].iloc[0])] += 1
        k = next((k for k, e in enumerate(errs) if not e), None)
        if k is None:
            unanswered.append(i)
        else:
            rescued[k + 1] += 1
            rescued_ids.append(i)
    limits = {}
    if "finish_reason" in raw and "completion_tokens" in raw:
        hit = raw[raw["finish_reason"] == "length"]
        limits = {str(int(a)): int(t) for a, t in hit.groupby("attempt")["completion_tokens"].max().items()}
    n_final_yes = lambda ids: int(sum(final.get(i) == "Yes" for i in ids))  # noqa: E731
    chars = [int(m.at[i, "chars"]) for i in unanswered if i in m.index]
    return ({"first_try_failures": len(first_fail), "first_try_failure_kinds": dict(kinds),
             "first_try_failures_final_yes": n_final_yes(first_fail),
             "rescued_by_attempt": {str(k): v for k, v in sorted(rescued.items())},
             "rescued": len(rescued_ids), "unanswered": len(unanswered),
             "unanswered_final_yes": n_final_yes(unanswered),
             "unanswered_chars_median": float(np.median(chars)) if chars else None,
             "reply_limit_by_attempt": limits}, rescued_ids)


def p_yes_view(units, n_boot: int, seed: int) -> dict:
    """Qwen's token probability of "Yes" against the final label: where it falls,
    whether another cut-off than 0.5 would change anything, and the version cut to
    the final label's Yes-rate."""
    us = [u for u in complete(units, QWEN, "final") if u.get("p_yes") is not None]
    if not us:
        return {}
    p = np.array([u["p_yes"] for u in us])
    f = np.array([u["final"] for u in us])
    lab = np.array([u[QWEN] for u in us])
    bands = []
    for lo, hi, name in zip(P_YES_BANDS[:-1], P_YES_BANDS[1:], P_YES_BAND_LABELS):
        sel = (p >= lo) & (p < hi)
        bands.append({"band": name, "n": int(sel.sum()), "final_yes": int(f[sel].sum())})
    cuts = {}
    for t in (0.5, 0.1, 0.01, 0.001):
        s = final_stats([dict(u, cut=int(u["p_yes"] >= t)) for u in us], "cut")
        cuts[str(t)] = {k: s[k] for k in ("n_model_yes", "hit_rate", "false_alarm_rate", "precision", "kappa")}
    rm = rate_matched_qwen(us, float(f.mean()))
    s_rm = final_stats(rm, "qwen_rm")
    s_rm["threshold"] = rm[0]["rm_threshold"]
    s_rm["ci"] = cluster_boot(rm, lambda b: final_stats(b, "qwen_rm"), n_boot, seed,
                              keys=("kappa", "hit_rate", "false_alarm_rate", "precision"))
    missed = (f == 1) & (lab == 0)
    return {"n": len(us), "bands": bands,
            "share_decisive": float(np.mean((p < 0.01) | (p >= 0.99))),
            "n_middle": int(np.sum((p >= 0.01) & (p < 0.99))),
            "label_is_p_yes_above_half": float(np.mean((p >= 0.5) == (lab == 1))),
            "misses": int(missed.sum()), "misses_below_0.01": int(np.sum(missed & (p < 0.01))),
            "cutoffs": cuts, "rate_matched_to_final": s_rm}


def _mcnemar_exact(b: int, c: int) -> float | None:
    """Two-sided exact McNemar p-value from the two discordant counts."""
    n = b + c
    if not n:
        return None
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(b, c) + 1)) / 2 ** n)


def layout_check(units, flat: pd.DataFrame, chat: pd.DataFrame, n_boot: int, seed: int) -> dict:
    """Qwen in the chat layout (the main run: worked examples as conversation
    turns) against the one-block layout Claude receives (instructions, examples
    and section as one text), on the same sections, each against the final label."""
    if flat.empty:
        return {}
    lab = {i: int(v == "Yes") for i, v in flat["label"].items() if v in ("Yes", "No")}
    us = [dict(u, flat=lab[u["key"]]) for u in units if u["key"] in lab and u[QWEN] is not None]
    fin = complete(us, "final")
    pos = [u for u in fin if u["final"] == 1]
    neg = [u for u in fin if u["final"] == 0]
    changes = {"final_yes_no_to_yes": sum(u[QWEN] == 0 and u["flat"] == 1 for u in pos),
               "final_yes_yes_to_no": sum(u[QWEN] == 1 and u["flat"] == 0 for u in pos),
               "final_no_no_to_yes": sum(u[QWEN] == 0 and u["flat"] == 1 for u in neg),
               "final_no_yes_to_no": sum(u[QWEN] == 1 and u["flat"] == 0 for u in neg)}

    def diff(b):                            # a re-draw can miss every final-Yes section: then undefined
        a, q = final_stats(b, "flat"), final_stats(b, QWEN)
        return {k: a[k] - q[k] if a[k] is not None and q[k] is not None else float("nan")
                for k in ("hit_rate", "false_alarm_rate", "precision", "kappa")}

    def reasons_first(reply) -> bool:       # wrote text before the answer object
        return isinstance(reply, str) and not reply.lstrip().startswith(("```", "{"))

    ids = [u["key"] for u in us]
    return {"rows": int(len(flat)), "answered": len(lab),
            "reparsed": int(flat["reparsed"].sum()) if "reparsed" in flat else 0,
            "n": len(us), "agreement": pair_stats(us, QWEN, "flat"),
            "table": {f"{k[0]},{k[1]}": v for k, v in _cm(us, QWEN, "flat").items()},
            "chat": final_stats(fin, QWEN), "flat": final_stats(fin, "flat"),
            "changes": changes,
            "p_exact": {"final_yes": _mcnemar_exact(changes["final_yes_no_to_yes"], changes["final_yes_yes_to_no"]),
                        "final_no": _mcnemar_exact(changes["final_no_no_to_yes"], changes["final_no_yes_to_no"])},
            "difference": diff(fin) if pos and neg else {},
            "difference_ci": cluster_boot(fin, diff, n_boot, seed,
                                          keys=("hit_rate", "false_alarm_rate", "precision", "kappa"))
            if pos and neg else {},
            "reasons_first": {"n": len(ids),
                              "chat": int(sum(reasons_first(chat.at[i, "raw_reply"]) for i in ids)),
                              "flat": int(sum(reasons_first(flat.at[i, "raw_reply"]) for i in ids))}}


def confidence_analysis(units) -> dict:
    out = {}
    both = complete(units, CLAUDE, QWEN)
    for arm in (CLAUDE, QWEN):
        c = f"{arm}_conf"
        us = [u for u in complete(units, arm) if u.get(c) is not None]
        vals = np.array([u[c] for u in us])
        d = {"n_with_confidence": int(len(us)),
             "n_missing": int(sum(u.get(c) is None for u in complete(units, arm)))}
        if not len(vals):
            out[arm] = d
            continue
        d["quantiles"] = {q: float(np.quantile(vals, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}
        d["mean"] = float(vals.mean())
        d["by_label"] = {lab: float(np.mean([u[c] for u in us if u[arm] == v]))
                         for v, lab in ((1, "Yes"), (0, "No")) if any(u[arm] == v for u in us)}
        hist = np.histogram(vals, bins=CONF_BINS)[0]
        d["histogram"] = dict(zip(CONF_BIN_LABELS, [int(h) for h in hist]))
        # agreement with the other model, by this model's confidence bin
        bins_agree = {}
        for lo, hi, lab in zip(CONF_BINS[:-1], CONF_BINS[1:], CONF_BIN_LABELS):
            g = [u for u in both if u.get(c) is not None and lo <= u[c] < hi]
            if g:
                bins_agree[lab] = {"n": len(g), "agreement_with_other_model":
                                   float(np.mean([u[CLAUDE] == u[QWEN] for u in g]))}
        d["agreement_by_bin"] = bins_agree
        agree = [u[c] for u in both if u.get(c) is not None and u[CLAUDE] == u[QWEN]]
        disagree = [u[c] for u in both if u.get(c) is not None and u[CLAUDE] != u[QWEN]]
        d["mean_on_agreements"] = float(np.mean(agree)) if agree else None
        d["mean_on_disagreements"] = float(np.mean(disagree)) if disagree else None
        # reliability against the final reconciled label, by bin: a useful
        # confidence matches the final label more often in its higher bins
        rel = {}
        for lo, hi, lab in zip(CONF_BINS[:-1], CONF_BINS[1:], CONF_BIN_LABELS):
            g = [u for u in us if lo <= u[c] < hi and u["final"] is not None]
            if g:
                yes = [u for u in g if u[arm] == 1]
                no = [u for u in g if u[arm] == 0]
                rel[lab] = {"n": len(g), "share_matching_final": _match(g, arm),
                            "disagreements": sum(u[arm] != u["final"] for u in g),
                            "yes_calls": len(yes), "yes_calls_right": sum(u["final"] == 1 for u in yes),
                            "no_calls": len(no), "no_calls_final_yes": sum(u["final"] == 1 for u in no)}
        d["match_final_by_bin"] = rel
        d["share_at_1"] = float(np.mean(vals == 1.0))
        # Triage: send every answer stated below a cut (or with no confidence) to a
        # person; how many of the disagreements with the final label would they see?
        ans = complete(units, arm, "final")
        d["triage"] = []
        for cut in TRIAGE_CUTS:
            rev = [u for u in ans if u.get(c) is None or u[c] < cut]
            d["triage"].append({
                "below": cut, "reviewed": len(rev), "share_reviewed": len(rev) / len(ans) if ans else None,
                "disagreements_caught": sum(u[arm] != u["final"] for u in rev),
                "disagreements": sum(u[arm] != u["final"] for u in ans),
                "misses_caught": sum(u[arm] == 0 and u["final"] == 1 for u in rev),
                "misses": sum(u[arm] == 0 and u["final"] == 1 for u in ans),
                "false_alarms_caught": sum(u[arm] == 1 and u["final"] == 0 for u in rev),
                "false_alarms": sum(u[arm] == 1 and u["final"] == 0 for u in ans)})
        right = [u[c] for u in us if u["final"] is not None and u[arm] == u["final"]]
        wrong = [u[c] for u in us if u["final"] is not None and u[arm] != u["final"]]
        d["mean_when_matching_final"] = float(np.mean(right)) if right else None
        d["mean_when_not_matching_final"] = float(np.mean(wrong)) if wrong else None
        out[arm] = d
    qw = [u for u in complete(units, QWEN) if u.get("qwen_conf") is not None and u.get("p_yes") is not None]
    if len(qw) > 2:
        conf = pd.Series([u["qwen_conf"] for u in qw])
        p_label = pd.Series([u["p_yes"] if u[QWEN] == 1 else 1 - u["p_yes"] for u in qw])
        out["qwen_confidence_vs_token_probability"] = {
            "n": len(qw), "spearman": float(conf.corr(p_label, method="spearman")),
            "note": "token probability of the chosen label vs the model's stated confidence"}
    return out


def repeat_agreement(base: pd.DataFrame, repeat: pd.DataFrame) -> dict:
    ids = [i for i in repeat.index if i in base.index
           and base.loc[i, "label"] in ("Yes", "No") and repeat.loc[i, "label"] in ("Yes", "No")]
    if not ids:
        return {"n": 0}
    same = [base.loc[i, "label"] == repeat.loc[i, "label"] for i in ids]
    cm = {}
    for i in ids:
        k = (int(base.loc[i, "label"] == "Yes"), int(repeat.loc[i, "label"] == "Yes"))
        cm[k] = cm.get(k, 0.0) + 1.0
    s = parity._stats(cm)
    diffs = [abs(float(base.loc[i, "confidence"]) - float(repeat.loc[i, "confidence"])) for i in ids
             if pd.notna(base.loc[i, "confidence"]) and pd.notna(repeat.loc[i, "confidence"])]
    return {"n": len(ids), "label_agreement": float(np.mean(same)), "kappa": s["kappa"],
            "n_label_changes": int(len(ids) - sum(same)),
            "confidence_abs_diff_mean": float(np.mean(diffs)) if diffs else None,
            "confidence_abs_diff_p90": float(np.quantile(diffs, 0.9)) if diffs else None}


# ------------------------------------------------------------------ deliverables
def two_coder_sheet(meta: pd.DataFrame, arms: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per section, the two models as coders, in the IRR dataset's layout."""
    c, q = arms[CLAUDE], arms[QWEN]

    def col(df, key, idx, default="."):
        if idx in df.index and pd.notna(df.loc[idx].get(key)):
            return df.loc[idx][key]
        return default

    rows = []
    for m in meta.itertuples(index=False):
        rows.append({
            "Volume": int(m.volume), "unique key": int(m.order), "UniqueKey": m.id, "question": "Q1",
            "Claude": col(c, "label", m.id), "Qwen": col(q, "label", m.id),
            "Claude confidence": col(c, "confidence", m.id),
            "Qwen confidence": col(q, "confidence", m.id),
            "Qwen P(Yes)": col(q, "p_yes", m.id),
            "Claude reasoning": col(c, "justification", m.id, ""),
            "Qwen reasoning": col(q, "justification", m.id, ""),
            "Claude quoted span": col(c, "quoted_span", m.id, ""),
            "Qwen quoted span": col(q, "quoted_span", m.id, ""),
        })
    return pd.DataFrame(rows).sort_values(["Volume", "unique key"]).reset_index(drop=True)


def disagreement_table(units) -> pd.DataFrame:
    rows = []
    for u in complete(units, CLAUDE, QWEN):
        if u[CLAUDE] == u[QWEN]:
            continue
        rows.append({
            "UniqueKey": u["key"], "Volume": u["volume"], "law": u["law"], "chars": u["chars"],
            "Claude": "Yes" if u[CLAUDE] else "No", "Qwen": "Yes" if u[QWEN] else "No",
            "final label": {1: "Yes", 0: "No"}.get(u["final"], ""),
            "final label status": u["final_status"],
            "Claude confidence": u.get("claude_conf"), "Qwen confidence": u.get("qwen_conf"),
            "Qwen P(Yes)": u.get("p_yes"),
            "first answers": "|".join("Yes" if l else "No" for l in u["coders"]),
            "Claude quoted span": u["claude_span"], "Qwen quoted span": u["qwen_span"],
            "Claude reasoning": u["claude_just"], "Qwen reasoning": u["qwen_just"],
        })
    return pd.DataFrame(rows)


def final_label_table(units) -> pd.DataFrame:
    """Sections where a model's label differs from the final label, or where it gave
    no answer: both models' answers and reasons side by side."""
    def label(u, arm):
        o = outcome(u, arm)
        return o if o in ("no answer", "not run") else ("Yes" if u[arm] else "No")

    rows = []
    for u in units:
        outs = {arm: outcome(u, arm) for arm in ARMS}
        if not any(o in ("missed", "false alarm", "no answer") for o in outs.values()):
            continue
        rows.append({
            "UniqueKey": u["key"], "Volume": u["volume"], "law": u["law"], "chars": u["chars"],
            "final label": {1: "Yes", 0: "No"}.get(u["final"], ""), "final label status": u["final_status"],
            "first answers": "|".join("Yes" if l else "No" for l in u["coders"]),
            "Claude": label(u, CLAUDE), "Claude outcome": outs[CLAUDE],
            "Qwen": label(u, QWEN), "Qwen outcome": outs[QWEN],
            "Claude confidence": u.get("claude_conf"), "Qwen confidence": u.get("qwen_conf"),
            "Qwen P(Yes)": u.get("p_yes"),
            "Claude quoted span": u["claude_span"], "Qwen quoted span": u["qwen_span"],
            "Claude reasoning": u["claude_just"], "Qwen reasoning": u["qwen_just"],
        })
    return pd.DataFrame(rows)


OUTPUT_FIRST = ("id", "label", "confidence", "confidence_invalid", "p_yes", "p_yes_censored",
                "logprob_yes", "logprob_no", "quoted_span", "justification", "raw_reply", "error",
                "finish_reason", "attempts", "reparsed")


def export_output(arm: pd.DataFrame, meta: pd.DataFrame, path: Path) -> int:
    """One JSON line per sampled section, in sample order: the model's latest
    attempt with every field its runner recorded, plus how many attempts it took
    and whether the answer was re-read from the saved reply."""
    def value(v):
        if v is None or v is pd.NA or (isinstance(v, float) and not math.isfinite(v)):
            return None
        return v.item() if hasattr(v, "item") else v

    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for i in meta["id"]:
            if i not in arm.index:
                continue
            rec = {k: value(v) for k, v in arm.loc[i].items() if k != "ok"}
            rec["id"] = i
            rec = {k: v for k, v in rec.items() if v is not None}
            ordered = {k: rec[k] for k in OUTPUT_FIRST if k in rec}
            ordered.update({k: v for k, v in rec.items() if k not in ordered})
            fh.write(json.dumps(ordered, ensure_ascii=False, allow_nan=False) + "\n")
            n += 1
    return n


def coverage(arm: pd.DataFrame, meta: pd.DataFrame) -> dict:
    ids = set(meta["id"])
    present = arm[arm.index.isin(ids)] if not arm.empty else arm
    parsed = present[present["label"].isin(["Yes", "No"])] if not present.empty else present
    errors = present[present["error"].notna()] if not present.empty else present
    out = {"sample_rows": len(ids), "rows_returned": int(len(present)), "parsed": int(len(parsed)),
           "errors": int(len(errors)), "not_yet_run": int(len(ids) - len(present))}
    if len(parsed):
        out["confidence_missing"] = int(parsed["confidence"].isna().sum())
        out["yes"] = int((parsed["label"] == "Yes").sum())
        out["no"] = int((parsed["label"] == "No").sum())
        if "reparsed" in parsed:
            out["reparsed"] = int(parsed["reparsed"].fillna(False).astype(bool).sum())
        if "cost_usd" in parsed and parsed["cost_usd"].notna().any():
            out["api_equivalent_cost_usd_kept_rows"] = float(parsed["cost_usd"].sum())
            out["api_equivalent_cost_usd"] = arm.attrs.get("cost_all_rows_usd")   # every call made
            out["rows_in_file"] = arm.attrs.get("rows_in_file")
        if "elapsed_s" in parsed and parsed["elapsed_s"].notna().any():
            out["median_seconds_per_row"] = float(parsed["elapsed_s"].median())
        for tok in ("output_tokens", "thinking_tokens", "cache_read_tokens"):
            if tok in parsed and parsed[tok].notna().any():
                out[f"mean_{tok}"] = float(parsed[tok].mean())
        if "p_yes" in parsed and parsed["p_yes"].notna().any():
            out["p_yes_present"] = int(parsed["p_yes"].notna().sum())
            out["p_yes_censored"] = int(parsed["p_yes_censored"].fillna(False).astype(bool).sum())
    return out


def clean(obj):
    """NaN/inf -> None so the JSON is valid for browsers (json.dumps would emit NaN)."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if not math.isfinite(obj) else float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def _pct(x, digits=1):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100*x:.{digits}f}%"


def _num(x, digits=3):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{digits}f}"


def _ci(d, digits=3):
    if not d or d.get("lo") is None:
        return ""
    return f" [{d['lo']:.{digits}f}, {d['hi']:.{digits}f}]"


def _ci_pct(d, digits=1):
    if not d or d.get("lo") is None:
        return ""
    return f" [{100 * d['lo']:.{digits}f}%, {100 * d['hi']:.{digits}f}%]"


def report_md(res: dict) -> str:
    mm, cov, S = res["model_vs_model"], res["coverage"], res["sample"]
    ref = (f"Reference label: the final reconciled label (Yes when every coder's answer in the final "
           f"workbook is Yes): {S['final_yes']} Yes ({_pct(S['final_yes_rate'])}), {S['final_no']} No; "
           f"{S['final_disputed']} sections still split in the final workbook count as Yes (flagged), "
           f"{S['final_single']} have one coder's answer only. " if S.get("final_yes") is not None
           else "Reference label: not attached (run eval/final_labels.py). ")
    L = ["# Q1 two-coder study: Claude Opus 5.5 vs Qwen3.6-27B", "",
         f"Sample: {S['n']:,} double-coded panel sections, {S['volumes']} volumes. " + ref +
         "Descriptive comparison; intervals are 95% law-clustered bootstraps.", "",
         "## Coverage", "", "| coder | returned | parsed | errors | confidence missing | Yes | No |",
         "|---|---|---|---|---|---|---|"]
    for arm in (CLAUDE, QWEN):
        c = cov[arm]
        L.append(f"| {arm} | {c['rows_returned']} | {c['parsed']} | {c['errors']} | "
                 f"{c.get('confidence_missing', 'n/a')} | {c.get('yes', 'n/a')} | {c.get('no', 'n/a')} |")
    if res.get("vs_final"):
        L += ["", "## Each model against the final reconciled label", "",
              ("Both rows use the same sections (those with a label from both models), so they are like for like."
               if mm.get("n") else "Only one model has results so far; the rows cover its own labelled sections."), "",
              "| coder | n | agreement | kappa | AC1 | hit rate (final Yes) | false alarms (final No) | "
              "precision (model Yes) | Yes-rate (final) |",
              "|---|---|---|---|---|---|---|---|---|"]
        for arm, v in res["vs_final"].items():
            c = v.get("ci", {})
            L.append(f"| {arm} | {v['n']} | {_pct(v['agreement'])}{_ci_pct(c.get('agreement'))} | "
                     f"{_num(v['kappa'])}{_ci(c.get('kappa'))} | {_num(v['ac1'])}{_ci(c.get('ac1'))} | "
                     f"{_pct(v['hit_rate'])} (n={v['n_final_yes']}) | "
                     f"{_pct(v['false_alarm_rate'])} (n={v['n_final_no']}) | "
                     f"{_pct(v['precision'])} (n={v['n_model_yes']}) | "
                     f"{_pct(v.get('yes_rate_' + arm))} ({_pct(v.get('yes_rate_final'))}) |")
        L.append("")
        for arm, v in res["vs_final"].items():
            t = v.get("table", {})
            L.append(f"- {arm} (model / final label): Yes/Yes {int(t.get('1,1', 0))}, "
                     f"Yes/No {int(t.get('1,0', 0))}, No/Yes {int(t.get('0,1', 0))}, "
                     f"No/No {int(t.get('0,0', 0))}; of the {v['n_disputed']} disputed sections it "
                     f"called {v['disputed_model_yes']} Yes.")
        for arm, v in (res.get("vs_final_each_arm_all_rows") or {}).items():
            L.append(f"- sensitivity, {arm} on all of its own labelled sections (n={v['n']}): "
                     f"kappa {_num(v['kappa'])}{_ci(v.get('ci', {}).get('kappa'))}, "
                     f"hit rate {_pct(v['hit_rate'])}, false alarms {_pct(v['false_alarm_rate'])}")
    for arm, lv in (res.get("length_view") or {}).items():
        L += ["", f"## Where {arm} differs from the final label: section length", "",
              "| quarter of the sample | chars | sections | final Yes | caught | missed | false alarms | "
              "no answer | differ from final |", "|---|---|---|---|---|---|---|---|---|"]
        for b in lv["bands"]:
            L.append(f"| {b['band']} | {b['chars']} | {b['n']} | {b['final_yes']} | {b['caught']} | {b['missed']} | "
                     f"{b['false_alarms']} | {b['no_answer']} | {_pct(b['share_disagree'])} |")
        rh, rs = (res.get("retry_history") or {}).get(arm), (res.get("rescued_answers") or {}).get(arm)
        if rh:
            L.append(f"\n{rh['first_try_failures']} sections failed on the first try "
                     f"({rh['first_try_failures_final_yes']} of them final Yes); rescued by attempt: "
                     f"{rh['rescued_by_attempt']} (reply limits seen per attempt: {rh['reply_limit_by_attempt']}); "
                     f"{rh['unanswered']} still unanswered ({rh['unanswered_final_yes']} final Yes, median "
                     f"{_num(rh['unanswered_chars_median'], 0)} chars).")
        if rs:
            L.append(f"Rescued answers against the final label: {rs['caught']} caught, {rs['missed']} missed, "
                     f"{rs['false_alarms']} false alarms, {rs['correct_no']} correct No (match {_pct(rs['match'])}).")
        tr = (res.get("triggers") or {}).get(arm)
        if tr:
            L.append("Quoted passage names a participation mechanism (consult, comment, hearing, cooperate, "
                     "coordinate, concur, rulemaking): " + ", ".join(
                         f"{k} {v['quote_names_mechanism']} of {v['n']}" for k, v in tr.items()) + ".")
    ci = mm.get("ci", {})
    L += ["", "## The two models against each other", ""]
    if mm.get("n"):
        L += [f"n = {mm['n']} sections with both labels.", "",
              "| | Qwen Yes | Qwen No |", "|---|---|---|",
              f"| Claude Yes | {int(mm['table'].get('1,1', 0))} | {int(mm['table'].get('1,0', 0))} |",
              f"| Claude No | {int(mm['table'].get('0,1', 0))} | {int(mm['table'].get('0,0', 0))} |", "",
              f"- raw agreement {_pct(mm['agreement'])}{_ci(ci.get('agreement'))}",
              f"- Cohen's kappa {_num(mm['kappa'])}{_ci(ci.get('kappa'))}; AC1 {_num(mm['ac1'])}{_ci(ci.get('ac1'))}",
              f"- Yes-rate Claude {_pct(mm['yes_rate_claude'])} vs Qwen {_pct(mm['yes_rate_qwen'])} "
              f"(ratio {_num(mm['yes_rate_ratio'], 2)}{_ci(ci.get('yes_rate_ratio'), 2)})"]
    else:
        L.append("Waiting for both runs.")
    if res.get("model_vs_model_rate_matched"):
        rm = res["model_vs_model_rate_matched"]
        L.append(f"- rate-matched (Qwen cut at P(Yes) >= {rm['threshold']:.3g} to Claude's Yes-rate): "
                 f"agreement {_pct(rm['agreement'])}, kappa {_num(rm['kappa'])}")
    L += ["", "## Confidence (self-reported, 0-1)", "",
          "| coder | with confidence | median | mean | mean when matching final | mean when not | "
          "mean on model agreements | mean on model disagreements |",
          "|---|---|---|---|---|---|---|---|"]
    for arm in (CLAUDE, QWEN):
        c = res["confidence"].get(arm, {})
        L.append(f"| {arm} | {c.get('n_with_confidence', 0)} | {_num(c.get('quantiles', {}).get(0.5), 2)} | "
                 f"{_num(c.get('mean'), 3)} | {_num(c.get('mean_when_matching_final'), 3)} | "
                 f"{_num(c.get('mean_when_not_matching_final'), 3)} | {_num(c.get('mean_on_agreements'), 3)} | "
                 f"{_num(c.get('mean_on_disagreements'), 3)} |")
    for arm in (CLAUDE, QWEN):
        c = res["confidence"].get(arm, {})
        if c.get("histogram"):
            L.append(f"\n{arm} confidence bins: " + ", ".join(f"{k}: {v}" for k, v in c["histogram"].items()))
        if c.get("match_final_by_bin"):
            L.append(f"{arm} share matching the final label, by confidence bin: " + ", ".join(
                f"{k}: {_pct(v['share_matching_final'])} (n={v['n']})"
                for k, v in c["match_final_by_bin"].items()))
    for arm in (CLAUDE, QWEN):
        for t in res["confidence"].get(arm, {}).get("triage", []):
            L.append(f"{arm}: reviewing every answer stated below {t['below']:g} (or with no confidence) means "
                     f"{t['reviewed']} sections ({_pct(t['share_reviewed'])}) and would catch "
                     f"{t['disagreements_caught']} of {t['disagreements']} disagreements with the final label "
                     f"({t['misses_caught']} of {t['misses']} misses, {t['false_alarms_caught']} of "
                     f"{t['false_alarms']} false alarms).")
    if res["confidence"].get("qwen_confidence_vs_token_probability"):
        q = res["confidence"]["qwen_confidence_vs_token_probability"]
        L.append(f"\nQwen stated confidence vs token probability of its label: Spearman {_num(q['spearman'])} (n={q['n']}).")
    pv = res.get("p_yes_view")
    if pv:
        rm = pv["rate_matched_to_final"]
        L += ["", "## Qwen's P(Yes) against the final label", "",
              "| P(Yes) band | sections | final Yes |", "|---|---|---|"]
        L += [f"| {b['band']} | {b['n']} | {b['final_yes']} |" for b in pv["bands"]]
        L += ["", f"{_pct(pv['share_decisive'])} of answers sit below 0.01 or at 0.99 and above; "
                  f"{pv['misses_below_0.01']} of {pv['misses']} misses have P(Yes) below 0.01.",
              "Cut-offs: " + "; ".join(f"P(Yes) >= {t}: {v['n_model_yes']} Yes calls, hit rate {_pct(v['hit_rate'])}, "
                                       f"false alarms {_pct(v['false_alarm_rate'])}, kappa {_num(v['kappa'])}"
                                       for t, v in pv["cutoffs"].items()) + ".",
              f"Cut to the final label's Yes-rate (P(Yes) >= {rm['threshold']:.3g}): hit rate {_pct(rm['hit_rate'])}, "
              f"false alarms {_pct(rm['false_alarm_rate'])}, precision {_pct(rm['precision'])}, "
              f"kappa {_num(rm['kappa'])}{_ci(rm['ci'].get('kappa'))}."]
    if res.get("graded_view"):
        g = res["graded_view"]
        L += ["", "## Qwen's P(Yes) where Claude says Yes / No", ""]
        for k, v in g.items():
            L.append(f"- {k} (n={v['n']}): median P(Yes) {v['p_yes_quantiles'][0.5]:.3g}; "
                     f"below 0.1: {_pct(v['share_p_yes_below_0.1'])}, 0.1-0.9: {_pct(v['share_p_yes_0.1_to_0.9'])}, "
                     f"above 0.9: {_pct(v['share_p_yes_above_0.9'])}")
    if res.get("claude_repeat"):
        r = res["claude_repeat"]
        L += ["", "## Claude self-agreement (repeat run)", "",
              f"n = {r['n']}: label agreement {_pct(r.get('label_agreement'))}, kappa {_num(r.get('kappa'))}, "
              f"{r.get('n_label_changes')} label changes; mean |confidence difference| {_num(r.get('confidence_abs_diff_mean'))}."]
    lc = res.get("qwen_layout_check")
    if lc:
        a, ch, fl, cg = lc["agreement"], lc["chat"], lc["flat"], lc["changes"]
        dci = lc.get("difference_ci") or {}
        L += ["", "## Prompt-layout check (Qwen: chat layout vs the one-block layout Claude receives)", "",
              f"{lc['rows']} sections labelled again in the one-block layout; {lc['answered']} answered "
              f"({lc['reparsed']} of them re-read from replies that dropped the code fence). "
              f"n = {lc['n']} answered in both layouts: agreement {_pct(a['agreement'])}, kappa {_num(a['kappa'])}, "
              f"Yes-rate chat {_pct(a.get('yes_rate_qwen'))} vs one-block {_pct(a.get('yes_rate_flat'))}.", "",
              "| layout | hit rate | false alarms | precision | kappa vs final |", "|---|---|---|---|---|",
              f"| chat (main run) | {_pct(ch['hit_rate'])} ({ch['n_final_yes']} final Yes) | "
              f"{_pct(ch['false_alarm_rate'])} | {_pct(ch['precision'])} | {_num(ch['kappa'])} |",
              f"| one-block | {_pct(fl['hit_rate'])} | {_pct(fl['false_alarm_rate'])} | {_pct(fl['precision'])} | "
              f"{_num(fl['kappa'])} |", "",
              f"Changed answers: final-Yes sections No->Yes {cg['final_yes_no_to_yes']}, Yes->No "
              f"{cg['final_yes_yes_to_no']} (exact p {_num(lc['p_exact']['final_yes'], 4)}); final-No sections "
              f"No->Yes {cg['final_no_no_to_yes']}, Yes->No {cg['final_no_yes_to_no']} "
              f"(exact p {_num(lc['p_exact']['final_no'], 4)}). Differences (one-block minus chat): hit rate "
              f"{_num((lc.get('difference') or {}).get('hit_rate'))}{_ci(dci.get('hit_rate'))}, false alarms "
              f"{_num((lc.get('difference') or {}).get('false_alarm_rate'))}{_ci(dci.get('false_alarm_rate'))}, kappa "
              f"{_num((lc.get('difference') or {}).get('kappa'))}{_ci(dci.get('kappa'))}.",
              f"Replies that reason in text before the answer: chat {lc['reasons_first']['chat']} of "
              f"{lc['reasons_first']['n']}, one-block {lc['reasons_first']['flat']} of {lc['reasons_first']['n']}."]
    sl = res["slices"]
    if sl:
        L += ["", "## Slices", "",
              "| slice | n | models agree | Claude Yes | Qwen Yes | final Yes | Claude = final | Qwen = final |",
              "|---|---|---|---|---|---|---|---|"]
        for group in ("by_length_quartile", "by_n_coders", "by_volume"):
            for k, v in sl.get(group, {}).items():
                L.append(f"| {k} | {v['n']} | {_pct(v['agreement'])} | {_pct(v['yes_rate_claude'])} | "
                         f"{_pct(v['yes_rate_qwen'])} | {_pct(v.get('final_yes_rate'))} | "
                         f"{_pct(v.get('claude_matches_final'))} | {_pct(v.get('qwen_matches_final'))} |")
    L += ["", "## Secondary: against the coders' first answers (before reconciliation)", "",
          "Each model sits in one coder's seat and is scored against the other coder's first answer, exactly "
          "as the second coder is scored; these numbers are a different scale from the final-label ones above "
          "and are never compared with them. Both rows use the same sections.", "",
          "| coder | n | kappa vs a coder | coders' kappa | delta kappa | delta agreement | Yes-rate (coders) | "
          "hit rate, all coders Yes | false alarms, all coders No |",
          "|---|---|---|---|---|---|---|---|---|"]
    for arm, v in res["vs_coders"].items():
        L.append(f"| {arm} | {v['n']} | {_num(v['kappa_vs_reference_coder'])} | {_num(v['kappa_coder_vs_coder'])} | "
                 f"{_num(v['delta_kappa'])}{_ci(v['delta_kappa_ci'])} | "
                 f"{_num(v['delta_agreement'])}{_ci(v['delta_agreement_ci'])} | "
                 f"{_pct(v['yes_rate_model'])} ({_pct(v['yes_rate_coders'])}) | "
                 f"{_pct(v['hit_rate_unanimous_yes'])} (n={v['n_unanimous_yes']}) | "
                 f"{_pct(v['false_alarm_rate_unanimous_no'])} (n={v['n_unanimous_no']}) |")
    if res.get("vs_coders_each_arm_all_rows"):
        L.append("")
        for arm, v in res["vs_coders_each_arm_all_rows"].items():
            L.append(f"- sensitivity, {arm} on all of its own labelled sections (n={v['n']}): "
                     f"delta kappa {_num(v['delta_kappa'])}{_ci(v['delta_kappa_ci'])}")
    L += ["", "## Caveats", "",
          "- Descriptive only: no frozen manifest or pre-registration; the Q1 plan's gates are separate.",
          "- The reference is the final reconciled label. Sections still split in the final workbook count as "
          "Yes (the team's rule) and are flagged; the coders' first answers appear only in the secondary section.",
          "- Claude saw the kit in flat form (system prompt + section) with schema-enforced output keys; "
          "Qwen saw the chat form with the fenced json block. The prompt-layout check above shows the layout alone "
          "moves Qwen's answers, so part of any Claude-Qwen difference may be the layout.",
          "- Confidence is a stated belief, not a calibrated probability; Qwen's P(Yes) is the only token "
          "probability, and it is near 0 or 1 because Qwen reasons in text before it writes the label.",
          "- Claude is not deterministic; the repeat run measures its self-agreement.",
          "- Yes is rare (about 5% of sections), so Yes-rates are read beside every kappa."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main
def run(results: Path, n_boot: int, seed: int) -> dict:
    meta = pd.read_parquet(results / "sample_meta.parquet")
    arms = {name: load_arm(results / f) for name, f in ARMS.items() if (results / f).exists()}
    for name in ARMS:
        arms.setdefault(name, pd.DataFrame(columns=["label", "confidence", "justification",
                                                    "quoted_span", "p_yes", "error"]))
    units = build_units(meta, arms)
    both = complete(units, CLAUDE, QWEN)

    sample = {"n": len(units), "volumes": int(meta["volume"].nunique()),
              "laws": int(meta["law"].nunique()), "any_coder_yes": int(meta["any_yes"].sum()),
              "unanimous_yes": int(meta["unanimous_yes"].sum()),
              "clipped": int(meta["section_clipped"].sum())}
    if "final_q1" in meta:
        status = meta["final_q1_status"]
        sample.update(final_yes=int((meta["final_q1"] == "Yes").sum()),
                      final_no=int((meta["final_q1"] == "No").sum()),
                      final_disputed=int((status == "disputed").sum()),
                      final_single=int((status == "single coder").sum()),
                      final_missing=int((status == "missing").sum()),
                      final_yes_rate=float((meta["final_q1"] == "Yes").mean()))
    res = {"sample": sample,
           "coverage": {name: coverage(arms[name], meta) for name in ARMS},
           "n_boot": n_boot, "seed": seed}

    mm = pair_stats(both)
    mm["table"] = {f"{k[0]},{k[1]}": v for k, v in _cm(both, CLAUDE, QWEN).items()}
    mm["ci"] = cluster_boot(both, pair_stats, n_boot, seed) if both else {}
    res["model_vs_model"] = mm
    if both and mm.get("yes_rate_claude"):
        rm_units = rate_matched_qwen(both, mm["yes_rate_claude"])
        if rm_units:
            s = pair_stats(rm_units, CLAUDE, "qwen_rm")
            res["model_vs_model_rate_matched"] = {"threshold": rm_units[0]["rm_threshold"],
                                                  "n": s["n"], "agreement": s["agreement"],
                                                  "kappa": s["kappa"], "ac1": s["ac1"]}
    # Both arms on the common complete set, so they are like for like; each arm
    # on all of its own labelled rows as a sensitivity.
    base = both if both else units
    res["vs_final"] = {arm: vs_final(base, arm, n_boot, seed) for arm in ARMS
                       if complete(base, arm, "final")}
    # (sensitivities only once both models have results; before that the
    # headline already covers each model's own rows)
    res["vs_final_each_arm_all_rows"] = {arm: vs_final(units, arm, n_boot, seed) for arm in ARMS
                                         if both and complete(units, arm, "final")
                                         and len(complete(units, arm)) != len(base)}
    res["vs_coders"] = {arm: vs_coders(base, arm, n_boot, seed) for arm in ARMS
                        if complete(base, arm)}
    res["vs_coders_each_arm_all_rows"] = {arm: vs_coders(units, arm, n_boot, seed) for arm in ARMS
                                          if both and complete(units, arm)
                                          and len(complete(units, arm)) != len(base)}
    res["slices"] = slices(units) if both else {}
    res["graded_view"] = graded_view(units)
    res["confidence"] = confidence_analysis(units)
    res["conf_bin_labels"] = CONF_BIN_LABELS

    # Each model on its own, as soon as its run exists
    ran = [arm for arm in ARMS if complete(units, arm)]
    res["length_view"] = {arm: length_view(units, arm) for arm in ran}
    res["triggers"] = {arm: trigger_view(units, arm) for arm in ran}
    res["retry_history"], res["rescued_answers"] = {}, {}
    for arm in ran:
        res["retry_history"][arm], rescued = retry_history(results / ARMS[arm], meta)
        ids = set(rescued)
        if ids:
            res["rescued_answers"][arm] = outcome_counts([u for u in units if u["key"] in ids], arm)
    res["p_yes_view"] = p_yes_view(units, n_boot, seed)

    repeat = results / "claude_repeat.jsonl"
    if repeat.exists():
        res["claude_repeat"] = repeat_agreement(arms[CLAUDE], load_arm(repeat))
    flat = results / "qwen_flat300.jsonl"
    if flat.exists() and not arms[QWEN].empty:
        res["qwen_layout_check"] = layout_check(units, load_arm(flat), arms[QWEN], n_boot, seed)

    (results / "REPORT.md").write_text(report_md(res))   # before clean(): it indexes float keys
    res = clean(res)
    (results / "comparison.json").write_text(json.dumps(res, indent=1, allow_nan=False))
    final_label_table(units).to_csv(results / "final_label_disagreements.csv", index=False)
    for arm in ran:
        export_output(arms[arm], meta, results / f"{arm}_output.jsonl")
    sheet = two_coder_sheet(meta, arms)
    sheet.to_csv(results / "q1_two_coder_sheet.csv", index=False)
    try:
        sheet.to_excel(results / "q1_two_coder_sheet.xlsx", index=False)
    except Exception as exc:  # openpyxl missing: the csv is the record
        print(f"  note: xlsx not written ({exc})")
    disagreement_table(units).to_csv(results / "disagreements.csv", index=False)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    res = run(args.results, args.n_boot, args.seed)
    mm = res["model_vs_model"]
    print(f"model vs model: n={mm['n']} agreement={_pct(mm.get('agreement'))} kappa={_num(mm.get('kappa'))}")
    for arm, v in res["vs_final"].items():
        print(f"{arm} vs final label: n={v['n']} kappa={_num(v['kappa'])}{_ci(v.get('ci', {}).get('kappa'))} "
              f"hit rate={_pct(v['hit_rate'])} false alarms={_pct(v['false_alarm_rate'])}")
    for arm, v in res["vs_coders"].items():
        print(f"{arm} vs coders' first answers: n={v['n']} delta kappa={_num(v['delta_kappa'])}{_ci(v['delta_kappa_ci'])}")
    print(f"wrote comparison.json, q1_two_coder_sheet.csv, disagreements.csv, REPORT.md -> {args.results}")


if __name__ == "__main__":
    main()
