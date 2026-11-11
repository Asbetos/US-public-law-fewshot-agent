#!/usr/bin/env python3
"""Concurrent few-shot labelling against an OpenAI-compatible server.

run_model.py in the repo root is the reference single-section CLI: it sends one
blocking request at a time, which forfeits the server's continuous batching. At
1,791 rows x 2 questions that is the difference between hours and a day, so this
runner keeps N requests in flight and is resumable.

Reuses the repo's own prompt kits and reply parser - the prompt sent here is
byte-identical to what run_model.py sends, plus sampling controls it does not
expose (max_tokens, and the chat-template switch that turns Qwen's thinking mode
off).

    python eval/run_batch.py --question q6 --input-jsonl results/q6/test.jsonl \
        --output results/q6/raw.jsonl --model qwen3.6-27b-awq --concurrency 8
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import q1_fewshot  # noqa: E402
import q6_fewshot  # noqa: E402
from run_model import answer_span, parse_reply  # noqa: E402  - one parser, one behaviour

KITS = {"q1": q1_fewshot, "q6": q6_fewshot}

# Largest section that always fits the 32,768-token window. The Q1 prefix is
# ~13,975 tokens and max_tokens is 768, leaving ~17,500 for the section; the
# densest statute text here tokenizes at 1.09 chars/token (one 32,767-char
# section is 29,983 tokens - tables of figures and citations, not prose).
# Sizing off an average ratio silently 400s on exactly those rows.
CONTEXT_WINDOW = 32768
Q1_PREFIX_TOKENS = 13975      # measured; q6's is ~12,217
DEFAULT_MAX_TOKENS = 768
DENSEST_CHARS_PER_TOKEN = 1.09
MAX_SECTION_CHARS = 19000     # clips 9 of 1,791 test rows, each flagged section_clipped
TOP_LOGPROBS = 5              # alternatives returned per generated token with --logprobs
LABEL_RE = re.compile(r'"label"\s*:\s*"(Yes|No)"')
_print_lock = threading.Lock()


def text_hash(text: str) -> str:
    """Short sha256 of the exact text a model was shown; echoed into every result
    row so results can always be tied to the input they were labelled on."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def ensure_trailing_newline(path: Path) -> None:
    """A run killed mid-write leaves a torn last line; appending straight after it
    would glue the next row onto it and lose both. Terminate it first."""
    if not path.exists() or path.stat().st_size == 0:
        return
    with open(path, "rb+") as fh:
        fh.seek(-1, os.SEEK_END)
        if fh.read(1) != b"\n":
            fh.write(b"\n")


def _norm_label(token: str) -> str:
    return (token or "").strip().strip('"')


def label_token_probs(logprobs: dict | None, expected_label: str | None = None) -> dict:
    """P(Yes) at the label token of the final json block, from vLLM's per-token
    log-probabilities (chat `logprobs: true` + `top_logprobs`).

    The generated text is rebuilt from the token pieces so the label value can be
    located by character offset, whatever the tokenizer did around the quotes.
    Only the answer object parse_reply reads is searched (the last fenced json
    block, or the bare object when the model dropped the fence), and the token
    found there must be the label that was parsed. If the other label is absent
    from the top alternatives its log-prob is bounded above by the smallest one
    listed, and `p_yes_censored` says so. Returns {} when there is no usable label
    token (the caller flags the row).
    """
    toks = (logprobs or {}).get("content") or []
    pieces = [t.get("token") or "" for t in toks]
    text = "".join(pieces)
    span = answer_span(text)                   # the same object parse_reply reads
    if span is None:
        return {}
    match = None
    for match in LABEL_RE.finditer(text, span[0], span[1]):
        pass
    if match is None:
        return {}
    target, pos, chosen = match.start(1), 0, None
    for tok, piece in zip(toks, pieces):
        if pos <= target < pos + len(piece):
            chosen = tok
            break
        pos += len(piece)
    if chosen is None or _norm_label(chosen.get("token")) not in ("Yes", "No"):
        return {}
    if expected_label and _norm_label(chosen.get("token")) != expected_label:
        return {}
    cands = [chosen] + list(chosen.get("top_logprobs") or [])
    lp: dict[str, float] = {}
    for c in cands:
        name = _norm_label(c.get("token"))
        if name in ("Yes", "No") and c.get("logprob") is not None:
            lp[name] = max(lp.get(name, -math.inf), float(c["logprob"]))
    if not lp:
        return {}
    censored = False
    floor = min(float(c["logprob"]) for c in cands if c.get("logprob") is not None)
    for name in ("Yes", "No"):
        if name not in lp:
            lp[name], censored = floor, True
    p_yes = 1.0 / (1.0 + math.exp(lp["No"] - lp["Yes"]))
    return {"p_yes": p_yes, "logprob_yes": lp["Yes"], "logprob_no": lp["No"],
            "p_yes_censored": censored}


def call_chat(args, messages: list[dict]) -> dict:
    """POST to /chat/completions, returning content + finish_reason + usage."""
    body = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "seed": args.seed,
    }
    if not args.thinking:
        # Qwen3.x chat templates open a bare <think> unless told otherwise; left
        # on, every reply burns reasoning tokens before reaching the json block.
        body["chat_template_kwargs"] = {"enable_thinking": False}
    if args.logprobs:
        # Output log-probs leave the prefix cache alone (only prompt_logprobs
        # would switch it off).
        body["logprobs"] = True
        body["top_logprobs"] = TOP_LOGPROBS
    request = urllib.request.Request(
        args.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {args.api_key}"} if args.api_key else {})},
    )
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    choice = data["choices"][0]
    return {
        "content": choice["message"]["content"] or "",
        "reasoning": choice["message"].get("reasoning_content") or "",
        "finish_reason": choice.get("finish_reason", ""),
        "usage": data.get("usage", {}),
        "logprobs": choice.get("logprobs"),
    }


def build_prompt_messages(kit, text: str, args) -> list[dict]:
    """The kit's chat messages, or its flat (system + section) form with --flat;
    --confidence asks for the extra output key (q1 kit only)."""
    kwargs = {"confidence": True} if args.confidence else {}
    if args.flat:
        return kit.build_flat_messages(text, **kwargs)
    return kit.build_messages(text, **kwargs)


def label_one(row: dict, args) -> dict:
    """One section -> one result row. Never raises; failures are recorded."""
    kit = KITS[args.question]
    text = row["text"]
    result = {"id": row.get("id"), "text_sha256": text_hash(text)}

    if args.max_section_chars and len(text) > args.max_section_chars:
        # Guard the context window: prefix is ~15-17k tokens and the longest
        # sections hit Excel's 32,767-char cap (~9k tokens more).
        text = text[: args.max_section_chars]
        result["section_clipped"] = True

    started = time.time()
    for attempt in range(1, args.retries + 1):
        try:
            reply = call_chat(args, build_prompt_messages(kit, text, args))
            break
        except Exception as exc:
            # Deliberately broad: this loop runs for hours, and a single
            # malformed response body must not take the whole run down. Every
            # failure is recorded per row and retried on the next invocation.
            if attempt == args.retries:
                return {**result, "error": f"request failed after {attempt} tries: "
                                           f"{type(exc).__name__}: {exc}",
                        "elapsed_s": round(time.time() - started, 2)}
            time.sleep(min(2 ** attempt, 30))

    usage = reply["usage"]
    result.update({
        "finish_reason": reply["finish_reason"],
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
        "elapsed_s": round(time.time() - started, 2),
    })

    parsed = parse_reply(reply["content"], confidence=args.confidence)
    if parsed is None:
        # Distinguish "ran out of room mid-answer" from "ignored the format".
        result["error"] = ("truncated before the json block (hit max_tokens)"
                           if reply["finish_reason"] == "length"
                           else "no valid ```json answer block in reply")
    else:
        result.update(parsed)
        if args.logprobs:
            probs = label_token_probs(reply.get("logprobs"), parsed["label"])
            if probs:
                result.update(probs)
            else:
                result["p_yes_missing"] = True
    result["raw_reply"] = reply["content"]
    if reply["reasoning"]:
        result["reasoning"] = reply["reasoning"]
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--question", choices=sorted(KITS), required=True)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"))
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--max-section-chars", type=int, default=MAX_SECTION_CHARS)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--limit", type=int, help="stop after N rows (smoke tests)")
    ap.add_argument("--thinking", action="store_true",
                    help="leave Qwen's reasoning mode on (much slower)")
    ap.add_argument("--confidence", action="store_true",
                    help="ask for the extra 0-1 \"confidence\" key (q1 kit only)")
    ap.add_argument("--logprobs", action="store_true",
                    help="record P(Yes) at the label token from the server's log-probs")
    ap.add_argument("--flat", action="store_true",
                    help="send the kit as system prompt + section (the Claude SDK form) "
                         "instead of exemplar chat turns (q1 kit only)")
    ap.add_argument("--overwrite", action="store_true",
                    help="ignore any existing output and start over")
    args = ap.parse_args()
    if (args.confidence or args.flat) and args.question != "q1":
        ap.error("--confidence and --flat are implemented for the q1 kit only")

    with open(args.input_jsonl, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    if args.limit:
        rows = rows[: args.limit]

    done: set = set()
    if args.output.exists() and not args.overwrite:
        with open(args.output, encoding="utf-8") as fh:
            for line in fh:
                try:
                    prev = json.loads(line)
                except json.JSONDecodeError:
                    continue  # torn final line from an interrupted run
                if "error" not in prev:  # retry anything that failed
                    done.add(prev.get("id"))
        print(f"resuming: {len(done)} rows already labelled", file=sys.stderr)

    todo = [r for r in rows if r.get("id") not in done]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.overwrite else "a"
    if mode == "a":
        ensure_trailing_newline(args.output)
    print(f"{args.question}: {len(todo)} of {len(rows)} rows to label, "
          f"concurrency {args.concurrency}, thinking={'on' if args.thinking else 'off'}, "
          f"flat={'on' if args.flat else 'off'}, confidence={'on' if args.confidence else 'off'}, "
          f"logprobs={'on' if args.logprobs else 'off'}",
          file=sys.stderr)

    started, counts = time.time(), {"ok": 0, "err": 0}
    # as_completed, not pool.map: map yields in submission order, so one slow
    # section would hold back the checkpointing of every row behind it - and on a
    # multi-hour run the checkpoint is what makes an interruption survivable.
    with open(args.output, mode, encoding="utf-8") as out, \
            ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(label_one, row, args) for row in todo]
        for n, future in enumerate(as_completed(futures), 1):
            result = future.result()
            with _print_lock:
                out.write(json.dumps(result, ensure_ascii=False) + "\n")
                out.flush()
                counts["err" if "error" in result else "ok"] += 1
                if n % 10 == 0 or n == len(todo):
                    rate = n / (time.time() - started)
                    eta = (len(todo) - n) / rate if rate else 0
                    print(f"  [{n}/{len(todo)}] {rate:.2f} rows/s  "
                          f"ok={counts['ok']} err={counts['err']}  "
                          f"eta {eta/60:.0f}m", file=sys.stderr)

    total = time.time() - started
    print(f"done in {total/60:.1f}m: {counts['ok']} ok, {counts['err']} errors -> {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
