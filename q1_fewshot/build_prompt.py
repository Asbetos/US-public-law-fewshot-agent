"""Model-agnostic renderers for the Q1 (participation) few-shot prompt.

Mirrors q6_fewshot/build_prompt.py. Single source of truth is examples.json
(created by extract_examples.py); if that file is absent the renderers fall
back to a zero-example, definition-only prompt.
"""
from __future__ import annotations

import json
from pathlib import Path

try:  # package import (from q1_fewshot import build_prompt)
    from .prompt_parts import PARTICIPATION_DEFINITION, QUESTION_TEXT, SYSTEM_INSTRUCTION
except ImportError:  # direct script / sys.path import
    from prompt_parts import PARTICIPATION_DEFINITION, QUESTION_TEXT, SYSTEM_INSTRUCTION

KIT_DIR = Path(__file__).resolve().parent
EXAMPLES_PATH = KIT_DIR / "examples.json"
MARKDOWN_PATH = KIT_DIR / "q1_fewshot_prompt.md"

# NOT part of the SME-approved prompt document. An opt-in fourth output key used
# by the Claude-vs-Qwen two-coder study (docs/Q1_CLAUDE_VS_QWEN_PLAN.md). Off by
# default, so the kit, the rendered markdown and the August results are unchanged.
# It is spliced into the instruction's own key list (which says "exactly these
# keys") rather than appended as a note: appended, Opus dropped it on 1 of 3 rows.
_JUSTIFICATION_BULLET = (
    '     - "justification": 2-4 sentences explaining why this label is correct\n'
    '       and why the tempting opposite reading is wrong.\n')
CONFIDENCE_BULLET = (
    '     - "confidence": a number from 0 to 1 for how likely you believe your\n'
    '       "label" is correct (1 = certain). Use the full range rather than\n'
    '       defaulting to a high value. The worked EXAMPLES predate this key and\n'
    '       omit it; you must include it.\n')

FLAT_SECTION_HEADER = "### Now label this section"


def load_examples(path: Path = EXAMPLES_PATH) -> list[dict]:
    """The 12 SME exemplars; [] until examples.json exists."""
    path = Path(path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _system_block(confidence: bool = False) -> str:
    instruction = SYSTEM_INSTRUCTION
    if confidence:
        if _JUSTIFICATION_BULLET not in instruction:
            raise RuntimeError("SYSTEM_INSTRUCTION changed; update the confidence splice anchor")
        instruction = instruction.replace(_JUSTIFICATION_BULLET,
                                          _JUSTIFICATION_BULLET + CONFIDENCE_BULLET, 1)
    return f"{instruction}\nDEFINITION:\n{PARTICIPATION_DEFINITION}"


CONFIDENCE_REMINDER = ('REMINDER: your ```json block must also contain the "confidence" key '
                       '(a number from 0 to 1), after "justification".')


def _user_turn(section_text: str, confidence: bool = False) -> str:
    turn = f"QUESTION:\n{QUESTION_TEXT}\n\nSECTION:\n{section_text}"
    # Only the section to label gets the reminder; the exemplar turns stay as the
    # SMEs wrote them. Without it both models drop the key on a share of rows.
    return f"{turn}\n\n{CONFIDENCE_REMINDER}" if confidence else turn


def _assistant_turn(example: dict) -> str:
    payload = {
        "label": example["label"],
        "quoted_span": example["quoted_span"],
        "justification": f"{example['resolution']} {example['temptation']}",
    }
    return (
        f"Temptation: {example['temptation']}\n"
        f"Resolution: {example['resolution']}\n"
        "```json\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n```"
    )


def build_messages(section_text: str, examples: list[dict] | None = None,
                   confidence: bool = False) -> list[dict]:
    """OpenAI-style chat messages: system, exemplar pairs (if any), final user turn."""
    examples = load_examples() if examples is None else examples
    messages = [{"role": "system", "content": _system_block(confidence)}]
    for example in examples:
        messages.append({"role": "user", "content": _user_turn(example["section_text"])})
        messages.append({"role": "assistant", "content": _assistant_turn(example)})
    messages.append({"role": "user", "content": _user_turn(section_text, confidence)})
    return messages


def _flat_parts(section_text: str, examples: list[dict], confidence: bool) -> tuple[list[str], str]:
    """The flat prompt's pieces: [system block, example 1..N] and the final section part."""
    parts = [_system_block(confidence)]
    for k, example in enumerate(examples, 1):
        parts.append(
            f"### Example {k}\n{_user_turn(example['section_text'])}\n\n"
            f"{_assistant_turn(example)}"
        )
    return parts, f"{FLAT_SECTION_HEADER}\n{_user_turn(section_text, confidence)}"


def build_flat_prompt(section_text: str, examples: list[dict] | None = None,
                      confidence: bool = False) -> str:
    """Single-string prompt for base/completion models and copy-paste use."""
    examples = load_examples() if examples is None else examples
    parts, final = _flat_parts(section_text, examples, confidence)
    return "\n\n".join(parts + [final])


def build_flat_messages(section_text: str, examples: list[dict] | None = None,
                        confidence: bool = False) -> list[dict]:
    """The flat prompt split in two: instruction + definition + examples as the
    system turn, the section alone as the user turn. For chat APIs that cannot
    take the exemplar pairs as assistant turns (the Claude Code SDK takes one
    system prompt and user turns only). Invariant: system + "\\n\\n" + user is
    exactly build_flat_prompt()."""
    examples = load_examples() if examples is None else examples
    parts, final = _flat_parts(section_text, examples, confidence)
    return [{"role": "system", "content": "\n\n".join(parts)},
            {"role": "user", "content": final}]


def render_markdown(examples: list[dict] | None = None) -> str:
    """Human-readable, copy-pasteable render of the complete flat prompt."""
    examples = load_examples() if examples is None else examples
    status = (
        "" if examples else
        "**Status: definition-only.** The SME worked examples have not been "
        "added yet; when `examples.json` lands, regenerating this file will "
        "include them automatically.\n\n"
    )
    header = (
        "<!-- GENERATED FILE - do not hand-edit. -->\n"
        "<!-- Regenerate: python q1_fewshot/build_prompt.py --write-markdown -->\n\n"
        "# Q1 Few-Shot Prompt (rendered)\n\n"
        + status +
        "Canonical data: `examples.json`; renderers: `build_prompt.py` "
        "(`build_messages()` for chat models, `build_flat_prompt()` for "
        "completion models). Everything below is the flat rendering.\n\n"
        "---\n\n"
    )
    return header + build_flat_prompt("<PASTE SECTION TEXT HERE>", examples) + "\n"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-markdown", action="store_true",
                        help=f"regenerate {MARKDOWN_PATH.name}")
    parser.add_argument("--section-file", type=Path,
                        help="print a flat prompt for the section text in FILE")
    args = parser.parse_args()
    if args.write_markdown:
        MARKDOWN_PATH.write_text(render_markdown(), encoding="utf-8")
        print(f"wrote {MARKDOWN_PATH}")
    if args.section_file:
        print(build_flat_prompt(args.section_file.read_text(encoding="utf-8")))
    if not args.write_markdown and not args.section_file:
        parser.print_help()


if __name__ == "__main__":
    main()
