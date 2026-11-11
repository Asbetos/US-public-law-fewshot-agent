#!/usr/bin/env python3
"""Label statute sections with the Q1 or Q6 few-shot prompt via any
OpenAI-compatible API.

Works with any server exposing /v1/chat/completions: vLLM (`vllm serve ...`),
Ollama (http://localhost:11434/v1), llama.cpp server, or a hosted provider.
Stdlib only - no packages to install.

Single section:
    python run_model.py --question q6 --base-url http://localhost:8000/v1 \\
        --model meta-llama/Llama-3.1-8B-Instruct --section-file section.txt

Batch (JSONL in, JSONL out; one {"id": ..., "text": ...} object per line):
    python run_model.py --question q1 --base-url http://localhost:8000/v1 \\
        --model meta-llama/Llama-3.1-8B-Instruct \\
        --input-jsonl sections.jsonl --output results.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))

import q1_fewshot  # noqa: E402
import q6_fewshot  # noqa: E402

KITS = {"q1": q1_fewshot, "q6": q6_fewshot}

JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
# A reply that is nothing but the JSON object: some prompt layouts make models
# drop the fence (Qwen did on half the flat-prompt replies). Prose around a bare
# object is still rejected, so stray braces in reasoning are never read as answers.
BARE_JSON = re.compile(r"\A\s*(\{.*\})\s*\Z", re.DOTALL)
VALID_LABELS = {"Yes", "No"}


def call_chat(base_url: str, model: str, messages: list[dict],
              api_key: str | None = None, temperature: float = 0.0,
              timeout: int = 600) -> str:
    """POST to an OpenAI-compatible /chat/completions and return the reply text."""
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def parse_confidence(value) -> tuple[float | None, bool]:
    """The optional "confidence" key as (value, invalid): a finite number in
    [0, 1] passes; anything else (absent, bool, text, out of range) is (None, True).
    The label is never discarded over a bad confidence."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None, True
    try:
        c = float(value)
    except (TypeError, ValueError):
        return None, True
    if not math.isfinite(c) or not 0.0 <= c <= 1.0:
        return None, True
    return c, False


def answer_span(reply: str) -> tuple[int, int] | None:
    """Character span of the answer object: the last fenced ```json block, or the
    whole reply when it is a bare JSON object; None when there is neither."""
    last = None
    for last in JSON_BLOCK.finditer(reply):
        pass
    if last is not None:
        return last.span(1)
    bare = BARE_JSON.match(reply)
    return bare.span(1) if bare else None


def parse_reply(reply: str, confidence: bool = False) -> dict | None:
    """Extract the final ```json answer block (or a reply that is only the JSON
    object); None if absent or malformed.

    With confidence=True (the kit built with its confidence flag) the result also
    carries "confidence" and "confidence_invalid"."""
    span = answer_span(reply)
    if span is None:
        return None
    try:
        payload = json.loads(reply[span[0]:span[1]])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("label") not in VALID_LABELS:
        return None
    parsed = {
        "label": payload["label"],
        "quoted_span": payload.get("quoted_span", ""),
        "justification": payload.get("justification", ""),
    }
    if confidence:
        parsed["confidence"], parsed["confidence_invalid"] = parse_confidence(payload.get("confidence"))
    return parsed


def label_section(section_text: str, args: argparse.Namespace) -> dict:
    """Send one section to the model; always returns a result dict."""
    build_messages = KITS[args.question].build_messages
    try:
        reply = call_chat(args.base_url, args.model, build_messages(section_text),
                          api_key=args.api_key, temperature=args.temperature,
                          timeout=args.timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return {"error": f"request failed: {exc}"}
    parsed = parse_reply(reply)
    if parsed is None:
        return {"error": "no valid ```json answer block in reply", "raw_reply": reply}
    parsed["raw_reply"] = reply
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--question", choices=sorted(KITS), default="q6",
                        help="which few-shot kit to use (default: %(default)s)")
    parser.add_argument("--base-url", default="http://localhost:8000/v1",
                        help="OpenAI-compatible API root (default: %(default)s)")
    parser.add_argument("--model", required=True,
                        help="model name as the server knows it")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"),
                        help="bearer token if the server needs one "
                             "(default: $OPENAI_API_KEY; vLLM/Ollama usually need none)")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=600,
                        help="per-request timeout in seconds (default: %(default)s)")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--section-file", type=Path,
                        help="file holding one section's text")
    source.add_argument("--input-jsonl", type=Path,
                        help='JSONL file, one {"id": ..., "text": ...} per line')
    parser.add_argument("--output", type=Path,
                        help="write results here (default: stdout)")
    args = parser.parse_args()

    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        if args.section_file:
            result = label_section(
                args.section_file.read_text(encoding="utf-8"), args)
            json.dump(result, out, ensure_ascii=False, indent=2)
            out.write("\n")
        else:
            with open(args.input_jsonl, encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle if line.strip()]
            for n, row in enumerate(rows, 1):
                result = {"id": row.get("id"), **label_section(row["text"], args)}
                out.write(json.dumps(result, ensure_ascii=False) + "\n")
                out.flush()
                status = result.get("label", "ERROR")
                print(f"[{n}/{len(rows)}] {result['id']}: {status}", file=sys.stderr)
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
