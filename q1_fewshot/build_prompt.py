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


def load_examples(path: Path = EXAMPLES_PATH) -> list[dict]:
    """The 12 SME exemplars; [] until examples.json exists."""
    path = Path(path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _system_block() -> str:
    return f"{SYSTEM_INSTRUCTION}\nDEFINITION:\n{PARTICIPATION_DEFINITION}"


def _user_turn(section_text: str) -> str:
    return f"QUESTION:\n{QUESTION_TEXT}\n\nSECTION:\n{section_text}"


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


def build_messages(section_text: str, examples: list[dict] | None = None) -> list[dict]:
    """OpenAI-style chat messages: system, exemplar pairs (if any), final user turn."""
    examples = load_examples() if examples is None else examples
    messages = [{"role": "system", "content": _system_block()}]
    for example in examples:
        messages.append({"role": "user", "content": _user_turn(example["section_text"])})
        messages.append({"role": "assistant", "content": _assistant_turn(example)})
    messages.append({"role": "user", "content": _user_turn(section_text)})
    return messages


def build_flat_prompt(section_text: str, examples: list[dict] | None = None) -> str:
    """Single-string prompt for base/completion models and copy-paste use."""
    examples = load_examples() if examples is None else examples
    parts = [_system_block()]
    for k, example in enumerate(examples, 1):
        parts.append(
            f"### Example {k}\n{_user_turn(example['section_text'])}\n\n"
            f"{_assistant_turn(example)}"
        )
    parts.append(f"### Now label this section\n{_user_turn(section_text)}")
    return "\n\n".join(parts)


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
