"""Tests for the eval pipeline - the batch runner and the scorer.

The metric code is the part nobody can eyeball: a sign error in MCC or an
off-by-one in the confusion counts would quietly change the headline number, so
these pin every metric against a hand-worked example.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "eval"))

import run_batch  # noqa: E402
import score  # noqa: E402


# --------------------------------------------------------------- run_batch

def _args(**kw):
    import argparse
    base = dict(question="q6", model="m", base_url="http://x/v1", api_key=None,
                temperature=0.0, seed=0, max_tokens=768, max_section_chars=28000,
                timeout=5, retries=1, thinking=False, confidence=False, logprobs=False,
                flat=False)
    base.update(kw)
    return argparse.Namespace(**base)


def test_label_one_parses_a_good_reply(monkeypatch):
    reply = ('Temptation: x\nResolution: y\n```json\n'
             '{"label": "Yes", "quoted_span": "shall construct", "justification": "z"}\n```')
    monkeypatch.setattr(run_batch, "call_chat", lambda a, m: {
        "content": reply, "reasoning": "", "finish_reason": "stop",
        "usage": {"prompt_tokens": 15000, "completion_tokens": 90,
                  "prompt_tokens_details": {"cached_tokens": 14800}}})
    out = run_batch.label_one({"id": "k1", "text": "The Secretary shall construct a dam."}, _args())
    assert out["label"] == "Yes"
    assert out["quoted_span"] == "shall construct"
    assert out["cached_tokens"] == 14800
    assert "error" not in out


def test_label_one_distinguishes_truncation_from_bad_format(monkeypatch):
    """A reply cut off at max_tokens is a capacity bug; a reply that ignored the
    format is a prompt bug. They need different fixes, so they get different errors."""
    monkeypatch.setattr(run_batch, "call_chat", lambda a, m: {
        "content": "Temptation: the section mentions build", "reasoning": "",
        "finish_reason": "length", "usage": {}})
    assert "max_tokens" in run_batch.label_one({"id": "k", "text": "t"}, _args())["error"]

    monkeypatch.setattr(run_batch, "call_chat", lambda a, m: {
        "content": "The answer is Yes.", "reasoning": "",
        "finish_reason": "stop", "usage": {}})
    assert "json" in run_batch.label_one({"id": "k", "text": "t"}, _args())["error"]


def test_label_one_clips_oversized_sections(monkeypatch):
    """Prefix is ~15-17k tokens; the longest sections would overflow the window."""
    seen = {}

    def fake(args, messages):
        seen["chars"] = len(messages[-1]["content"])
        return {"content": '```json\n{"label": "No", "quoted_span": "", "justification": ""}\n```',
                "reasoning": "", "finish_reason": "stop", "usage": {}}

    monkeypatch.setattr(run_batch, "call_chat", fake)
    out = run_batch.label_one({"id": "k", "text": "x" * 50000}, _args(max_section_chars=1000))
    assert out["section_clipped"] is True
    assert seen["chars"] < 2000


def test_label_one_records_failure_after_retries(monkeypatch):
    def boom(args, messages):
        raise OSError("connection refused")
    monkeypatch.setattr(run_batch, "call_chat", boom)
    out = run_batch.label_one({"id": "k", "text": "t"}, _args(retries=1))
    assert "request failed" in out["error"]
    assert out["id"] == "k"


def test_thinking_switch_reaches_the_request_body(monkeypatch):
    bodies = []

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
                               "usage": {}}).encode()

    def fake_urlopen(request, timeout=None):
        bodies.append(json.loads(request.data.decode()))
        return FakeResponse()

    monkeypatch.setattr(run_batch.urllib.request, "urlopen", fake_urlopen)
    run_batch.call_chat(_args(thinking=False), [{"role": "user", "content": "x"}])
    run_batch.call_chat(_args(thinking=True), [{"role": "user", "content": "x"}])
    assert bodies[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert "chat_template_kwargs" not in bodies[1]


def test_logprobs_switch_reaches_the_request_body(monkeypatch):
    bodies = []

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "hi"}, "finish_reason": "stop",
                                            "logprobs": {"content": []}}],
                               "usage": {}}).encode()

    def fake_urlopen(request, timeout=None):
        bodies.append(json.loads(request.data.decode()))
        return FakeResponse()

    monkeypatch.setattr(run_batch.urllib.request, "urlopen", fake_urlopen)
    out = run_batch.call_chat(_args(logprobs=True), [{"role": "user", "content": "x"}])
    assert bodies[0]["logprobs"] is True and bodies[0]["top_logprobs"] == run_batch.TOP_LOGPROBS
    assert out["logprobs"] == {"content": []}
    run_batch.call_chat(_args(logprobs=False), [{"role": "user", "content": "x"}])
    assert "logprobs" not in bodies[1]


# ---------------------------------------------------------- label log-probs

def _toks(pieces, label_idx, chosen_lp, alts):
    """vLLM-shaped logprobs.content: every piece a token; the label token carries
    the alternatives."""
    content = []
    for i, p in enumerate(pieces):
        tok = {"token": p, "logprob": -0.01}
        if i == label_idx:
            tok["logprob"] = chosen_lp
            tok["top_logprobs"] = [{"token": p, "logprob": chosen_lp}] + \
                [{"token": t, "logprob": lp} for t, lp in alts]
        content.append(tok)
    return {"content": content}


REPLY_PIECES = ["Temptation", ":", " x", "\n", "```", "json", "\n", '{"', "label", '":',
                ' "', "Yes", '"', ",", ' "', "quoted_span", '":', ' ""', "}", "\n", "```"]


def test_label_token_probs_reads_the_yes_no_pair():
    lp = _toks(REPLY_PIECES, 11, -0.1, [("No", -2.4), (' "', -9.0)])
    out = run_batch.label_token_probs(lp, "Yes")
    assert out["logprob_yes"] == -0.1 and out["logprob_no"] == -2.4
    assert out["p_yes"] == pytest.approx(1 / (1 + np.exp(-2.4 + 0.1)))
    assert out["p_yes_censored"] is False


def test_label_token_probs_bounds_a_missing_alternative():
    """If "No" is not among the top alternatives, its log-prob can only be below
    the smallest one listed; P(Yes) is then a lower bound and says so."""
    lp = _toks(REPLY_PIECES, 11, -0.01, [('"', -5.0), (" yes", -7.5)])
    out = run_batch.label_token_probs(lp, "Yes")
    assert out["p_yes_censored"] is True
    assert out["logprob_no"] == -7.5
    assert out["p_yes"] > 0.99


def test_label_token_probs_uses_the_last_json_block_and_tolerates_quotes():
    pieces = ['```json\n{"label": "No"}\n```', " revised:\n", '```json\n{"', "label", '":', ' "No',
              '"}', "\n```"]
    lp = _toks(pieces, 5, -0.3, [(' "Yes', -1.4)])
    out = run_batch.label_token_probs(lp, "No")
    assert out["logprob_no"] == -0.3 and out["logprob_yes"] == -1.4
    assert out["p_yes"] < 0.5


def test_label_token_probs_ignores_label_text_outside_the_fenced_block():
    """Prose after the block that mentions "label": "Yes" must not be scored, and
    a token that is not the parsed label is refused rather than mis-scored."""
    pieces = ['```json\n{"', "label", '":', ' "', "No", '"}', "\n```", '\nNote: "label": "', "Yes", '" would apply loosely.']
    lp = _toks(pieces, 4, -0.2, [("Yes", -1.7)])
    lp["content"][8]["logprob"] = -0.5
    lp["content"][8]["top_logprobs"] = [{"token": "Yes", "logprob": -0.5}, {"token": "No", "logprob": -0.9}]
    out = run_batch.label_token_probs(lp, "No")
    assert out["logprob_no"] == -0.2 and out["logprob_yes"] == -1.7
    assert run_batch.label_token_probs(lp, "Yes") == {}          # parsed label must match the token


def test_label_token_probs_reads_a_bare_json_reply():
    """The flat layout makes Qwen drop the fence on some replies; the bare object is
    the answer parse_reply reads, so P(Yes) comes from it too, and prose is not."""
    pieces = ['{"', "label", '":', ' "', "Yes", '",', ' "quoted_span": "x"}']
    out = run_batch.label_token_probs(_toks(pieces, 4, -0.05, [("No", -3.1)]), "Yes")
    assert out["logprob_yes"] == -0.05 and out["logprob_no"] == -3.1
    prose = ['Answer: {"', "label", '":', ' "', "Yes", '"}']
    assert run_batch.label_token_probs(_toks(prose, 4, -0.05, [("No", -3.1)]), "Yes") == {}


def test_label_token_probs_is_empty_without_a_label_token():
    assert run_batch.label_token_probs(None) == {}
    assert run_batch.label_token_probs({"content": []}) == {}
    assert run_batch.label_token_probs(_toks(["no", " json", " here"], 0, -0.1, [])) == {}


def test_ensure_trailing_newline_repairs_a_torn_file(tmp_path):
    p = tmp_path / "raw.jsonl"
    p.write_text('{"id": "a", "label": "No"}\n{"id": "b", "lab')
    run_batch.ensure_trailing_newline(p)
    assert p.read_bytes().endswith(b"\n")
    with open(p, "a") as fh:
        fh.write('{"id": "c", "label": "Yes"}\n')
    rows = [l for l in p.read_text().splitlines() if l]
    assert json.loads(rows[-1])["id"] == "c"               # the new row is intact on its own line
    run_batch.ensure_trailing_newline(tmp_path / "missing.jsonl")   # no file: no-op


def test_text_hash_is_stable_and_short():
    assert run_batch.text_hash("abc") == run_batch.text_hash("abc") and len(run_batch.text_hash("abc")) == 16
    assert run_batch.text_hash("abc") != run_batch.text_hash("abc ")


def test_label_one_records_p_yes_or_flags_its_absence(monkeypatch):
    reply = ('Temptation: x\n```json\n{"label": "Yes", "quoted_span": "", "justification": ""}\n```')
    good = _toks(REPLY_PIECES, 11, -0.2, [("No", -1.8)])
    monkeypatch.setattr(run_batch, "call_chat", lambda a, m: {
        "content": reply, "reasoning": "", "finish_reason": "stop", "usage": {}, "logprobs": good})
    out = run_batch.label_one({"id": "k", "text": "t"}, _args(question="q1", logprobs=True))
    assert out["label"] == "Yes" and 0.5 < out["p_yes"] < 1
    assert out["text_sha256"] == run_batch.text_hash("t")
    monkeypatch.setattr(run_batch, "call_chat", lambda a, m: {
        "content": reply, "reasoning": "", "finish_reason": "stop", "usage": {}, "logprobs": None})
    out = run_batch.label_one({"id": "k", "text": "t"}, _args(question="q1", logprobs=True))
    assert out["p_yes_missing"] is True and "p_yes" not in out


def test_flat_and_confidence_flags_shape_the_prompt(monkeypatch):
    seen = {}

    def fake(args, messages):
        seen["messages"] = messages
        return {"content": '```json\n{"label": "No", "quoted_span": "", "justification": "", '
                           '"confidence": 0.6}\n```',
                "reasoning": "", "finish_reason": "stop", "usage": {}, "logprobs": None}

    monkeypatch.setattr(run_batch, "call_chat", fake)
    out = run_batch.label_one({"id": "k", "text": "SECTION TEXT"},
                              _args(question="q1", flat=True, confidence=True))
    assert [m["role"] for m in seen["messages"]] == ["system", "user"]
    assert '"confidence"' in seen["messages"][0]["content"]
    assert "SECTION TEXT" in seen["messages"][1]["content"]
    assert out["confidence"] == 0.6 and out["confidence_invalid"] is False

    out = run_batch.label_one({"id": "k", "text": "SECTION TEXT"}, _args(question="q1"))
    assert len(seen["messages"]) == 26 and '"confidence"' not in seen["messages"][0]["content"]
    assert "confidence" not in out


# ------------------------------------------------------------------- score

def test_counts_and_metrics_match_a_worked_example():
    gold = np.array(["Yes"] * 10 + ["No"] * 90)
    pred = np.array(["Yes"] * 6 + ["No"] * 4 + ["Yes"] * 5 + ["No"] * 85)
    c = score.counts(gold, pred)
    assert c == {"tp": 6, "fn": 4, "fp": 5, "tn": 85}

    m = score.metrics_from_counts(c)
    assert m["precision_yes"] == pytest.approx(6 / 11)
    assert m["recall_yes"] == pytest.approx(0.6)
    assert m["f1_yes"] == pytest.approx(2 * (6 / 11) * 0.6 / ((6 / 11) + 0.6))
    assert m["accuracy"] == pytest.approx(0.91)
    assert m["specificity"] == pytest.approx(85 / 90)
    assert m["balanced_accuracy"] == pytest.approx((0.6 + 85 / 90) / 2)
    # MCC by the textbook formula, computed independently here.
    expected = (6 * 85 - 5 * 4) / ((11 * 10 * 90 * 89) ** 0.5)
    assert m["mcc"] == pytest.approx(expected)


def test_always_no_baseline_scores_high_accuracy_and_zero_f1():
    """The whole reason accuracy is not the headline on this data."""
    gold = np.array(["Yes"] * 4 + ["No"] * 96)
    m = score.metrics_from_counts(score.counts(gold, np.full(100, "No")))
    assert m["accuracy"] == pytest.approx(0.96)
    assert m["f1_yes"] == 0.0
    assert m["mcc"] == 0.0
    assert m["recall_yes"] == 0.0


def test_perfect_prediction_saturates_every_metric():
    gold = np.array(["Yes"] * 20 + ["No"] * 80)
    m = score.metrics_from_counts(score.counts(gold, gold.copy()))
    for k in ("accuracy", "f1_yes", "mcc", "cohen_kappa", "balanced_accuracy"):
        assert m[k] == pytest.approx(1.0), k


def test_cohen_kappa_is_zero_for_chance_agreement():
    """Predicting the base rate at random earns kappa ~ 0, unlike accuracy."""
    gold = np.array(["Yes"] * 50 + ["No"] * 50)
    pred = np.array((["Yes", "No"] * 25) + (["Yes", "No"] * 25))
    assert score.metrics_from_counts(score.counts(gold, pred))["cohen_kappa"] == pytest.approx(0.0)


def test_bootstrap_ci_brackets_the_point_estimate_and_is_deterministic():
    gold = np.array(["Yes"] * 30 + ["No"] * 170)
    pred = np.array(["Yes"] * 20 + ["No"] * 10 + ["Yes"] * 15 + ["No"] * 155)
    point = score.metrics_from_counts(score.counts(gold, pred))["f1_yes"]
    ci = score.bootstrap_ci(gold, pred)
    assert ci["f1_yes"]["lo"] < point < ci["f1_yes"]["hi"]
    assert score.bootstrap_ci(gold, pred)["mcc"] == ci["mcc"]  # seeded, so reproducible


def test_empty_input_does_not_divide_by_zero():
    m = score.metrics_from_counts({"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    assert m["f1_yes"] == 0.0 and m["mcc"] == 0.0 and m["accuracy"] == 0.0
    assert score.bootstrap_ci(np.array([]), np.array([])) == {}


def test_norm_collapses_the_whitespace_excel_introduces():
    assert score.norm("  shall\n  construct\ta bridge ") == "shall construct a bridge"
    assert score.norm(None) == ""


def test_default_section_clip_fits_the_context_window():
    """Pins the shipped --max-section-chars against the window arithmetic.

    A section clipped to MAX_SECTION_CHARS must still fit alongside the longer
    (Q1) few-shot prefix and the generation budget, even at the worst
    chars-per-token ratio in this corpus - otherwise those rows 400 instead of
    being labelled, which is how the first full run lost a section.
    """
    section_tokens = run_batch.MAX_SECTION_CHARS / run_batch.DENSEST_CHARS_PER_TOKEN
    used = run_batch.Q1_PREFIX_TOKENS + section_tokens + run_batch.DEFAULT_MAX_TOKENS
    assert used < run_batch.CONTEXT_WINDOW, (
        f"worst-case prompt is {used:,.0f} tokens, over the "
        f"{run_batch.CONTEXT_WINDOW:,}-token window")
    # and it should not be needlessly conservative - leave under 2k of slack
    assert run_batch.CONTEXT_WINDOW - used < 2000


# ------------------------------------------------------------- collect_infra

def test_infra_parses_vllm_memory_and_kv_geometry(tmp_path):
    """The memory figures come from vLLM's own log lines, so the patterns that
    read them are load-bearing - a silent miss would put nulls on the dashboard."""
    import collect_infra
    log = tmp_path / "vllm.log"
    log.write_text(
        "INFO [gpu_model_runner.py:5405] Model loading took 18.32 GiB memory and 9.42 seconds\n"
        "INFO [default_loader.py:430] Loading weights took 3.02 seconds\n"
        "INFO [gpu_model_runner.py:6913] Graph capturing finished in 1 secs, took 0.51 GiB\n"
        "INFO Actual usage is 18.51 GiB for consumed memory (weights and non-torch), "
        "0.83 GiB for peak activation, and\n"
        "INFO [gpu_worker.py:563] Available KV cache memory: 2.03 GiB\n"
        "INFO [kv_cache_utils.py:2235] GPU KV cache size: 50,972 tokens\n"
        "INFO [interface.py:911] Setting attention block size to 1568 tokens\n"
        "INFO Avg generation throughput: 53.1 tokens/s, Running: 5 reqs, Waiting: 3 reqs\n"
        "INFO Avg generation throughput: 0.0 tokens/s, Running: 0 reqs, Waiting: 0 reqs\n"
        "INFO Prefix cache hit rate: 82.4%\n")
    got = collect_infra.parse_server_log(log)
    assert got["weights_and_runtime_gib"] == 18.51
    assert got["peak_activation_gib"] == 0.83
    # must not pick up "Model loading took 18.32 GiB" for the graph cost
    assert got["cuda_graphs_gib"] == 0.51
    assert got["kv_cache_gib"] == 2.03
    assert got["kv_cache_tokens"] == 50972
    assert got["attention_block_tokens"] == 1568
    assert got["kv_blocks"] == 50972 // 1568
    assert got["kv_bytes_per_token"] == round(2.03 * 1024**3 / 50972)
    assert got["prefix_cache_hit_rate_pct"] == 82.4
    # idle samples must not drag the concurrency/throughput averages toward zero
    assert got["mean_concurrent_reqs"] == 5.0
    assert got["mean_generation_tok_s"] == 53.1


def test_infra_survives_a_missing_log(tmp_path):
    import collect_infra
    assert collect_infra.parse_server_log(tmp_path / "nope.log") == {}


def test_operator_defined_rates_use_the_specified_denominators():
    """The four custom rates are normalised per-class, not the textbook way.

    TP and FP are both over actual positives; TN and FN both over actual
    negatives. So rate_false_positive is NOT the usual FPR (fp/actual_neg) and
    rate_false_negative is NOT the usual FNR (fn/actual_pos). Pinning it here
    because the two are easy to silently "correct" into the textbook forms.
    """
    m = score.metrics_from_counts({"tp": 168, "fp": 87, "fn": 35, "tn": 1497})
    assert m["actual_positives"] == 203 and m["actual_negatives"] == 1584
    assert m["rate_true_positive"] == pytest.approx(168 / 203)
    assert m["rate_false_positive"] == pytest.approx(87 / 203)
    assert m["rate_true_negative"] == pytest.approx(1497 / 1584)
    assert m["rate_false_negative"] == pytest.approx(35 / 1584)
    # explicitly different from the textbook rates
    assert m["rate_false_positive"] != pytest.approx(87 / 1584)
    assert m["rate_false_negative"] != pytest.approx(35 / 203)
    # TP rate still coincides with recall by definition
    assert m["rate_true_positive"] == pytest.approx(m["recall_yes"])


def test_operator_rates_handle_an_empty_class():
    m = score.metrics_from_counts({"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    for k in ("rate_true_positive", "rate_false_positive",
              "rate_true_negative", "rate_false_negative"):
        assert m[k] == 0.0
