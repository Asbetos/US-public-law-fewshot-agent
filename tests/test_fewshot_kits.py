"""Tests for the few-shot prompt kits (q1_fewshot/, q6_fewshot/).

The two kits implement the same contract, so the bulk of the suite is
parameterised over both. Kit-specific expectations - the question wording and
the definition rules taken from the SME-approved prompt documents - live in
their own tests at the bottom.
"""
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))

KITS = ["q1_fewshot", "q6_fewshot"]
TARGET = "The Secretary shall construct a bridge across the Missouri River."

EXPECTED_IDS = [
    "no-easy-1", "yes-easy-1",
    "no-ambiguous-2", "yes-ambiguous-2",
    "no-ambiguous-3", "yes-ambiguous-3",
    "no-ambiguous-4", "yes-ambiguous-4",
    "no-ambiguous-5", "yes-ambiguous-5",
    "no-ambiguous-6", "yes-ambiguous-6",
]


@pytest.fixture(params=KITS)
def kit(request):
    """One few-shot kit, imported as a package (never as loose modules -
    both kits define build_prompt/prompt_parts/extract_examples)."""
    name = request.param
    return SimpleNamespace(
        name=name,
        dir=REPO_DIR / name,
        pkg=importlib.import_module(name),
        extract=importlib.import_module(f"{name}.extract_examples"),
        build=importlib.import_module(f"{name}.build_prompt"),
        parts=importlib.import_module(f"{name}.prompt_parts"),
    )


def _collapse(text):
    return re.sub(r"\s+", " ", text).strip()


def _fenced_json_blocks(text):
    return [json.loads(m) for m in
            re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)]


# --------------------------- exemplar data ---------------------------------

def test_extracts_twelve_examples(kit):
    assert len(kit.extract.build_examples(kit.extract.DEFAULT_CSV)) == 12


def test_labels_balanced_and_binary(kit):
    labels = [e["label"] for e in kit.extract.build_examples(kit.extract.DEFAULT_CSV)]
    assert labels.count("Yes") == 6
    assert labels.count("No") == 6


def test_ordering_easy_first_then_interleaved(kit):
    ids = [e["id"] for e in kit.extract.build_examples(kit.extract.DEFAULT_CSV)]
    assert ids == EXPECTED_IDS


def test_quoted_span_appears_in_section_text(kit):
    for ex in kit.extract.build_examples(kit.extract.DEFAULT_CSV):
        assert (ex["quoted_span"] in ex["section_text"]
                or _collapse(ex["quoted_span"]) in _collapse(ex["section_text"])), ex["id"]


def test_required_fields_nonempty(kit):
    keys = {"id", "volume", "unique_key", "difficulty", "label",
            "section_text", "quoted_span", "temptation", "resolution"}
    for ex in kit.extract.build_examples(kit.extract.DEFAULT_CSV):
        assert set(ex) == keys
        for key in keys - {"volume"}:
            assert isinstance(ex[key], str) and ex[key].strip(), (ex["id"], key)
        assert isinstance(ex["volume"], int)


def test_no_volume_95_leakage(kit):
    """Volume 95 is the held-out evaluation volume; it must never be taught."""
    assert all(e["volume"] != 95
               for e in kit.extract.build_examples(kit.extract.DEFAULT_CSV))


def test_examples_json_on_disk_matches_extractor(kit):
    on_disk = json.loads((kit.dir / "examples.json").read_text(encoding="utf-8"))
    assert on_disk == kit.extract.build_examples(kit.extract.DEFAULT_CSV)


# ----------------------------- renderers -----------------------------------

def test_build_messages_shape_and_roles(kit):
    messages = kit.build.build_messages(TARGET)
    assert len(messages) == 26  # system + 12 user/assistant pairs + final user
    assert messages[0]["role"] == "system"
    assert "DEFINITION" in messages[0]["content"]
    for i, msg in enumerate(messages[1:-1]):
        assert msg["role"] == ("user" if i % 2 == 0 else "assistant")
    assert messages[-1]["role"] == "user"
    assert TARGET in messages[-1]["content"]


def test_assistant_turns_demonstrate_output_contract(kit):
    examples = kit.build.load_examples()
    assistants = [m for m in kit.build.build_messages(TARGET)
                  if m["role"] == "assistant"]
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


def test_exemplar_user_turns_carry_full_verbatim_sections(kit):
    examples = kit.build.load_examples()
    users = [m for m in kit.build.build_messages(TARGET)[1:-1] if m["role"] == "user"]
    for ex, msg in zip(examples, users):
        assert ex["section_text"] in msg["content"]


def test_flat_prompt_contains_everything(kit):
    flat = kit.build.build_flat_prompt(TARGET)
    for k in range(1, 13):
        assert f"### Example {k}" in flat
    assert TARGET in flat
    assert len(_fenced_json_blocks(flat)) == 12


def test_renderers_are_deterministic(kit):
    assert kit.build.build_messages(TARGET) == kit.build.build_messages(TARGET)
    assert kit.build.build_flat_prompt(TARGET) == kit.build.build_flat_prompt(TARGET)


def test_package_import_works(kit):
    assert kit.pkg.build_messages(TARGET) == kit.build.build_messages(TARGET)


def test_markdown_file_matches_render(kit):
    on_disk = (kit.dir / f"{kit.name}_prompt.md").read_text(encoding="utf-8")
    assert on_disk == kit.build.render_markdown()


def test_cli_runs_as_a_script(kit):
    """Covers the direct-script import fallback in build_prompt.py."""
    result = subprocess.run(
        [sys.executable, str(kit.dir / "build_prompt.py"), "--help"],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# ------------------- kit-specific: fidelity to the SME docs -----------------

def test_q6_question_and_definition_match_sme_doc():
    """2026-08-04 Q6_fewshot_final_prompt.docx."""
    from q6_fewshot import prompt_parts as p
    assert p.QUESTION_TEXT == "Does this section implicate physical construction?"
    d = _collapse(p.CONSTRUCTION_DEFINITION)
    assert "anchored to land or seabed" in d
    assert '"operation, maintenance, and repair" (or similar language)' in d
    assert "destined to be in a building" in d


def test_q1_question_and_definition_match_sme_doc():
    """2026-08-05 Q1_fewshot_final_prompt.docx."""
    from q1_fewshot import prompt_parts as p
    assert p.QUESTION_TEXT == "Does this section recommend or require participation?"
    assert "every actor involved in participation is inside" in _collapse(
        p.SYSTEM_INSTRUCTION)
    d = _collapse(p.PARTICIPATION_DEFINITION)
    assert d.startswith("Participation is when the federal government may or must "
                        "consult or coordinate with people outside of the government")
    assert "It does not include applications for benefits or grants." in d
    assert "It does include the ability to sue the government over a decision." in d
    assert "requiring a public comment period, or requiring rulemaking;" in d


def test_q1_empty_section_cell_was_repaired():
    """The SME left this exemplar's section cell empty and pasted the full
    section into the quoted-span cell; the extractor promotes it."""
    from q1_fewshot import extract_examples as ex
    key = "080-101-000-001-000-000-000-S-000000000000101"
    assert key in ex.SECTION_TEXT_FROM_SPAN
    repaired = next(e for e in ex.build_examples(ex.DEFAULT_CSV)
                    if e["unique_key"] == key)
    assert repaired["section_text"] == repaired["quoted_span"]
    assert len(repaired["section_text"]) > 4000
