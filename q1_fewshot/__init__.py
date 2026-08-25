"""Q1 few-shot labelling kit: model-agnostic prompt builders for the question
"Does this section recommend or require participation?" (Yes/No)."""

from .build_prompt import (  # noqa: F401
    build_flat_prompt,
    build_messages,
    load_examples,
    render_markdown,
)
