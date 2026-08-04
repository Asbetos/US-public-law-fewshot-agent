"""Model-agnostic renderers for the Q6 few-shot prompt.

Single source of truth is examples.json (created by extract_examples.py).
Renderers are deterministic pure functions; no model SDK imports.
"""
from __future__ import annotations

import json
from pathlib import Path

try:  # package import (from q6_fewshot import build_prompt)
    from .prompt_parts import CONSTRUCTION_DEFINITION, QUESTION_TEXT, SYSTEM_INSTRUCTION
except ImportError:  # direct script / sys.path import
    from prompt_parts import CONSTRUCTION_DEFINITION, QUESTION_TEXT, SYSTEM_INSTRUCTION

KIT_DIR = Path(__file__).resolve().parent
EXAMPLES_PATH = KIT_DIR / "examples.json"
MARKDOWN_PATH = KIT_DIR / "q6_fewshot_prompt.md"


def load_examples(path: Path = EXAMPLES_PATH) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _system_block() -> str:
    return f"{SYSTEM_INSTRUCTION}\nDEFINITION:\n{CONSTRUCTION_DEFINITION}"


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
    """OpenAI-style chat messages: system, 12 exemplar pairs, final user turn."""
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
    header = (
        "<!-- GENERATED FILE - do not hand-edit. -->\n"
        "<!-- Regenerate: python q6_fewshot/build_prompt.py --write-markdown -->\n\n"
        "# Q6 Few-Shot Prompt (rendered)\n\n"
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
