#!/usr/bin/env python3
"""Score few-shot predictions against the SME held-out labels.

Accuracy is close to meaningless on this data - Q1 is 3.9% positive, so a model
that always says "No" scores 96%. The headline numbers here are therefore the
Yes-class precision/recall/F1 and MCC, each with a bootstrap CI, because Q1's 69
positives cannot support a tight estimate and the report should say so.

    python eval/score.py --results-dir results --out results/metrics.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DATASET = REPO / "data" / "fewshot_q1q6"
BOOTSTRAP_N = 2000
RNG_SEED = 0



def read_jsonl(path) -> "pd.DataFrame":
    """Tolerant JSONL reader.

    The runner appends and flushes per row, so a reader that runs while a
    repair pass is still writing can catch a half-written final line.
    pd.read_json would abort on it; skipping it loses at most the row that is
    mid-flight and will be present next time.
    """
    import pandas as pd

    rows, bad = [], 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
    if bad:
        print(f"  note: skipped {bad} unparseable line(s) in {path} (writer still active)")
    return pd.DataFrame(rows)

def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def counts(gold: np.ndarray, pred: np.ndarray) -> dict:
    """Confusion counts with Yes as the positive class."""
    return {
        "tp": int(((gold == "Yes") & (pred == "Yes")).sum()),
        "fp": int(((gold == "No") & (pred == "Yes")).sum()),
        "fn": int(((gold == "Yes") & (pred == "No")).sum()),
        "tn": int(((gold == "No") & (pred == "No")).sum()),
    }


def metrics_from_counts(c: dict) -> dict:
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    denom = np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / denom) if denom else 0.0
    # Cohen's kappa against the SME as the second rater.
    po = (tp + tn) / n if n else 0.0
    pe = (((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)) if n else 0.0
    kappa = (po - pe) / (1 - pe) if pe != 1 else 0.0
    # Operator-specified rates. NOTE the denominators: TP and FP are both over the
    # number of actual positives, TN and FN both over the number of actual
    # negatives. That is deliberate and NOT the textbook FPR/FNR - fp_rate here
    # is "false alarms per real positive", and fn_rate is "misses per real
    # negative". Keeping them symmetric within each class is the point.
    actual_pos, actual_neg = tp + fn, fp + tn
    return {
        "n": n, **c,
        "actual_positives": actual_pos,
        "actual_negatives": actual_neg,
        "rate_true_positive": tp / actual_pos if actual_pos else 0.0,
        "rate_false_positive": fp / actual_pos if actual_pos else 0.0,
        "rate_true_negative": tn / actual_neg if actual_neg else 0.0,
        "rate_false_negative": fn / actual_neg if actual_neg else 0.0,
        "accuracy": po,
        "precision_yes": prec,
        "recall_yes": rec,
        "f1_yes": f1,
        "specificity": spec,
        "balanced_accuracy": (rec + spec) / 2,
        "mcc": mcc,
        "cohen_kappa": kappa,
        "predicted_positive_rate": (tp + fp) / n if n else 0.0,
        "actual_positive_rate": (tp + fn) / n if n else 0.0,
    }


def bootstrap_ci(gold: np.ndarray, pred: np.ndarray, keys=("f1_yes", "mcc", "recall_yes",
                                                           "precision_yes")) -> dict:
    """Percentile CIs by resampling rows with replacement."""
    rng = np.random.default_rng(RNG_SEED)
    n = len(gold)
    if n == 0:
        return {}
    draws = {k: [] for k in keys}
    for _ in range(BOOTSTRAP_N):
        idx = rng.integers(0, n, n)
        m = metrics_from_counts(counts(gold[idx], pred[idx]))
        for k in keys:
            draws[k].append(m[k])
    return {k: {"lo": float(np.percentile(v, 2.5)), "hi": float(np.percentile(v, 97.5))}
            for k, v in draws.items()}


def span_quality(df: pd.DataFrame, question: str) -> dict:
    """Is the model's quoted_span real, and does it point where the SME pointed?

    A model can get the label right for the wrong reason; the kit asks for a
    verbatim supporting quote precisely so that is checkable.
    """
    pred_yes = df[df.pred == "Yes"]
    # bool() matters: `a and b` yields "" (not False) for an empty span, which
    # would make this a mixed str/bool list that np.mean cannot reduce.
    verbatim = [bool(norm(r.quoted_span)) and norm(r.quoted_span) in norm(r.Text)
                for r in pred_yes.itertuples()]

    both = df[(df.pred == "Yes") & (df.gold == "Yes")]
    ious = []
    for r in both.itertuples():
        sme, model = norm(getattr(r, f"{question.upper()}_span")), norm(r.quoted_span)
        if not sme or not model:
            continue
        a, b = set(sme.lower().split()), set(model.lower().split())
        if a | b:
            ious.append(len(a & b) / len(a | b))
    return {
        "predicted_yes": int(len(pred_yes)),
        "span_verbatim_rate": float(np.mean(verbatim)) if verbatim else None,
        "span_nonempty_rate": float((pred_yes.quoted_span.map(norm) != "").mean())
                              if len(pred_yes) else None,
        "sme_span_iou_mean": float(np.mean(ious)) if ious else None,
        "sme_span_iou_median": float(np.median(ious)) if ious else None,
        "sme_span_compared": len(ious),
    }


def slice_metrics(df: pd.DataFrame, by: str) -> list[dict]:
    out = []
    for value, g in df.groupby(by, dropna=False):
        m = metrics_from_counts(counts(g.gold.values, g.pred.values))
        out.append({"slice": by, "value": str(value), **m})
    return out


def score_question(question: str, results_dir: Path, heldout: pd.DataFrame) -> dict:
    raw_path = results_dir / question / "raw.jsonl"
    if not raw_path.exists():
        return {"error": f"{raw_path} not found"}

    preds = read_jsonl(raw_path)
    preds = preds.drop_duplicates(subset="id", keep="last")  # resume can re-emit
    for col in ("label", "quoted_span", "justification", "error", "finish_reason"):
        if col not in preds:
            preds[col] = None

    df = heldout.merge(preds, left_on="UniqueKey", right_on="id", how="left")
    df["gold"] = df[question.upper()].map(norm)
    df["pred_raw"] = df["label"].map(lambda v: v if v in ("Yes", "No") else None)

    total = len(df)
    unparsed = df.pred_raw.isna()
    failure_kinds = (df.loc[unparsed, "error"].fillna("no response recorded")
                     .value_counts().to_dict())

    # Two readings of the same run: strict drops unparseable rows, deployed
    # forces them to No (what a pipeline must actually do with a non-answer).
    scored = df[~unparsed].copy()
    scored["pred"] = scored.pred_raw
    deployed = df.copy()
    deployed["pred"] = deployed.pred_raw.fillna("No")

    gold_s, pred_s = scored.gold.values, scored.pred.values
    primary = metrics_from_counts(counts(gold_s, pred_s))
    gold_d, pred_d = deployed.gold.values, deployed.pred.values

    all_no = metrics_from_counts(counts(gold_d, np.full(len(gold_d), "No")))
    all_yes = metrics_from_counts(counts(gold_d, np.full(len(gold_d), "Yes")))

    length_q = pd.qcut(df.TextChars, 4, labels=["Q1 shortest", "Q2", "Q3", "Q4 longest"],
                       duplicates="drop")
    scored_sliced = scored.assign(length_bucket=length_q.loc[scored.index])

    lat = df["elapsed_s"].dropna() if "elapsed_s" in df else pd.Series(dtype=float)
    def tok(col):
        return float(df[col].dropna().sum()) if col in df else 0.0

    return {
        "question": question,
        "rows": total,
        "coverage": {
            "parsed": int((~unparsed).sum()),
            "unparsed": int(unparsed.sum()),
            "parse_rate": float((~unparsed).mean()),
            "failure_kinds": failure_kinds,
            "truncated_at_max_tokens": int((df.finish_reason == "length").sum()),
            "section_clipped": int(df.get("section_clipped", pd.Series(dtype=bool))
                                   .fillna(False).sum()),
        },
        "primary_strict": {**primary, "ci": bootstrap_ci(gold_s, pred_s)},
        "deployed_failures_as_no": metrics_from_counts(counts(gold_d, pred_d)),
        "baselines": {"always_no": all_no, "always_yes": all_yes},
        "spans": span_quality(scored, question),
        "slices": (slice_metrics(scored, "Volume")
                   + slice_metrics(scored, "EntryType")
                   + slice_metrics(scored_sliced, "length_bucket")),
        "throughput": {
            "median_latency_s": float(lat.median()) if len(lat) else None,
            "p95_latency_s": float(lat.quantile(0.95)) if len(lat) else None,
            "prompt_tokens": tok("prompt_tokens"),
            "completion_tokens": tok("completion_tokens"),
            "cached_prompt_tokens": tok("cached_tokens"),
            "mean_completion_tokens": (float(df["completion_tokens"].dropna().mean())
                                       if "completion_tokens" in df else None),
        },
        "errors": [
            {
                "id": r.UniqueKey, "volume": int(r.Volume), "kind": kind,
                "law": str(r.LawIdentifier), "section": str(r.SectionName),
                "chars": int(r.TextChars),
                "text": str(r.Text)[:1200],
                "gold_span": norm(getattr(r, f"{question.upper()}_span"))[:600],
                "model_span": norm(r.quoted_span)[:600],
                "justification": norm(r.justification)[:900],
            }
            for kind, subset in (
                ("false_positive", scored[(scored.gold == "No") & (scored.pred == "Yes")]),
                ("false_negative", scored[(scored.gold == "Yes") & (scored.pred == "No")]),
            )
            for r in subset.itertuples()
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results-dir", type=Path, default=REPO / "results")
    ap.add_argument("--out", type=Path, default=REPO / "results" / "metrics.json")
    ap.add_argument("--questions", nargs="+", default=["q1", "q6"])
    args = ap.parse_args()

    heldout = pd.read_parquet(DATASET / "fewshot_q1q6_heldout.parquet")
    run_meta = {}
    meta_path = args.results_dir / "run_meta.json"
    if meta_path.exists():
        run_meta = json.loads(meta_path.read_text())

    report = {"run": run_meta, "test_set": {
        "rows": len(heldout),
        "volumes": sorted(heldout.Volume.unique().tolist()),
        "source": str(DATASET),
    }, "questions": {}}

    for q in args.questions:
        report["questions"][q] = score_question(q, args.results_dir, heldout)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, default=str))
    print(f"wrote {args.out}\n")

    for q, r in report["questions"].items():
        if "error" in r:
            print(f"{q.upper()}: {r['error']}")
            continue
        p, c = r["primary_strict"], r["coverage"]
        ci = p["ci"].get("f1_yes", {})
        print(f"{q.upper()}  n={p['n']}  parse={c['parse_rate']:.1%}")
        print(f"   F1(Yes) {p['f1_yes']:.3f} [{ci.get('lo',0):.3f}-{ci.get('hi',0):.3f}]"
              f"   P {p['precision_yes']:.3f}  R {p['recall_yes']:.3f}")
        print(f"   MCC {p['mcc']:.3f}   kappa {p['cohen_kappa']:.3f}"
              f"   bal.acc {p['balanced_accuracy']:.3f}   acc {p['accuracy']:.3f}"
              f"  (always-No acc {r['baselines']['always_no']['accuracy']:.3f})")
        print(f"   confusion tp={p['tp']} fp={p['fp']} fn={p['fn']} tn={p['tn']}"
              f"   span verbatim {r['spans']['span_verbatim_rate']}\n")


if __name__ == "__main__":
    main()
