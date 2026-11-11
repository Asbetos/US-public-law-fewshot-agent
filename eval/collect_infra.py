#!/usr/bin/env python3
"""Collect the measured infrastructure cost of the run.

Everything here is read back from the server log, the GPU, the model on disk and
the per-row results - nothing is estimated. The point is that on this hardware
the infrastructure IS the finding: a 27B model in 4-bit leaves ~2 GiB for KV on a
23 GB card, and that single number explains the throughput.

    python eval/collect_infra.py --out results/infra.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GIB = 1024 ** 3



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

def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:
        return ""


def dir_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())


def parse_server_log(log: Path) -> dict:
    """Pull the measured memory/KV/throughput facts out of vLLM's own logging."""
    if not log.exists():
        return {}
    text = log.read_text(errors="ignore")

    def one(pattern, cast=float, default=None):
        m = re.findall(pattern, text)
        return cast(m[-1].replace(",", "")) if m else default

    running = [int(x) for x in re.findall(r"Running: (\d+) reqs", text)]
    gen = [float(x) for x in re.findall(r"Avg generation throughput: ([0-9.]+) tokens/s", text)]
    hits = [float(x) for x in re.findall(r"Prefix cache hit rate: ([0-9.]+)%", text)]
    # ignore idle samples - they say nothing about capacity
    busy_run = [r for r in running if r > 0]
    busy_gen = [g for g in gen if g > 1]

    args = {}
    m = re.search(r"non-default args: (\{.*?\})\n", text)
    if m:
        try:
            args = json.loads(m.group(1).replace("'", '"').replace("True", "true")
                              .replace("False", "false").replace("None", "null"))
        except Exception:
            pass

    kv_gib = one(r"Available KV cache memory: ([0-9.]+) GiB")
    kv_tokens = one(r"GPU KV cache size: ([0-9,]+) tokens", int)
    return {
        "weights_and_runtime_gib": one(r"Actual usage is ([0-9.]+) GiB for consumed memory"),
        "model_loading_gib": one(r"Model loading took ([0-9.]+) GiB"),
        "peak_activation_gib": one(r"([0-9.]+) GiB for peak activation"),
        # anchored on the capture line: a bare "took N GiB" also matches the
        # model-loading line, which is 18.32 GiB, not the graph cost
        "cuda_graphs_gib": one(r"Graph capturing finished in \d+ secs, took ([0-9.]+) GiB"),
        "kv_cache_gib": kv_gib,
        "kv_cache_tokens": kv_tokens,
        "kv_bytes_per_token": round(kv_gib * GIB / kv_tokens) if kv_gib and kv_tokens else None,
        "attention_block_tokens": one(r"Setting attention block size to (\d+) tokens", int),
        "kv_blocks": (kv_tokens // one(r"Setting attention block size to (\d+) tokens", int, 1)
                      if kv_tokens else None),
        "prefix_cache_hit_rate_pct": round(max(hits), 1) if hits else None,
        "mean_concurrent_reqs": round(sum(busy_run) / len(busy_run), 1) if busy_run else None,
        "max_concurrent_reqs": max(running) if running else None,
        "mean_generation_tok_s": round(sum(busy_gen) / len(busy_gen), 1) if busy_gen else None,
        "peak_generation_tok_s": round(max(gen), 1) if gen else None,
        "weights_load_seconds": one(r"Loading weights took ([0-9.]+) seconds"),
        "server_args": args,
    }


def per_question(results_dir: Path, run_log: Path) -> dict:
    """Per-row cost, straight from the recorded results."""
    import numpy as np
    import pandas as pd

    wall = {}
    if run_log.exists():
        # run_batch prints "done in 12.3m: ..." per question, in q6 then q1 order
        mins = re.findall(r"^done in ([0-9.]+)m", run_log.read_text(errors="ignore"), re.M)
        for q, m in zip(("q6", "q1"), mins):
            wall[q] = float(m) * 60

    out = {}
    for q in ("q6", "q1"):
        raw = results_dir / q / "raw.jsonl"
        if not raw.exists():
            continue
        df = read_jsonl(raw).drop_duplicates(subset="id", keep="last")
        lat = df.get("elapsed_s", pd.Series(dtype=float)).dropna()
        pt = df.get("prompt_tokens", pd.Series(dtype=float)).dropna()
        ct = df.get("completion_tokens", pd.Series(dtype=float)).dropna()
        cached = df.get("cached_tokens", pd.Series(dtype=float)).dropna()
        w = wall.get(q)
        out[q] = {
            "rows": int(len(df)),
            "wall_seconds": w,
            "median_seconds_per_row": float(lat.median()) if len(lat) else None,
            "p95_seconds_per_row": float(lat.quantile(0.95)) if len(lat) else None,
            "rows_per_hour": round(3600 * len(df) / w, 1) if w else None,
            "mean_prompt_tokens": float(pt.mean()) if len(pt) else None,
            "mean_completion_tokens": float(ct.mean()) if len(ct) else None,
            "mean_cached_tokens": float(cached.mean()) if len(cached) else None,
            "total_prompt_tokens": float(pt.sum()) if len(pt) else None,
            "total_completion_tokens": float(ct.sum()) if len(ct) else None,
            "latency_by_tokens": _latency_by_tokens(df),
        }
    return out


# Fixed, human-readable token buckets. Section tokens run min 11 / p50 132 /
# p90 589 / max 29,983, so the low bins are where most of the corpus lives and
# the high bins are rare but expensive - the counts on each bar say which.
TOKEN_BINS = [(0, 50, "< 50"), (50, 100, "50–99"), (100, 200, "100–199"),
              (200, 400, "200–399"), (400, 800, "400–799"), (800, 10**9, "800+")]


def _latency_by_tokens(df) -> list:
    """Median seconds per section, bucketed by the section's true token length.

    Characters are a bad proxy here (1.1-4.9 chars/token across this corpus), so
    this joins the cached tokenizer output rather than using TextChars.
    """
    import pandas as pd

    cache = REPO / "results" / "section_tokens.json"
    if not cache.exists() or "elapsed_s" not in df:
        return []
    tokens = json.loads(cache.read_text())
    m = df.dropna(subset=["elapsed_s"]).copy()
    m["section_tokens"] = m["id"].map(tokens)
    m = m.dropna(subset=["section_tokens"])
    if not len(m):
        return []

    out = []
    for lo, hi, label in TOKEN_BINS:
        g = m[(m.section_tokens >= lo) & (m.section_tokens < hi)]
        if not len(g):
            continue
        out.append({
            "bucket": label,
            "rows": int(len(g)),
            "median_seconds": float(g.elapsed_s.median()),
            "p25_seconds": float(g.elapsed_s.quantile(0.25)),
            "p75_seconds": float(g.elapsed_s.quantile(0.75)),
            "median_tokens": int(g.section_tokens.median()),
            "median_completion_tokens": (float(g.completion_tokens.median())
                                         if "completion_tokens" in g else None),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO / "results" / "infra.json")
    ap.add_argument("--results-dir", type=Path, default=REPO / "results")
    ap.add_argument("--server-log", type=Path,
                    default=Path("/groups/brooksgrp/citizen_voice/models/vllm_server.log"))
    ap.add_argument("--run-log", type=Path,
                    default=Path("/groups/brooksgrp/citizen_voice/models/fullrun.log"))
    ap.add_argument("--model-dir", type=Path,
                    default=Path("/groups/brooksgrp/citizen_voice/models/"
                                 "cyankiwi__Qwen3.6-27B-AWQ-INT4"))
    args = ap.parse_args()

    server = parse_server_log(args.server_log)
    gpu_csv = sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader")
    name, total_mib, driver = ([p.strip() for p in gpu_csv.split(",")] + ["", "", ""])[:3]
    total_gib = float(re.sub(r"[^0-9.]", "", total_mib)) / 1024 if total_mib else None

    cfg = {}
    cfg_path = args.model_dir / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
    text_cfg = cfg.get("text_config", {})
    layers = text_cfg.get("num_hidden_layers")
    interval = text_cfg.get("full_attention_interval")

    weights = server.get("weights_and_runtime_gib")
    kv = server.get("kv_cache_gib")
    graphs = server.get("cuda_graphs_gib")
    used = sum(v for v in (weights, kv, graphs) if v)

    infra = {
        "gpu": {"name": name, "total_gib": round(total_gib, 2) if total_gib else None,
                "driver": driver},
        "memory_gib": {
            "weights_and_runtime": weights,
            "kv_cache": kv,
            "cuda_graphs": graphs,
            "peak_activation": server.get("peak_activation_gib"),
            "unused": round(total_gib - used, 2) if total_gib and used else None,
            "total": round(total_gib, 2) if total_gib else None,
        },
        "kv": {k: server.get(k) for k in
               ("kv_cache_tokens", "kv_bytes_per_token", "attention_block_tokens", "kv_blocks")},
        "model": {
            "repo": args.model_dir.name.replace("__", "/"),
            "disk_gib": round(dir_bytes(args.model_dir) / GIB, 2) if args.model_dir.exists() else None,
            "quantisation": (cfg.get("quantization_config", {}) or {}).get("quant_method")
                            or "AWQ 4-bit (compressed-tensors)",
            "architecture": (cfg.get("architectures") or [None])[0],
            "layers": layers,
            "full_attention_layers": (layers // interval) if layers and interval else None,
            "hidden_size": text_cfg.get("hidden_size"),
            "vocab_size": text_cfg.get("vocab_size"),
            "kv_heads": text_cfg.get("num_key_value_heads"),
            "head_dim": text_cfg.get("head_dim"),
        },
        "serving": {
            "vllm": sh(f"{REPO}/.venv-vllm/bin/python -c \"import vllm;print(vllm.__version__)\""),
            "torch": sh(f"{REPO}/.venv-vllm/bin/python -c \"import torch;print(torch.__version__)\""),
            **{k: server["server_args"].get(k) for k in
               ("max_model_len", "max_num_seqs", "gpu_memory_utilization",
                "kv_cache_dtype", "enable_prefix_caching")},
            "weights_load_seconds": server.get("weights_load_seconds"),
        },
        "observed": {k: server.get(k) for k in
                     ("prefix_cache_hit_rate_pct", "mean_concurrent_reqs", "max_concurrent_reqs",
                      "mean_generation_tok_s", "peak_generation_tok_s")},
        "per_question": per_question(args.results_dir, args.run_log),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(infra, indent=2))
    print(f"wrote {args.out}")
    m = infra["memory_gib"]
    print(f"  GPU {infra['gpu']['name']} {m['total']} GiB: weights {m['weights_and_runtime']}"
          f" + KV {m['kv_cache']} + graphs {m['cuda_graphs']} -> {m['unused']} unused")
    print(f"  KV {infra['kv']['kv_cache_tokens']:,} tokens in "
          f"{infra['kv']['kv_blocks']} blocks of {infra['kv']['attention_block_tokens']}"
          f"  ({infra['kv']['kv_bytes_per_token']:,} bytes/token)")
    for q, d in infra["per_question"].items():
        print(f"  {q}: {d['rows']} rows, median {d['median_seconds_per_row']}s/row, "
              f"{d['rows_per_hour']} rows/h")


if __name__ == "__main__":
    main()
