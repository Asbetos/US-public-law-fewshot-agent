#!/usr/bin/env python3
"""Capture what actually produced the numbers, for the dashboard footer.

A metrics file without the serving config is not reproducible - quantisation and
KV-cache dtype both move the answers.

    python eval/write_run_meta.py --out results/run_meta.json
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:
        return ""


def server_args(log: Path) -> dict:
    if not log.exists():
        return {}
    m = re.search(r"non-default args: (\{.*\})", log.read_text(errors="ignore"))
    if not m:
        return {}
    try:
        return json.loads(m.group(1).replace("'", '"').replace("True", "true")
                          .replace("False", "false").replace("None", "null"))
    except Exception:
        return {}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO / "results" / "run_meta.json")
    ap.add_argument("--server-log", type=Path,
                    default=Path("/groups/brooksgrp/citizen_voice/models/vllm_server.log"))
    ap.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model-repo", default="cyankiwi/Qwen3.6-27B-AWQ-INT4")
    args = ap.parse_args()

    sargs = server_args(args.server_log)
    served = "?"
    try:
        with urllib.request.urlopen(args.base_url.rstrip("/") + "/models", timeout=10) as r:
            served = json.loads(r.read())["data"][0]["id"]
    except Exception:
        pass

    gpu = sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader")
    vllm_v = sh(f"{REPO}/.venv-vllm/bin/python -c \"import vllm;print(vllm.__version__)\"")
    torch_v = sh(f"{REPO}/.venv-vllm/bin/python -c \"import torch;print(torch.__version__)\"")
    leak = sh(f"/groups/brooksgrp/citizen_voice/workspace/.venv/bin/python "
              f"{REPO}/verify_no_test_leakage.py")
    clean = "RESULT: clean" in leak

    meta = {
        "model_short": "Qwen3.6-27B AWQ-4bit",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "leakage_gate": {
            "clean": clean,
            "detail": ("verify_no_test_leakage.py exits 0: no few-shot exemplar appears in the "
                       "test set by volume, unique key, or text. Three colliding rows were "
                       "removed from the test set upstream (1,794 -> 1,791 rows)."
                       if clean else
                       "verify_no_test_leakage.py reports leakage - the scores below are "
                       "optimistic. Fix before quoting these numbers."),
        },
        "display": [
            ["Model", f"{args.model_repo} (AWQ 4-bit, group size 32)"],
            ["Base model", "Qwen/Qwen3.6-27B - 64 layers, hybrid linear/full attention, 248k vocab"],
            ["Served as", served],
            ["Sampling", "temperature 0, seed 0, max_tokens "
                         f"{sargs.get('max_tokens', 768)}, thinking mode off"],
            ["Serving", f"vLLM {vllm_v} · torch {torch_v} · fp8 KV cache · "
                        f"max_model_len {sargs.get('max_model_len', '?')} · "
                        f"max_num_seqs {sargs.get('max_num_seqs', '?')} · prefix caching on"],
            ["GPU", gpu or "unknown"],
            ["Prompt", "12 SME-authored worked examples per question, from the repo's "
                       "q1_fewshot / q6_fewshot kits (unmodified)"],
            ["Test set", "data/fewshot_q1q6 held-out split - volumes 62, 91, 132"],
            ["Leakage gate", "clean (exit 0)" if clean else "NOT CLEAN"],
            ["Host", platform.node()],
            ["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(meta, indent=2))
    print(f"wrote {args.out}  (leakage gate {'clean' if clean else 'NOT CLEAN'})")


if __name__ == "__main__":
    main()
