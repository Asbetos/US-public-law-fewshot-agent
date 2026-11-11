#!/usr/bin/env python3
"""The Claude coder for the Q1 two-coder study: labels sections with the Q1
few-shot kit through the Claude Code SDK (claude-agent-sdk).

Same JSONL contract as eval/run_batch.py (one {"id", "text"} per input line,
one result row per output line, resumable: rows already labelled without an
`error` are skipped, errored rows are retried on the next run).

Why the shape is what it is:
  - the SDK takes one system prompt and user turns only, so the kit is sent in
    its flat form: instruction + definition + 12 worked examples as the system
    prompt (what Claude Code caches), the section as the user turn
    (q1_fewshot.build_flat_messages, byte-identical to build_flat_prompt);
  - tools=[] plus no settings/skills/hooks (setting_sources=[]) make each call a
    pure text classification; a served-model mismatch or any tool-use block
    fails the row rather than passing silently;
  - the SDK's bundled CLI (2.1.169) predates Opus 5.5, so --cli-path defaults to
    the system CLI;
  - on a subscription the SDK reports the 5-hour and 7-day windows on every
    call; the runner logs them per row and pauses until the reset when a window
    is exhausted, so an unattended run needs no babysitting. With
    ANTHROPIC_API_KEY set the same code bills the key (no windows).

    python eval/run_claude.py --input-jsonl results/q1_panel3k/sample.jsonl \
        --output results/q1_panel3k/claude_raw.jsonl --concurrency 2
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import q1_fewshot  # noqa: E402
from run_batch import ensure_trailing_newline, text_hash  # noqa: E402  - shared with the Qwen runner
from run_model import parse_confidence, parse_reply  # noqa: E402  - one parser, one behaviour

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"
# The installed Claude Code CLI, not the SDK's bundled copy (too old for Opus 5.5);
# CLAUDE_CLI overrides the PATH lookup.
DEFAULT_CLI = os.environ.get("CLAUDE_CLI") or shutil.which("claude")
PAUSE_AT_UTILIZATION = 0.97   # stop issuing calls this close to a window's cap
LIMIT_WORDS = ("limit", "rate_limit", "overloaded", "429", "529")
STRUCTURED_TOOL = "StructuredOutput"   # the CLI's own tool behind output_format
VALID_LABELS = {"Yes", "No"}
_print_lock = threading.Lock()

# The kit's answer keys as a JSON schema. Asked for in prose alone, Opus left
# "confidence" out on a share of rows (it copies the 12 three-key examples), so
# the keys are enforced through the SDK's structured output instead; the fenced
# ```json block in the text is the fallback when no structured output arrives.
def answer_schema(confidence: bool = True) -> dict:
    props = {
        "label": {"type": "string", "enum": sorted(VALID_LABELS)},
        "quoted_span": {"type": "string"},
        "justification": {"type": "string"},
    }
    if confidence:
        props["confidence"] = {"type": "number", "minimum": 0, "maximum": 1}
    return {"type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}

# A CLI started from inside a Claude Code session refuses to nest; the batch
# always runs as its own process.
os.environ.pop("CLAUDECODE", None)


def build_prompt(text: str, confidence: bool = True) -> tuple[str, str]:
    """(system prompt, user turn) for one section."""
    system, user = q1_fewshot.build_flat_messages(text, confidence=confidence)
    return system["content"], user["content"]


def prompt_fingerprint(system: str) -> str:
    return hashlib.sha256(system.encode("utf-8")).hexdigest()[:16]


class LimitGate:
    """Shared view of the subscription windows, fed by the SDK's rate-limit events."""

    def __init__(self, pause_at: float = PAUSE_AT_UTILIZATION):
        self.pause_at = pause_at
        self.latest: dict = {}
        self._lock = threading.Lock()

    def update(self, raw: dict) -> None:
        with self._lock:
            self.latest = raw or {}

    def snapshot(self) -> dict:
        """Per-row log fields: utilization of each window and the overall status."""
        with self._lock:
            raw = self.latest
        windows = raw.get("unifiedWindows") or {}
        out = {"limit_status": raw.get("status")}
        for name in ("five_hour", "seven_day"):
            w = windows.get(name) or {}
            out[f"{name}_utilization"] = w.get("utilization")
        return out

    def seconds_to_wait(self, now: float) -> float:
        """0 unless a window is rejected or within pause_at of its cap; then the
        seconds until that window resets (plus a little slack)."""
        with self._lock:
            raw = self.latest
        waits = []
        windows = dict((raw.get("unifiedWindows") or {}))
        if raw.get("status") == "rejected" and raw.get("resetsAt"):
            waits.append(float(raw["resetsAt"]) - now)
        for w in windows.values():
            util, resets = w.get("utilization"), w.get("resetsAt")
            if resets and (w.get("status") == "rejected" or (util or 0) >= self.pause_at):
                waits.append(float(resets) - now)
        # A window whose reset time has passed is stale information, not a reason to wait.
        waits = [w for w in waits if w > 0]
        return max(waits) + 30.0 if waits else 0.0

    def wait_if_needed(self, log=print) -> float:
        waited = 0.0
        while True:
            delay = self.seconds_to_wait(time.time())
            if delay <= 0:
                return waited
            log(f"  usage window exhausted: pausing {delay/60:.0f} min until it resets")
            time.sleep(min(delay, 1800))
            waited += min(delay, 1800)


def _is_limit_error(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in LIMIT_WORDS)


def parse_result(r: dict, confidence: bool) -> dict | None:
    """The answer from one SDK result: the structured output when the schema
    route delivered one, else the kit's fenced json block in the text."""
    so = r.get("structured_output")
    if isinstance(so, dict) and so.get("label") in VALID_LABELS:
        parsed = {"label": so["label"], "quoted_span": str(so.get("quoted_span", "")),
                  "justification": str(so.get("justification", "")), "answer_source": "structured"}
        if confidence:
            parsed["confidence"], parsed["confidence_invalid"] = parse_confidence(so.get("confidence"))
        return parsed
    parsed = parse_reply("\n".join(r["text"]), confidence=confidence)
    if parsed is not None:
        parsed["answer_source"] = "text"
    return parsed


def _confidence_missing(r: dict) -> bool:
    parsed = parse_result(r, confidence=True)
    return bool(parsed) and parsed["confidence_invalid"]


async def ask(system: str, user: str, args, gate: LimitGate) -> dict:
    """One SDK query. Never raises: exceptions are recorded in the result."""
    from claude_agent_sdk import ClaudeAgentOptions, query
    from claude_agent_sdk.types import (AssistantMessage, RateLimitEvent, ResultMessage,
                                        TextBlock, ThinkingBlock, ToolUseBlock)

    stderr_lines: list[str] = []
    opts = ClaudeAgentOptions(
        model=args.model, system_prompt=system, tools=[], setting_sources=[],
        max_turns=1, effort=args.effort, cwd=str(args.cwd), cli_path=args.cli_path,
        output_format={"type": "json_schema", "schema": answer_schema(args.confidence)} if args.schema else None,
        stderr=lambda line: stderr_lines.append(line))   # else a CLI failure says only "check stderr"
    out = {"text": [], "thinking_chars": 0, "served_model": None, "tool_use": False,
           "structured_output": None, "result": None, "exception": None}

    async def run():
        async for m in query(prompt=user, options=opts):
            if isinstance(m, AssistantMessage):
                out["served_model"] = m.model
                for b in m.content:
                    if isinstance(b, TextBlock):
                        out["text"].append(b.text)
                    elif isinstance(b, ThinkingBlock):
                        out["thinking_chars"] += len(b.thinking or "")
                    elif isinstance(b, ToolUseBlock) and b.name != STRUCTURED_TOOL:
                        out["tool_use"] = True
            elif isinstance(m, ResultMessage):
                usage = m.usage or {}
                out["structured_output"] = m.structured_output
                out["result"] = {
                    "is_error": m.is_error, "subtype": m.subtype, "text": m.result,
                    "cost_usd": m.total_cost_usd, "duration_api_ms": m.duration_api_ms,
                    "input_tokens": usage.get("input_tokens"),
                    "cache_read_tokens": usage.get("cache_read_input_tokens"),
                    "cache_write_tokens": usage.get("cache_creation_input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
                }
            elif isinstance(m, RateLimitEvent):
                gate.update(m.rate_limit_info.raw)

    try:
        await asyncio.wait_for(run(), timeout=args.timeout)
    except Exception as exc:  # the SDK raises a bare Exception on error results
        tail = " | ".join(l.strip() for l in stderr_lines[-5:] if l.strip())
        out["exception"] = f"{type(exc).__name__}: {exc}" + (f" [stderr: {tail[:400]}]" if tail else "")
    return out


def label_one(row: dict, args, gate: LimitGate) -> dict:
    """One section -> one result row. Never raises; failures are recorded."""
    system, user = build_prompt(row["text"], confidence=args.confidence)
    result = {"id": row.get("id"), "text_sha256": text_hash(row["text"])}
    started, attempts, limit_waits, notes = time.time(), 0, 0, []
    while True:
        gate.wait_if_needed()
        attempts += 1
        r = asyncio.run(ask(system, user, args, gate))
        res = r["result"] or {}
        error_text = r["exception"] or (res.get("text") if res.get("is_error") else None)
        if error_text and _is_limit_error(error_text) and limit_waits < args.max_limit_waits:
            # The window closed between the last event and this call: wait for
            # the reset the gate knows about, or a fixed interval if it does not.
            limit_waits += 1
            delay = gate.seconds_to_wait(time.time()) or args.limit_sleep
            notes.append(f"limit: {error_text[:120]}")
            with _print_lock:
                print(f"  [{row.get('id')}] usage limit hit; waiting {delay/60:.0f} min", file=sys.stderr)
            time.sleep(delay)
            continue
        tries = attempts - limit_waits          # waiting out a window is not a failed try
        if error_text and tries < args.retries:
            notes.append(f"error: {error_text[:160]}")
            time.sleep(min(2 ** tries, 30))
            continue
        if (not error_text and args.confidence and tries < args.retries
                and _confidence_missing(r)):
            # The model answered but left out the confidence key: one more ask is
            # far cheaper than a row without a confidence score.
            notes.append("confidence key missing")
            continue
        break

    result.update({
        "attempts": attempts, "limit_waits": limit_waits, "attempt_notes": notes,
        "elapsed_s": round(time.time() - started, 2),
        "served_model": r["served_model"],
        **{k: v for k, v in res.items() if k not in ("is_error", "subtype", "text")},
        **gate.snapshot(),
    })
    reply = "\n".join(r["text"])
    if error_text:
        result["error"] = f"request failed after {attempts} tries: {error_text[:300]}"
    elif r["tool_use"]:
        result["error"] = "tool use in reply (fail closed)"
    elif r["served_model"] and not str(r["served_model"]).startswith(args.served_model_prefix):
        result["error"] = f"served model {r['served_model']!r} is not {args.served_model_prefix!r}"
    else:
        parsed = parse_result(r, confidence=args.confidence)
        if parsed is None:
            result["error"] = "no structured output and no valid ```json answer block in reply"
        else:
            result.update(parsed)
    result["raw_reply"] = reply
    return result


def write_manifest(args, system_prompt: str, n_rows: int) -> Path:
    """What produced the rows: model, versions, prompt hash, auth route."""
    try:
        cli_version = subprocess.run([args.cli_path, "--version"], capture_output=True,
                                     text=True, timeout=30).stdout.strip()
    except Exception:
        cli_version = "?"
    try:
        from importlib.metadata import version
        sdk_version = version("claude-agent-sdk")
    except Exception:
        sdk_version = "?"
    manifest = {
        "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "model": args.model, "effort": args.effort, "confidence_key": args.confidence,
        "structured_output_schema": args.schema,
        "auth": "api_key (ANTHROPIC_API_KEY)" if os.environ.get("ANTHROPIC_API_KEY")
                else "claude.ai subscription login",
        "claude_code_cli": cli_version, "claude_agent_sdk": sdk_version,
        "cli_path": args.cli_path, "host": platform.node(),
        "system_prompt_sha256_16": prompt_fingerprint(system_prompt),
        "system_prompt_chars": len(system_prompt),
        "input": str(args.input_jsonl), "rows": n_rows, "concurrency": args.concurrency,
    }
    path = args.output.with_name(args.output.stem + "_manifest.json")
    path.write_text(json.dumps(manifest, indent=1))
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--served-model-prefix", default=None,
                    help="fail a row whose served model does not start with this (default: --model)")
    ap.add_argument("--effort", default=DEFAULT_EFFORT, choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--cli-path", default=DEFAULT_CLI)
    ap.add_argument("--cwd", type=Path, default=None,
                    help="empty working directory for the CLI (default: <output dir>/.claude_cwd)")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=600, help="seconds per call")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--limit-sleep", type=int, default=900,
                    help="seconds to wait after a usage-limit error when no reset time is known")
    ap.add_argument("--max-limit-waits", type=int, default=200)
    ap.add_argument("--no-confidence", dest="confidence", action="store_false",
                    help="do not ask for the extra \"confidence\" key")
    ap.add_argument("--no-schema", dest="schema", action="store_false",
                    help="do not enforce the answer keys through the SDK's structured output; "
                         "rely on the fenced ```json block only")
    ap.add_argument("--limit", type=int, help="stop after N rows (smoke tests)")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    if not args.cli_path:
        ap.error("no `claude` CLI on PATH; pass --cli-path or set CLAUDE_CLI")
    args.served_model_prefix = args.served_model_prefix or args.model
    args.cwd = args.cwd or args.output.parent / ".claude_cwd"
    args.cwd.mkdir(parents=True, exist_ok=True)

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
                    continue
                if "error" not in prev:
                    done.add(prev.get("id"))
        print(f"resuming: {len(done)} rows already labelled", file=sys.stderr)

    todo = [r for r in rows if r.get("id") not in done]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    system_prompt, _ = build_prompt("x", confidence=args.confidence)
    manifest = write_manifest(args, system_prompt, len(rows))
    print(f"claude: {len(todo)} of {len(rows)} rows to label, model {args.model}, effort {args.effort}, "
          f"concurrency {args.concurrency}, confidence={'on' if args.confidence else 'off'}; "
          f"manifest {manifest}", file=sys.stderr)

    gate = LimitGate()
    started, counts = time.time(), {"ok": 0, "err": 0}
    mode = "w" if args.overwrite else "a"
    if mode == "a":
        ensure_trailing_newline(args.output)
    with open(args.output, mode, encoding="utf-8") as out, \
            ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(label_one, row, args, gate) for row in todo]
        for n, future in enumerate(as_completed(futures), 1):
            result = future.result()
            with _print_lock:
                out.write(json.dumps(result, ensure_ascii=False) + "\n")
                out.flush()
                counts["err" if "error" in result else "ok"] += 1
                if n % 10 == 0 or n == len(todo):
                    rate = n / (time.time() - started)
                    eta = (len(todo) - n) / rate if rate else 0
                    snap = gate.snapshot()
                    print(f"  [{n}/{len(todo)}] {rate*3600:.0f} rows/h  ok={counts['ok']} "
                          f"err={counts['err']}  5h={snap.get('five_hour_utilization')} "
                          f"7d={snap.get('seven_day_utilization')}  eta {eta/60:.0f}m", file=sys.stderr)

    total = time.time() - started
    print(f"done in {total/60:.1f}m: {counts['ok']} ok, {counts['err']} errors -> {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
