"""Tests for the Q1 two-coder study pieces: the panel sample builder, the Claude
runner's prompt and limit handling, and the comparison statistics."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "eval"))

import make_panel_sample as mps  # noqa: E402
import run_claude  # noqa: E402
from q1_fewshot import build_flat_prompt  # noqa: E402


# ------------------------------------------------------------ sample builder

def _panel():
    rows = []
    # vol 80: three sections, orders 1-3; order 3 single-coded; vol 62 (test) one section
    rows += [(80, 1, "Coder D", "no"), (80, 1, "Coder B", "yes"),
             (80, 2, "Coder D", "no"), (80, 2, "Coder B", "no"), (80, 2, "Coder A", "no"),
             (80, 3, "Coder D", "yes"),
             (80, 4, "Coder D", "yes"), (80, 4, "Coder B", "yes"),
             (62, 1, "Coder D", "no"), (62, 1, "Coder B", "no"),
             (80, 5, "Coder D", ""), (80, 5, "Coder B", "no")]
    return pd.DataFrame(rows, columns=["volume", "order", "coder", "Q1"])


def _training():
    return pd.DataFrame({
        "Volume": [80, 80, 80, 80, 62, 80],
        "OrderCoded": [1, 2, 3, 4, 1, 5],
        "UniqueKey": ["k1", "k2", "k3", "k4", "k62", "k5"],
        "LawIdentifier": ["L1", "L1", "L2", "L2", "L9", "L3"],
        "Text": ["text one", "  “EXEMPLAR   with   odd\n spacing”", "text three", "text four", "test vol", "text five"],
    })


NO_EXEMPLARS = (set(), [])


def test_frame_applies_every_exclusion_and_keeps_coder_labels():
    exemplars = ({"nothing"}, [mps.normalise('"EXEMPLAR with odd spacing"')])
    frame = mps.build_frame(_panel(), _training(), exemplars, log=lambda *a: None)
    assert list(frame["id"]) == ["k1", "k4"]          # k2 exemplar, k3 single-coded, k62 test vol, k5 blank
    k1 = frame.set_index("id").loc["k1"]
    assert k1["coder_labels"] == ["Yes", "No"]        # coders sorted by name: Coder B, Coder D
    assert k1["coders"] == ["Coder B", "Coder D"]
    assert bool(k1["any_yes"]) and not bool(k1["unanimous_yes"])
    assert bool(frame.set_index("id").loc["k4"]["unanimous_yes"])
    assert frame["law"].tolist() == ["L1", "L2"]


def test_exemplars_are_also_matched_by_key_and_by_containment():
    panel, td = _panel(), _training()
    td.loc[td["UniqueKey"] == "k4", "Text"] = "preamble. " + "x" * 300 + " trailer"
    # k1 by unique key; k4 contains a long exemplar; k2's near-duplicate text no longer listed
    exemplars = ({"k1"}, ["x" * 300])
    frame = mps.build_frame(panel, td, exemplars, log=lambda *a: None)
    assert list(frame["id"]) == ["k2"]
    # a short exemplar is never matched by containment (too easy to hit by accident)
    frame = mps.build_frame(panel, td, (set(), ["text"]), log=lambda *a: None)
    assert list(frame["id"]) == ["k1", "k2", "k4"]


def test_empty_and_placeholder_texts_are_dropped():
    panel, td = _panel(), _training()
    td.loc[td["UniqueKey"] == "k1", "Text"] = "\n"
    td.loc[td["UniqueKey"] == "k2", "Text"] = "(blank)"
    frame = mps.build_frame(panel, td, NO_EXEMPLARS, log=lambda *a: None)
    assert list(frame["id"]) == ["k4"]


def test_normalise_collapses_whitespace_and_quotes():
    assert mps.normalise('  “Sec. 3.   (a)\n  The Board”  ') == "Sec. 3. (a) The Board"
    assert mps.normalise(None) == ""


def test_draw_is_reproducible_and_without_replacement():
    frame = pd.DataFrame({"id": [f"k{i}" for i in range(50)], "volume": 80, "order": range(50)})
    a = mps.draw(frame, 10, seed=7)
    b = mps.draw(frame, 10, seed=7)
    assert a["id"].tolist() == b["id"].tolist()
    assert a["id"].is_unique and len(a) == 10
    assert mps.draw(frame, 10, seed=8)["id"].tolist() != a["id"].tolist()


def test_outputs_keep_labels_out_of_the_model_input(tmp_path):
    frame = mps.build_frame(_panel(), _training(), NO_EXEMPLARS, log=lambda *a: None)
    frame.loc[frame["id"] == "k1", "text"] = "x" * 100
    mps.write_outputs(frame, tmp_path, max_chars=40, log=lambda *a: None)
    rows = [json.loads(l) for l in (tmp_path / "sample.jsonl").read_text().splitlines()]
    assert all(set(r) == {"id", "text"} for r in rows)
    assert len(next(r for r in rows if r["id"] == "k1")["text"]) == 40
    meta = pd.read_parquet(tmp_path / "sample_meta.parquet").set_index("id")
    assert bool(meta.loc["k1", "section_clipped"])
    assert meta.loc["k1", "text_sha256"] == mps.text_hash("x" * 40)   # hash of the clipped text
    assert "text" not in meta.columns


# -------------------------------------------------------------- claude runner

def test_claude_prompt_is_the_flat_kit_with_the_confidence_key():
    system, user = run_claude.build_prompt("THE SECTION", confidence=True)
    assert system + "\n\n" + user == build_flat_prompt("THE SECTION", confidence=True)
    assert '"confidence"' in system and "THE SECTION" in user
    assert run_claude.prompt_fingerprint(system) == run_claude.prompt_fingerprint(system)
    assert run_claude.prompt_fingerprint(system) != run_claude.prompt_fingerprint(system + " ")


def test_limit_gate_pauses_only_when_a_window_is_exhausted():
    gate = run_claude.LimitGate(pause_at=0.97)
    now = 1_000.0
    assert gate.seconds_to_wait(now) == 0
    gate.update({"status": "allowed", "unifiedWindows": {
        "five_hour": {"utilization": 0.5, "resetsAt": now + 3600, "status": "allowed"},
        "seven_day": {"utilization": 0.2, "resetsAt": now + 86400, "status": "allowed"}}})
    assert gate.seconds_to_wait(now) == 0
    assert gate.snapshot() == {"limit_status": "allowed", "five_hour_utilization": 0.5,
                               "seven_day_utilization": 0.2}
    gate.update({"status": "allowed", "unifiedWindows": {
        "five_hour": {"utilization": 0.98, "resetsAt": now + 600, "status": "allowed"}}})
    assert gate.seconds_to_wait(now) == pytest.approx(630)
    gate.update({"status": "rejected", "resetsAt": now + 1200, "rateLimitType": "five_hour",
                 "unifiedWindows": {"five_hour": {"utilization": 1.0, "resetsAt": now + 1200,
                                                  "status": "rejected"}}})
    assert gate.seconds_to_wait(now) == pytest.approx(1230)
    assert gate.seconds_to_wait(now + 5000) == 0   # already reset


def _fake_ask(replies):
    """Return successive canned SDK results from label_one's asyncio.run(ask(...))."""
    it = iter(replies)

    async def ask(system, user, args, gate):
        return next(it)
    return ask


def _args(**kw):
    import argparse
    base = dict(model="claude-opus-5-5", served_model_prefix="claude-opus-5-5", effort="medium",
                cwd=Path("/tmp"), cli_path="claude", timeout=5, retries=2, limit_sleep=0,
                max_limit_waits=1, confidence=True, schema=True)
    base.update(kw)
    return argparse.Namespace(**base)


def _ok(reply, model="claude-opus-5-5", tool_use=False, structured=None):
    return {"text": [reply], "thinking_chars": 0, "served_model": model, "tool_use": tool_use,
            "structured_output": structured,
            "result": {"is_error": False, "subtype": "success", "text": None, "cost_usd": 0.01,
                       "duration_api_ms": 100, "input_tokens": 2, "cache_read_tokens": 21697,
                       "cache_write_tokens": 0, "output_tokens": 300, "thinking_tokens": 30},
            "exception": None}


GOOD = ('Temptation: none.\n```json\n{"label": "Yes", "quoted_span": "public comment", '
        '"justification": "comment period", "confidence": 0.9}\n```')


def test_label_one_parses_a_good_reply_and_logs_usage(monkeypatch):
    monkeypatch.setattr(run_claude, "ask", _fake_ask([_ok(GOOD)]))
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(), run_claude.LimitGate())
    assert out["label"] == "Yes" and out["confidence"] == 0.9 and out["justification"] == "comment period"
    assert out["cache_read_tokens"] == 21697 and out["cost_usd"] == 0.01
    assert out["served_model"] == "claude-opus-5-5" and out["attempts"] == 1
    assert "error" not in out


def test_label_one_prefers_structured_output_and_retries_a_missing_confidence(monkeypatch):
    structured = {"label": "No", "quoted_span": "", "justification": "intra-government", "confidence": 0.8}
    monkeypatch.setattr(run_claude, "ask", _fake_ask([_ok(GOOD, structured=structured)]))
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(), run_claude.LimitGate())
    assert out["label"] == "No" and out["confidence"] == 0.8 and out["answer_source"] == "structured"
    assert out["raw_reply"] == GOOD

    no_key = ('```json\n{"label": "No", "quoted_span": "", "justification": "j"}\n```')
    monkeypatch.setattr(run_claude, "ask", _fake_ask([_ok(no_key), _ok(GOOD)]))
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(), run_claude.LimitGate())
    assert out["attempts"] == 2 and out["attempt_notes"] == ["confidence key missing"]
    assert out["label"] == "Yes" and out["confidence"] == 0.9 and out["answer_source"] == "text"

    monkeypatch.setattr(run_claude, "ask", _fake_ask([_ok(no_key), _ok(no_key)]))
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(), run_claude.LimitGate())
    assert out["label"] == "No" and out["confidence"] is None and out["confidence_invalid"] is True
    assert "error" not in out


def test_label_one_fails_closed_on_tool_use_or_wrong_model(monkeypatch):
    monkeypatch.setattr(run_claude, "ask", _fake_ask([_ok(GOOD, tool_use=True)]))
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(), run_claude.LimitGate())
    assert "tool use" in out["error"] and "label" not in out

    monkeypatch.setattr(run_claude, "ask", _fake_ask([_ok(GOOD, model="claude-sonnet-5-5")]))
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(), run_claude.LimitGate())
    assert "served model" in out["error"] and "label" not in out


def test_label_one_waits_through_a_usage_limit_then_retries(monkeypatch):
    limited = {"text": [], "thinking_chars": 0, "served_model": None, "tool_use": False,
               "result": {"is_error": True, "subtype": "error", "text":
                          "You've hit your session limit · resets 3:50pm"},
               "exception": None}
    monkeypatch.setattr(run_claude, "ask", _fake_ask([limited, _ok(GOOD)]))
    monkeypatch.setattr(run_claude.time, "sleep", lambda s: None)
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(), run_claude.LimitGate())
    assert out["label"] == "Yes" and out["limit_waits"] == 1 and out["attempts"] == 2


# ---------------------------------------------------------------- comparison

import compare_models as cm  # noqa: E402


def _unit(key, volume, law, coders, claude, qwen, p_yes=None, cc=0.9, qc=1.0, final=None,
          final_status="agreed"):
    return dict(key=key, volume=volume, order=int(key[1:]), law=law, chars=500, clipped=False,
                coders=coders, coder_names=["A", "B"][:len(coders)], n_coders=len(coders),
                any_yes=any(coders), unanimous_yes=all(coders), unanimous_no=not any(coders),
                final=int(all(coders)) if final is None else final, final_status=final_status,
                claude=claude, qwen=qwen, p_yes=p_yes, claude_conf=cc, qwen_conf=qc,
                claude_just="cj", qwen_just="qj", claude_span="", qwen_span="")


def _units():
    us = []
    for i in range(40):
        lab = 1 if i % 10 == 0 else 0
        us.append(_unit(f"k{i}", 80 + (i % 2), f"L{i // 4}", [lab, lab], lab, lab,
                        p_yes=0.95 if lab else 0.05))
    return us


def test_identical_coders_give_perfect_agreement_and_zero_delta():
    us = _units()
    s = cm.pair_stats(us)
    assert s["n"] == 40 and s["agreement"] == 1.0 and s["kappa"] == pytest.approx(1.0)
    assert s["yes_rate_ratio"] == pytest.approx(1.0)
    v = cm.vs_coders(us, "claude", n_boot=20, seed=0)
    assert v["delta_kappa"] == pytest.approx(0.0) and v["delta_agreement"] == pytest.approx(0.0)
    assert v["hit_rate_unanimous_yes"] == 1.0 and v["false_alarm_rate_unanimous_no"] == 0.0
    ci = cm.cluster_boot(us, cm.pair_stats, n_boot=20, seed=0)
    assert ci["kappa"]["lo"] == pytest.approx(1.0) and ci["kappa"]["hi"] == pytest.approx(1.0)


def test_pair_stats_counts_a_single_disagreement_and_handles_empties():
    us = _units()
    us[1]["qwen"] = 1                      # Qwen alone says Yes once
    s = cm.pair_stats(us)
    assert s["agreement"] == pytest.approx(39 / 40)
    assert s["yes_rate_qwen"] == pytest.approx(5 / 40) and s["yes_rate_claude"] == pytest.approx(4 / 40)
    assert cm.disagreement_table(us)["UniqueKey"].tolist() == ["k1"]
    empty = cm.pair_stats([])
    assert empty["n"] == 0 and np.isnan(empty["kappa"])
    us[2]["claude"] = None                 # a missing label drops the row from complete cases
    assert cm.pair_stats(cm.complete(us, "claude", "qwen"))["n"] == 39


def test_rate_matching_hits_the_target_yes_rate():
    us = _units()
    for i, u in enumerate(us):
        u["p_yes"] = (i + 1) / 40          # distinct scores, so a quantile cut is exact
    rm = cm.rate_matched_qwen(us, target_rate=0.25)
    assert sum(u["qwen_rm"] for u in rm) == 10
    assert all(u["qwen_rm"] == 1 for u in rm if u["p_yes"] > 0.76)
    assert cm.rate_matched_qwen([dict(u, p_yes=None) for u in us], 0.25) == []


def test_confidence_analysis_bins_and_reliability():
    us = _units()
    for u in us[:20]:
        u["claude_conf"] = 0.6             # the lower-confidence half
    us[25]["final"] = 1 - us[25]["claude"]  # one high-confidence miss against the final label
    res = cm.confidence_analysis(us)
    c = res["claude"]
    assert c["n_with_confidence"] == 40 and c["histogram"]["below 0.70"] == 20 and c["histogram"]["0.90-0.94"] == 20
    assert c["match_final_by_bin"]["below 0.70"]["share_matching_final"] == 1.0
    assert c["match_final_by_bin"]["0.90-0.94"]["share_matching_final"] == pytest.approx(19 / 20)
    assert c["match_final_by_bin"]["0.90-0.94"]["disagreements"] == 1
    assert c["mean_when_not_matching_final"] == pytest.approx(0.9)
    assert c["mean_on_agreements"] == pytest.approx(0.75) and c["mean_on_disagreements"] is None
    assert res["qwen_confidence_vs_token_probability"]["n"] == 40


def test_vs_final_counts_hits_false_alarms_precision_and_disputes():
    us = []
    # 10 final Yes (2 disputed): claude catches 8; 30 final No: claude calls 3 Yes
    for i in range(40):
        final = 1 if i < 10 else 0
        claude = 1 if (i < 8 or 10 <= i < 13) else 0
        us.append(_unit(f"k{i}", 80, f"L{i // 2}", [final, final], claude, final, final=final,
                        final_status="disputed" if i in (0, 9) else "agreed"))
    v = cm.vs_final(us, "claude", n_boot=20, seed=0)
    assert v["n"] == 40 and v["n_final_yes"] == 10 and v["n_final_no"] == 30
    assert v["hit_rate"] == pytest.approx(0.8) and v["false_alarm_rate"] == pytest.approx(0.1)
    assert v["precision"] == pytest.approx(8 / 11) and v["n_model_yes"] == 11
    assert v["agreement"] == pytest.approx(35 / 40)
    assert v["table"] == {"1,1": 8.0, "0,1": 2.0, "1,0": 3.0, "0,0": 27.0}
    assert v["n_disputed"] == 2 and v["disputed_model_yes"] == 1
    assert v["yes_rate_final"] == pytest.approx(0.25) and v["yes_rate_claude"] == pytest.approx(11 / 40)
    assert v["ci"]["hit_rate"]["lo"] <= 0.8 <= v["ci"]["hit_rate"]["hi"]
    perfect = cm.vs_final(us, "qwen", n_boot=10, seed=0)
    assert perfect["kappa"] == pytest.approx(1.0) and perfect["false_alarm_rate"] == 0.0


def test_reparse_reads_bare_json_but_never_a_fail_closed_row():
    bare = '{"label": "Yes", "quoted_span": "x", "justification": "y", "confidence": 0.9}'
    df = pd.DataFrame([
        {"id": "a", "error": "no valid ```json answer block in reply", "raw_reply": bare},
        {"id": "b", "error": "tool use in reply (fail closed)", "raw_reply": bare},
        {"id": "c", "error": "truncated before the json block (hit max_tokens)", "raw_reply": "Tempting-but-wrong reading: x"}])
    out = cm.reparse(df).set_index("id")
    assert out.at["a", "label"] == "Yes" and out.at["a", "confidence"] == 0.9 and bool(out.at["a", "reparsed"])
    assert pd.isna(out.at["a", "error"])
    assert out.at["b", "error"].startswith("tool use") and not out.at["b", "reparsed"]
    assert out.at["c", "error"].startswith("truncated") and not out.at["c", "reparsed"]


def test_outcome_names_each_box_and_separates_no_answer_from_not_run():
    u = _unit("k1", 80, "L", [1, 1], claude=None, qwen=0, final=1)
    assert cm.outcome(u, "qwen") == "missed" and cm.outcome(u, "claude") == "not run"
    assert cm.outcome(dict(u, claude_ran=True), "claude") == "no answer"
    assert cm.outcome(dict(u, qwen=1), "qwen") == "caught"
    assert cm.outcome(dict(u, qwen=1, final=0), "qwen") == "false alarm"
    assert cm.outcome(dict(u, final=0), "qwen") == "correct No"
    c = cm.outcome_counts([u, dict(u, qwen=1), dict(u, qwen=1, final=0), dict(u, qwen=None, qwen_ran=True)], "qwen")
    assert (c["caught"], c["missed"], c["false_alarms"], c["no_answer"], c["answered"]) == (1, 1, 1, 1, 3)
    assert c["match"] == pytest.approx(1 / 3)


def test_length_view_cuts_the_whole_sample_into_four_quarters():
    us = [_unit(f"k{i}", 80, f"L{i}", [0, 0], None, 1 if i == 39 else 0, final=0) for i in range(40)]
    for i, u in enumerate(us):
        u["chars"] = 100 + i
    lv = cm.length_view(us, "qwen")
    assert [b["n"] for b in lv["bands"]] == [10, 10, 10, 10]
    assert lv["bands"][3]["false_alarms"] == 1 and lv["bands"][3]["share_disagree"] == pytest.approx(0.1)
    assert sum(b["disagreements"] for b in lv["bands"]) == 1


def test_retry_history_tracks_rescues_unanswered_sections_and_reply_limits(tmp_path):
    meta = pd.DataFrame({"id": ["a", "b", "c"], "final_q1": ["Yes", "No", "Yes"], "chars": [100, 200, 5000]})
    cut = {"error": "truncated before the json block (hit max_tokens)", "finish_reason": "length"}
    rows = [{"id": "a", "label": "Yes", "finish_reason": "stop", "completion_tokens": 200},
            {"id": "b", **cut, "completion_tokens": 768}, {"id": "c", **cut, "completion_tokens": 768},
            {"id": "b", **cut, "completion_tokens": 768}, {"id": "c", **cut, "completion_tokens": 768},
            {"id": "b", "label": "No", "finish_reason": "stop", "completion_tokens": 900},
            {"id": "c", **cut, "completion_tokens": 1536}]
    path = tmp_path / "raw.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    h, rescued = cm.retry_history(path, meta)
    assert h["first_try_failures"] == 2 and h["first_try_failures_final_yes"] == 1
    assert h["rescued_by_attempt"] == {"3": 1} and rescued == ["b"]
    assert h["unanswered"] == 1 and h["unanswered_final_yes"] == 1 and h["unanswered_chars_median"] == 5000
    assert h["reply_limit_by_attempt"] == {"1": 768, "2": 768, "3": 1536}


def test_layout_check_counts_changed_answers_and_reasoning_first():
    us = [_unit(f"k{i}", 80, f"L{i}", [int(i < 6)] * 2, None, int(i < 2), final=int(i < 6)) for i in range(20)]
    ids = [f"k{i}" for i in range(20)]
    flat = pd.DataFrame({"label": ["Yes"] * 5 + ["No", "Yes"] + ["No"] * 13,      # catches 5 of 6, one false alarm
                         "raw_reply": ['{"label": "Yes"}'] * 20, "reparsed": [True] * 3 + [False] * 17}, index=ids)
    chat = pd.DataFrame({"raw_reply": ["Tempting-but-wrong reading: x\n```json\n{}\n```"] * 20}, index=ids)
    lc = cm.layout_check(us, flat, chat, n_boot=20, seed=0)
    assert lc["n"] == 20 and lc["reparsed"] == 3
    assert lc["changes"] == {"final_yes_no_to_yes": 3, "final_yes_yes_to_no": 0,
                             "final_no_no_to_yes": 1, "final_no_yes_to_no": 0}
    assert lc["chat"]["hit_rate"] == pytest.approx(2 / 6) and lc["flat"]["hit_rate"] == pytest.approx(5 / 6)
    assert lc["p_exact"]["final_yes"] == pytest.approx(0.25)          # three one-way changes: 2 / 2**3
    assert lc["reasons_first"] == {"n": 20, "chat": 20, "flat": 0}


def test_p_yes_view_bands_cutoffs_and_rate_matching():
    us = []
    for i in range(20):
        p = 0.999 if i < 3 else (0.995 if i == 10 else 0.0001)        # catches 3 of 4, one false alarm
        us.append(_unit(f"k{i}", 80, f"L{i}", [int(i < 4)] * 2, None, int(p >= 0.5), p_yes=p, final=int(i < 4)))
    pv = cm.p_yes_view(us, n_boot=10, seed=0)
    bands = {b["band"]: b for b in pv["bands"]}
    assert bands["below 0.001"]["n"] == 16 and bands["0.99 and above"]["n"] == 4
    assert bands["0.99 and above"]["final_yes"] == 3
    assert pv["share_decisive"] == 1.0 and pv["n_middle"] == 0
    assert pv["misses"] == 1 and pv["misses_below_0.01"] == 1
    assert pv["cutoffs"]["0.5"]["n_model_yes"] == pv["cutoffs"]["0.01"]["n_model_yes"] == 4
    assert pv["rate_matched_to_final"]["n_model_yes"] == 4 and pv["label_is_p_yes_above_half"] == 1.0
    assert cm.p_yes_view([dict(u, p_yes=None) for u in us], n_boot=5, seed=0) == {}


def test_confidence_triage_counts_what_a_reviewer_would_see():
    us = _units()                                                  # every answer matches the final label
    us[5]["qwen"], us[5]["qwen_conf"] = 1, 0.9                     # a false alarm stated at 0.9
    us[6]["qwen"], us[6]["qwen_conf"] = 1, 1.0                     # a false alarm stated at 1.0
    us[7]["qwen_conf"] = None                                      # no confidence: always reviewed
    t = {x["below"]: x for x in cm.confidence_analysis(us)["qwen"]["triage"]}
    assert t[1.0]["reviewed"] == 2 and t[1.0]["disagreements_caught"] == 1 and t[1.0]["disagreements"] == 2
    assert t[1.0]["false_alarms_caught"] == 1 and t[1.0]["false_alarms"] == 2
    assert t[0.9]["reviewed"] == 1 and t[0.9]["disagreements_caught"] == 0


def test_final_label_table_and_output_export(tmp_path):
    us = _units()
    us[1]["qwen"] = 1                                   # false alarm
    us[2]["qwen"], us[2]["qwen_ran"] = None, True       # asked, never answered
    us[3]["claude"] = None                              # Claude not run here: not a difference
    t = cm.final_label_table(us).set_index("UniqueKey")
    assert set(t.index) == {"k1", "k2"}
    assert t.at["k1", "Qwen outcome"] == "false alarm" and t.at["k2", "Qwen"] == "no answer"
    meta = pd.DataFrame({"id": ["k2", "k1", "k9"]})
    arm = pd.DataFrame({"label": ["No", None], "confidence": [1.0, np.nan], "error": [np.nan, "truncated"],
                        "attempts": [1, 3], "ok": [True, False]}, index=["k1", "k2"])
    assert cm.export_output(arm, meta, tmp_path / "out.jsonl") == 2
    lines = [json.loads(l) for l in (tmp_path / "out.jsonl").read_text().splitlines()]
    assert [l["id"] for l in lines] == ["k2", "k1"]                 # sample order; ids never run are skipped
    assert list(lines[0])[0] == "id" and "ok" not in lines[0] and "confidence" not in lines[0]
    assert lines[0]["error"] == "truncated" and lines[0]["attempts"] == 3 and lines[1]["label"] == "No"


# ------------------------------------------------------------ final labels

import final_labels as fl  # noqa: E402


@pytest.mark.parametrize("answers,expected", [
    (["yes", "yes"], ("Yes", "agreed")),
    (["yes", "yes", "yes"], ("Yes", "agreed")),
    (["no", "no"], ("No", "agreed")),
    (["no", "no", "yes"], ("Yes", "disputed")),       # the team's rule for a split left in the final sheet
    (["yes", "no"], ("Yes", "disputed")),
    (["no"], ("No", "single coder")),
    (["yes"], ("Yes", "single coder")),
    ([], (None, "missing")),
])
def test_final_label_rule(answers, expected):
    assert fl.final_label(answers) == expected


def test_annotate_attaches_final_labels_by_volume_and_order():
    meta = pd.DataFrame({"id": ["a", "b", "c", "d"], "volume": [80, 80, 81, 81], "order": [1, 2, 1, 9],
                         "final_q1": ["stale"] * 4})
    answers = pd.DataFrame([(80, 1, "Coder D", "yes"), (80, 1, "Coder B", "yes"),
                            (80, 2, "Coder D", "no"), (80, 2, "Coder B", "yes"), (80, 2, "Coder A", "no"),
                            (81, 1, "Coder C", "no")], columns=["volume", "order", "coder", "q1"])
    out = fl.annotate(meta, answers).set_index("id")
    assert list(out["final_q1"]) == ["Yes", "Yes", "No", None]
    assert list(out["final_q1_status"]) == ["agreed", "disputed", "single coder", "missing"]
    assert list(out["final_n_coders"]) == [2, 3, 1, 0]
    assert out.loc["a", "final_answers"] == "yes|yes"           # coders sorted by name: Coder B, Coder D
    assert out.loc["b", "final_answers"] == "no|yes|no"         # Coder A, Coder B, Coder D
    s = fl.summary(out.reset_index())
    assert s["final_yes"] == 2 and s["status"]["disputed"] == 1
    assert s["disputed_sections"] == [{"volume": 80, "order": 2, "final_answers": "no|yes|no"}]


def test_run_writes_the_report_from_float_keyed_results(tmp_path):
    """clean() stringifies dict keys for JSON; the report must be built before that."""
    meta = pd.DataFrame({"id": [f"k{i}" for i in range(8)], "volume": [80] * 8, "order": range(8),
                         "law": ["L1", "L1", "L2", "L2", "L3", "L3", "L4", "L4"], "chars": [500] * 8,
                         "section_clipped": [False] * 8, "text_sha256": ["h"] * 8, "n_coders": [2] * 8,
                         "coders": [["A", "B"]] * 8, "coder_labels": [["Yes", "Yes"]] * 2 + [["No", "No"]] * 6,
                         "n_yes": [2, 2, 0, 0, 0, 0, 0, 0], "any_yes": [True] * 2 + [False] * 6,
                         "unanimous_yes": [True] * 2 + [False] * 6})
    meta.to_parquet(tmp_path / "sample_meta.parquet", index=False)
    for name in ("claude", "qwen"):
        with open(tmp_path / f"{name}_raw.jsonl", "w") as fh:
            for i in range(8):
                lab = "Yes" if i < 2 else "No"
                row = {"id": f"k{i}", "text_sha256": "h", "label": lab, "confidence": 0.9 if i % 2 else 0.6,
                       "justification": "j", "quoted_span": "", "cost_usd": 0.01}
                if name == "qwen":
                    row["p_yes"] = 0.95 if lab == "Yes" else 0.05
                fh.write(json.dumps(row) + "\n")
    res = cm.run(tmp_path, n_boot=10, seed=0)
    report = (tmp_path / "REPORT.md").read_text()
    assert "| claude | 8 | 0.75 |" in report           # the median, read from float-keyed quantiles
    assert "claude_yes (n=2): median P(Yes) 0.95" in report
    assert (tmp_path / "comparison.json").exists()
    assert res["vs_coders"]["claude"]["n"] == 8 and res["coverage"]["claude"]["api_equivalent_cost_usd"] == pytest.approx(0.08)


def test_run_reports_against_the_final_label(tmp_path):
    n = 10
    meta = pd.DataFrame({"id": [f"k{i}" for i in range(n)], "volume": [80] * n, "order": range(n),
                         "law": [f"L{i // 2}" for i in range(n)], "chars": [500] * n,
                         "section_clipped": [False] * n, "text_sha256": ["h"] * n, "n_coders": [2] * n,
                         "coders": [["A", "B"]] * n,
                         # first answers: section 2 was split before reconciliation
                         "coder_labels": [["Yes", "Yes"], ["Yes", "Yes"], ["Yes", "No"]] + [["No", "No"]] * 7,
                         "n_yes": [2, 2, 1] + [0] * 7, "any_yes": [True] * 3 + [False] * 7,
                         "unanimous_yes": [True, True] + [False] * 8,
                         "final_q1": ["Yes", "Yes", "Yes"] + ["No"] * 7,
                         "final_q1_status": ["agreed", "agreed", "disputed"] + ["agreed"] * 7})
    meta.to_parquet(tmp_path / "sample_meta.parquet", index=False)
    labels = {"claude": ["Yes", "Yes", "No", "Yes"] + ["No"] * 6, "qwen": ["Yes", "No"] + ["No"] * 8}
    for name, labs in labels.items():
        with open(tmp_path / f"{name}_raw.jsonl", "w") as fh:
            for i, lab in enumerate(labs):
                fh.write(json.dumps({"id": f"k{i}", "text_sha256": "h", "label": lab, "confidence": 0.8,
                                     "justification": "j", "quoted_span": "",
                                     **({"p_yes": 0.9 if lab == "Yes" else 0.1} if name == "qwen" else {})}) + "\n")
    res = cm.run(tmp_path, n_boot=10, seed=0)
    assert res["sample"]["final_yes"] == 3 and res["sample"]["final_disputed"] == 1
    c, q = res["vs_final"]["claude"], res["vs_final"]["qwen"]
    assert c["hit_rate"] == pytest.approx(2 / 3) and c["false_alarm_rate"] == pytest.approx(1 / 7)
    assert q["hit_rate"] == pytest.approx(1 / 3) and q["false_alarm_rate"] == 0.0
    assert c["n_disputed"] == 1 and c["disputed_model_yes"] == 0
    report = (tmp_path / "REPORT.md").read_text()
    assert "## Each model against the final reconciled label" in report
    assert report.index("final reconciled label") < report.index("## Secondary: against the coders' first answers")
    dis = pd.read_csv(tmp_path / "disagreements.csv")
    assert set(dis["final label"]) <= {"Yes", "No"} and "first answers" in dis.columns


def test_run_with_only_qwen_writes_its_views_and_the_layout_check(tmp_path):
    n = 12
    meta = pd.DataFrame({"id": [f"k{i}" for i in range(n)], "volume": [80] * n, "order": range(n),
                         "law": [f"L{i // 2}" for i in range(n)], "chars": [100 * (i + 1) for i in range(n)],
                         "section_clipped": [False] * n, "text_sha256": ["h"] * n, "n_coders": [2] * n,
                         "coders": [["A", "B"]] * n, "coder_labels": [["Yes", "Yes"]] * 3 + [["No", "No"]] * 9,
                         "n_yes": [2] * 3 + [0] * 9, "any_yes": [True] * 3 + [False] * 9,
                         "unanimous_yes": [True] * 3 + [False] * 9,
                         "final_q1": ["Yes"] * 3 + ["No"] * 9, "final_q1_status": ["agreed"] * n})
    meta.to_parquet(tmp_path / "sample_meta.parquet", index=False)
    rows = []
    for i in range(n):
        if i == 5:                                       # fails once, answered on the retry
            rows.insert(0, {"id": "k5", "text_sha256": "h", "error": "truncated before the json block (hit max_tokens)",
                            "finish_reason": "length", "completion_tokens": 768})
        rows.append({"id": f"k{i}", "text_sha256": "h", "label": "Yes" if i in (0, 1, 4) else "No",
                     "confidence": 1.0, "justification": "j", "quoted_span": "", "p_yes": 0.99 if i in (0, 1, 4) else 0.001,
                     "raw_reply": "Tempting-but-wrong reading: x", "finish_reason": "stop", "completion_tokens": 200})
    (tmp_path / "qwen_raw.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    bare = json.dumps({"label": "Yes", "quoted_span": "", "justification": "j", "confidence": 0.9})
    flat = [{"id": f"k{i}", "text_sha256": "h", "error": "no valid ```json answer block in reply", "raw_reply": bare}
            if i in (0, 2) else {"id": f"k{i}", "text_sha256": "h", "label": "No", "raw_reply": "```json\n{}\n```"}
            for i in range(n)]
    (tmp_path / "qwen_flat300.jsonl").write_text("".join(json.dumps(r) + "\n" for r in flat))
    res = cm.run(tmp_path, n_boot=10, seed=0)
    assert res["model_vs_model"]["n"] == 0 and set(res["vs_final"]) == {"qwen"}
    assert res["retry_history"]["qwen"]["rescued"] == 1 and res["rescued_answers"]["qwen"]["n"] == 1
    lc = res["qwen_layout_check"]
    assert lc["reparsed"] == 2 and lc["changes"]["final_yes_no_to_yes"] == 1     # k2: missed in chat, caught in one block
    assert len(res["length_view"]["qwen"]["bands"]) == 4
    assert (tmp_path / "qwen_output.jsonl").exists() and not (tmp_path / "claude_output.jsonl").exists()
    assert len((tmp_path / "qwen_output.jsonl").read_text().splitlines()) == n
    report = (tmp_path / "REPORT.md").read_text()
    assert "Waiting for both runs." in report and "## Prompt-layout check" in report
    assert pd.read_csv(tmp_path / "final_label_disagreements.csv")["UniqueKey"].tolist() == ["k2", "k4"]


def test_run_refuses_results_labelled_on_a_different_text(tmp_path):
    meta = pd.DataFrame({"id": ["k0"], "volume": [80], "order": [0], "law": ["L1"], "chars": [5],
                         "section_clipped": [False], "text_sha256": ["hash-of-new-text"], "n_coders": [2],
                         "coders": [["A", "B"]], "coder_labels": [["No", "No"]], "n_yes": [0],
                         "any_yes": [False], "unanimous_yes": [False]})
    meta.to_parquet(tmp_path / "sample_meta.parquet", index=False)
    (tmp_path / "qwen_raw.jsonl").write_text(json.dumps({"id": "k0", "text_sha256": "hash-of-old-text",
                                                          "label": "No", "justification": "", "quoted_span": ""}) + "\n")
    with pytest.raises(SystemExit):
        cm.run(tmp_path, n_boot=5, seed=0)


def test_two_coder_sheet_uses_dots_for_missing_labels():
    meta = pd.DataFrame({"id": ["k1", "k2"], "volume": [80, 80], "order": [1, 2], "law": ["L", "L"],
                         "chars": [10, 10], "section_clipped": [False, False], "n_coders": [2, 2],
                         "coders": [["A", "B"], ["A", "B"]], "coder_labels": [["Yes", "No"], ["No", "No"]],
                         "n_yes": [1, 0], "any_yes": [True, False], "unanimous_yes": [False, False]})
    claude = pd.DataFrame({"label": ["Yes"], "confidence": [0.8], "justification": ["because"],
                           "quoted_span": ["x"], "p_yes": [np.nan], "error": [None]}, index=["k1"])
    qwen = pd.DataFrame({"label": ["No", None], "confidence": [1.0, np.nan], "justification": ["q", ""],
                         "quoted_span": ["", ""], "p_yes": [0.01, np.nan], "error": [None, "boom"]},
                        index=["k1", "k2"])
    sheet = cm.two_coder_sheet(meta, {"claude": claude, "qwen": qwen})
    assert list(sheet.columns)[:6] == ["Volume", "unique key", "UniqueKey", "question", "Claude", "Qwen"]
    assert sheet.loc[0, "Claude"] == "Yes" and sheet.loc[0, "Qwen"] == "No"
    assert sheet.loc[1, "Claude"] == "." and sheet.loc[1, "Qwen"] == "."
    assert sheet.loc[0, "Claude reasoning"] == "because" and sheet.loc[0, "Qwen P(Yes)"] == 0.01
    assert "coder labels" not in sheet.columns   # models only, as decided


def test_label_one_records_other_errors_after_retries(monkeypatch):
    boom = {"text": [], "thinking_chars": 0, "served_model": None, "tool_use": False,
            "result": None, "exception": "Exception: CLI crashed"}
    monkeypatch.setattr(run_claude, "ask", _fake_ask([boom, boom, boom]))
    monkeypatch.setattr(run_claude.time, "sleep", lambda s: None)
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(retries=2), run_claude.LimitGate())
    assert out["attempts"] == 2 and "CLI crashed" in out["error"]
    assert out["text_sha256"] == run_claude.text_hash("t")


def test_limit_waits_do_not_consume_the_retry_budget(monkeypatch):
    limited = {"text": [], "thinking_chars": 0, "served_model": None, "tool_use": False,
               "result": {"is_error": True, "subtype": "error", "text": "You've hit your session limit"},
               "exception": None}
    boom = dict(limited, result=None, exception="Exception: transient")
    monkeypatch.setattr(run_claude, "ask", _fake_ask([limited, boom, _ok(GOOD)]))
    monkeypatch.setattr(run_claude.time, "sleep", lambda s: None)
    out = run_claude.label_one({"id": "a", "text": "t"}, _args(retries=2, max_limit_waits=5), run_claude.LimitGate())
    assert out["label"] == "Yes" and out["attempts"] == 3 and out["limit_waits"] == 1


def test_answer_schema_follows_the_confidence_flag():
    assert "confidence" in run_claude.answer_schema(True)["required"]
    assert "confidence" not in run_claude.answer_schema(False)["properties"]
    assert run_claude.answer_schema(False)["required"] == ["label", "quoted_span", "justification"]
