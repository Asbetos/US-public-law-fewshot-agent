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


def test_parse_reply_accepts_a_reply_that_is_only_the_json_object():
    """Some prompt layouts make models drop the fence; a reply that is nothing but
    the object is still an answer, but braces inside prose are never read as one."""
    bare = '\n{"label": "No", "quoted_span": "x", "justification": "y", "confidence": 1.0}\n'
    parsed = run_model.parse_reply(bare, confidence=True)
    assert parsed["label"] == "No" and parsed["confidence"] == 1.0
    assert run_model.parse_reply(
        'Answer: {"label": "Yes", "quoted_span": "", "justification": ""}') is None
    assert run_model.parse_reply('{"label": "Yes", "quoted_span": ""} then prose') is None


def test_parse_confidence_accepts_only_finite_unit_interval_numbers():
    assert run_model.parse_confidence(0.85) == (0.85, False)
    assert run_model.parse_confidence(1) == (1.0, False)
    assert run_model.parse_confidence("0.4") == (0.4, False)
    for bad in (None, True, -0.1, 1.5, "high", float("nan"), [0.5], {}):
        assert run_model.parse_confidence(bad) == (None, True), bad


def test_parse_reply_confidence_is_opt_in_and_never_drops_the_label():
    reply = ('```json\n{"label": "Yes", "quoted_span": "x", "justification": "y", '
             '"confidence": 0.9}\n```')
    assert "confidence" not in run_model.parse_reply(reply)
    parsed = run_model.parse_reply(reply, confidence=True)
    assert parsed["confidence"] == 0.9 and parsed["confidence_invalid"] is False

    missing = '```json\n{"label": "No", "quoted_span": "", "justification": ""}\n```'
    parsed = run_model.parse_reply(missing, confidence=True)
    assert parsed["label"] == "No"
    assert parsed["confidence"] is None and parsed["confidence_invalid"] is True

    bad = '```json\n{"label": "No", "quoted_span": "", "justification": "", "confidence": "sure"}\n```'
    parsed = run_model.parse_reply(bad, confidence=True)
    assert parsed["label"] == "No" and parsed["confidence_invalid"] is True
