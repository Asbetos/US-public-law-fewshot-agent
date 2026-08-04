"""Tests for the Q6 few-shot prompt kit (prompts/q6_fewshot/)."""
import json
import re
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
KIT_DIR = REPO_DIR / "q6_fewshot"
sys.path.insert(0, str(KIT_DIR))
sys.path.insert(0, str(REPO_DIR))

import build_prompt  # noqa: E402
import extract_examples  # noqa: E402
import run_model  # noqa: E402


def _examples():
    return extract_examples.build_examples(extract_examples.DEFAULT_CSV)


def test_extracts_twelve_examples():
    assert len(_examples()) == 12


def test_labels_balanced_and_binary():
    labels = [ex["label"] for ex in _examples()]
    assert labels.count("Yes") == 6
    assert labels.count("No") == 6
    assert set(labels) == {"Yes", "No"}


def test_ordering_easy_first_then_interleaved():
    ids = [ex["id"] for ex in _examples()]
    assert ids == [
        "no-easy-1", "yes-easy-1",
        "no-ambiguous-2", "yes-ambiguous-2",
        "no-ambiguous-3", "yes-ambiguous-3",
        "no-ambiguous-4", "yes-ambiguous-4",
        "no-ambiguous-5", "yes-ambiguous-5",
        "no-ambiguous-6", "yes-ambiguous-6",
    ]


def test_quoted_span_appears_in_section_text():
    collapse = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
    for ex in _examples():
        assert (
            ex["quoted_span"] in ex["section_text"]
            or collapse(ex["quoted_span"]) in collapse(ex["section_text"])
        ), f"span missing from section for {ex['id']}"


def test_required_fields_nonempty():
    keys = {"id", "volume", "unique_key", "difficulty", "label",
            "section_text", "quoted_span", "temptation", "resolution"}
    for ex in _examples():
        assert set(ex) == keys
        for key in keys - {"volume"}:
            assert isinstance(ex[key], str) and ex[key].strip(), (ex["id"], key)
        assert isinstance(ex["volume"], int)


def test_no_volume_95_leakage():
    assert all(ex["volume"] != 95 for ex in _examples())


def test_examples_json_on_disk_matches_extractor():
    on_disk = json.loads(
        (KIT_DIR / "examples.json").read_text(encoding="utf-8")
    )
    assert on_disk == _examples()


TARGET = "The Secretary shall construct a bridge across the Missouri River."


def _fenced_json_blocks(text):
    return [json.loads(m) for m in
            re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)]


def test_build_messages_shape_and_roles():
    messages = build_prompt.build_messages(TARGET)
    assert len(messages) == 26
    assert messages[0]["role"] == "system"
    for i, msg in enumerate(messages[1:-1]):
        assert msg["role"] == ("user" if i % 2 == 0 else "assistant")
    assert messages[-1]["role"] == "user"
    assert TARGET in messages[-1]["content"]
    assert "DEFINITION" in messages[0]["content"]


def test_assistant_turns_demonstrate_output_contract():
    messages = build_prompt.build_messages(TARGET)
    examples = build_prompt.load_examples()
    assistants = [m for m in messages if m["role"] == "assistant"]
    assert len(assistants) == 12
    for ex, msg in zip(examples, assistants):
        assert msg["content"].startswith("Temptation:")
        assert "Resolution:" in msg["content"]
        blocks = _fenced_json_blocks(msg["content"])
        assert len(blocks) == 1
        payload = blocks[0]
        assert set(payload) == {"label", "quoted_span", "justification"}
        assert payload["label"] == ex["label"]
        assert payload["quoted_span"] == ex["quoted_span"]
        assert payload["justification"].strip()


def test_exemplar_user_turns_carry_full_verbatim_sections():
    messages = build_prompt.build_messages(TARGET)
    examples = build_prompt.load_examples()
    users = [m for m in messages[1:-1] if m["role"] == "user"]
    for ex, msg in zip(examples, users):
        assert ex["section_text"] in msg["content"]


def test_flat_prompt_contains_everything():
    flat = build_prompt.build_flat_prompt(TARGET)
    for k in range(1, 13):
        assert f"### Example {k}" in flat
    assert TARGET in flat
    assert len(_fenced_json_blocks(flat)) == 12


def test_renderers_are_deterministic():
    assert build_prompt.build_messages(TARGET) == build_prompt.build_messages(TARGET)
    assert build_prompt.build_flat_prompt(TARGET) == build_prompt.build_flat_prompt(TARGET)


def test_markdown_file_matches_render():
    on_disk = (KIT_DIR / "q6_fewshot_prompt.md").read_text(encoding="utf-8")
    assert on_disk == build_prompt.render_markdown()


def test_package_import_works():
    import q6_fewshot
    assert q6_fewshot.build_messages(TARGET) == build_prompt.build_messages(TARGET)


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
