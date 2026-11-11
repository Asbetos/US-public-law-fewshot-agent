#!/bin/bash
# Serve the AWQ-4bit Qwen3.6-27B on the single L4 (23.3 GB usable).
#
# The binding constraint is VRAM: the 4-bit weights are ~20 GB, not the naive
# 13.5 GB, because Qwen3.6-27B has a 248k vocab with untied embeddings, a vision
# tower and an MTP head that quantizers leave in bf16. Everything below buys back
# room for the KV cache:
#   --language-model-only  drops the vision tower we never use (text-only task)
#   --kv-cache-dtype fp8   halves KV; 16 of the 64 layers are full attention at
#                          4 kv-heads x 256 head_dim = 64 KB/token at bf16
#   --max-num-seqs         caps concurrent sequences so KV cannot be oversubscribed
#
# --enable-prefix-caching must be passed EXPLICITLY: vLLM defaults it OFF for this
# hybrid linear-attention model. Without it the run is ~10x slower for two
# compounding reasons - every request re-prefills the identical ~12k-token few-shot
# prefix, AND the mamba page size forces a 1,568-token attention block, so a 12k
# prompt claims 8 of the ~28 available blocks and only 2 requests fit at once.
# Cached, those prefix blocks are shared by every request rather than copied.
set -euo pipefail
cd "$(dirname "$0")/.."

# vLLM JIT-compiles some kernels at startup and shells out to `ninja`, so the
# venv's bin must be on PATH - calling .venv-vllm/bin/vllm directly is not enough.
export PATH="$PWD/.venv-vllm/bin:$PATH"

MODEL="${MODEL:-/groups/brooksgrp/citizen_voice/models/cyankiwi__Qwen3.6-27B-AWQ-INT4}"
PORT="${PORT:-8000}"
MAX_LEN="${MAX_LEN:-32768}"
GPU_UTIL="${GPU_UTIL:-0.97}"
MAX_SEQS="${MAX_SEQS:-8}"
EXTRA="${EXTRA:-}"

echo "model:    $MODEL"
echo "max_len:  $MAX_LEN   gpu_util: $GPU_UTIL   max_seqs: $MAX_SEQS   extra: $EXTRA"

exec .venv-vllm/bin/vllm serve "$MODEL" \
    --served-model-name qwen3.6-27b-awq \
    --host 127.0.0.1 --port "$PORT" \
    --language-model-only \
    --max-model-len "$MAX_LEN" \
    --gpu-memory-utilization "$GPU_UTIL" \
    --kv-cache-dtype fp8 \
    --enable-prefix-caching \
    --max-num-seqs "$MAX_SEQS" \
    $EXTRA

# Measured on this box (single L4, 23.0 GB), cyankiwi AWQ-INT4, prefix caching on:
#   gpu_util 0.95 -> 1.59 GiB KV / 40,049 tokens -> 4-5 concurrent, ~0.12 rows/s
#   gpu_util 0.97 -> 2.03 GiB KV / 50,972 tokens   <- the value used
# The smaller Alennnndy AWQ-4bit build was tried and is WORSE here: 17.4 GiB of
# weights but only 0.96 GiB of KV, too little to serve one max-length request.
# Always relaunch from a verified-idle GPU (nvidia-smi ~164 MiB) - profiling
# against memory the previous engine has not yet released produces bogus,
# sometimes negative, KV numbers.
