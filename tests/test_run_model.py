"""Tests for run_model.py - the OpenAI-compatible client and reply parser."""
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))

import run_model  # noqa: E402


def test_parse_reply_extracts_answer():
    reply = (
        "Temptation: looks like a No.\nResolution: it is construction.\n"
        '```json\n{"label": "Yes", "quoted_span": "shall construct", '
        '"justification": "Builds a structure on land."}\n```'
    )
    parsed = run_model.parse_reply(reply)
    assert parsed["label"] == "Yes"
    assert parsed["quoted_span"] == "shall construct"


def test_parse_reply_uses_last_json_block():
    """Models sometimes draft an answer then revise it."""
    reply = (
        '```json\n{"label": "No", "quoted_span": "", "justification": "draft"}\n```\n'
        "On reflection:\n"
        '```json\n{"label": "Yes", "quoted_span": "x", "justification": "final"}\n```'
    )
    assert run_model.parse_reply(reply)["label"] == "Yes"


def test_parse_reply_rejects_missing_or_invalid_json():
    assert run_model.parse_reply("no code block here") is None
    assert run_model.parse_reply("```json\n{not valid}\n```") is None
    assert run_model.parse_reply(
        '```json\n{"label": "Maybe", "quoted_span": ""}\n```') is None
