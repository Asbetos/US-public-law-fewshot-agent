"""Extract the 12 SME Q1 exemplars from data/Q1_examples.csv into examples.json.

The CSV is transposed: column 0 is the field name, columns 1-12 are the
exemplars (1-6 = No with column 1 easy; 7-12 = Yes with column 7 easy).
Section text and quoted span are kept byte-for-byte verbatim; only the
prose fields (temptation / resolution) are whitespace-collapsed.

Mirrors q6_fewshot/extract_examples.py. Differences, all in the constants
below: the Q1/Q6 marker value, the renamed "What makes it [the opposite
answer] look tempting?" column, and one documented section-text repair.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parent
REPO_DIR = KIT_DIR.parent
DEFAULT_CSV = REPO_DIR / "data" / "Q1_examples.csv"
DEFAULT_OUT = KIT_DIR / "examples.json"

N_EXAMPLES = 12
N_PER_LABEL = 6
HELD_OUT_VOLUME = 95
QUESTION_MARKER = "1"

# Field-name prefixes (prefix match: some CSV labels embed quotes/arrows).
# NOTE: the Q1 sheet renamed the tempting column to "What makes it [the
# opposite answer] look tempting?", so the prefix stops before the bracket.
FIELD_PREFIXES = {
    "volume": "Volume",
    "unique_key": "UniqueKey",
    "question": "Q1 or Q6?",
    "section_text": "Section text",
    "label": "Correct answer",
    "quoted_span": "Quoted span",
    "resolution": "Explain why",
    "temptation": "What makes it",
}

# Documented data repair. For this exemplar the SME left the section-text cell
# empty and pasted the full section (NLRB Sec. 3-4) into the quoted-span cell
# instead. Promote the span to section_text so the exemplar is usable; the span
# then equals the section, which several other exemplars already do.
SECTION_TEXT_FROM_SPAN = {"080-101-000-001-000-000-000-S-000000000000101"}


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _read_fields(csv_path: Path) -> dict[str, list[str]]:
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    fields: dict[str, list[str]] = {}
    for row in rows:
        if not row:
            continue
        name = row[0].strip()
        for key, prefix in FIELD_PREFIXES.items():
            if key not in fields and name.startswith(prefix):
                cells = row[1:1 + N_EXAMPLES]
                if len(cells) != N_EXAMPLES:
                    raise ValueError(
                        f"field {name!r}: expected {N_EXAMPLES} cells, got {len(cells)}"
                    )
                fields[key] = cells
    missing = sorted(set(FIELD_PREFIXES) - set(fields))
    if missing:
        raise ValueError(f"missing fields in {csv_path}: {missing}")
    return fields


def build_examples(csv_path: Path = DEFAULT_CSV) -> list[dict]:
    fields = _read_fields(Path(csv_path))
    examples = []
    for i in range(N_EXAMPLES):
        label = fields["label"][i].strip().capitalize()
        expected = "No" if i < N_PER_LABEL else "Yes"
        if label != expected:
            raise ValueError(f"column {i + 1}: expected label {expected}, got {label!r}")
        if fields["question"][i].strip() != QUESTION_MARKER:
            raise ValueError(f"column {i + 1}: not a Q{QUESTION_MARKER} exemplar")
        volume = int(fields["volume"][i].strip())
        if volume == HELD_OUT_VOLUME:
            raise ValueError(f"column {i + 1}: volume {HELD_OUT_VOLUME} is held out")
        unique_key = fields["unique_key"][i].strip()
        section_text = fields["section_text"][i]
        quoted_span = fields["quoted_span"][i]
        if unique_key in SECTION_TEXT_FROM_SPAN and not section_text.strip():
            section_text = quoted_span
            print(f"  repair: column {i + 1} ({unique_key}) "
                  f"section_text promoted from quoted_span")
        if (quoted_span not in section_text
                and _collapse_ws(quoted_span) not in _collapse_ws(section_text)):
            raise ValueError(f"column {i + 1}: quoted span not found in section text")
        group_index = (i % N_PER_LABEL) + 1
        difficulty = "easy" if group_index == 1 else "ambiguous"
        examples.append({
            "id": f"{label.lower()}-{difficulty}-{group_index}",
            "volume": volume,
            "unique_key": unique_key,
            "difficulty": difficulty,
            "label": label,
            "section_text": section_text,
            "quoted_span": quoted_span,
            "temptation": _collapse_ws(fields["temptation"][i]),
            "resolution": _collapse_ws(fields["resolution"][i]),
        })
    nos, yeses = examples[:N_PER_LABEL], examples[N_PER_LABEL:]
    ordered = [nos[0], yeses[0]]
    for k in range(1, N_PER_LABEL):
        ordered.extend([nos[k], yeses[k]])
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    examples = build_examples(args.csv)
    args.out.write_text(
        json.dumps(examples, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(examples)} exemplars -> {args.out}")


if __name__ == "__main__":
    main()
