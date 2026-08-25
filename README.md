# US Public Law Few-Shot Agent

A model-agnostic **few-shot labelling kit** for classifying sections of
published U.S. Statutes. Currently covers one question, **Q6**:

> **"Does this section implicate physical construction?"** — answered **Yes** or **No**.

The kit teaches any LLM — Claude or open-source models served via vLLM,
Ollama, or Hugging Face — to answer the way subject-matter experts do, using
the experts' own worked examples.

## How it works, in one paragraph

Think of it like training a new employee: you hand them a rule book *and*
walk them through a dozen solved cases, including the tricky ones, explaining
"this looks like a Yes, but it's actually a No, and here's why." Every request
to the model contains exactly that: the rule book (our definition of
construction), twelve expert-solved cases with their reasoning, and the new
section to label. The model answers in a fixed three-part form that a program
can read automatically.

## Repository layout

| Path | What it is |
|---|---|
| `data/Q6_examples.csv` | The experts' original spreadsheet: 12 real statute sections (6 Yes, 6 No; 1 easy + 5 tricky each) with correct answers, proof quotes, and contrastive reasoning. |
| `q6_fewshot/examples.json` | The 12 solved cases in clean machine-readable form (generated from the CSV). |
| `q6_fewshot/prompt_parts.py` | The rule book: system instructions plus the full definition of "construction", including the traps. |
| `q6_fewshot/build_prompt.py` | The assembler: combines rule book + solved cases + your new section into one request. Also the CLI. |
| `q6_fewshot/extract_examples.py` | The importer: rebuilds `examples.json` from the CSV, with validation. |
| `q6_fewshot/q6_fewshot_prompt.md` | The complete request rendered as one readable document (generated — do not hand-edit). |
| `q1_fewshot/` | **Q1 (participation)** — the same five files for "Does this section recommend or require participation?", built from `data/Q1_examples.csv`. |
| `*_fewshot/*_final_prompt.docx` | The SME-approved prompt document for each question — the authority for the instruction and definition wording. Edit it first, then mirror into `prompt_parts.py`. |
| `run_model.py` | The runner: sends the prompt to any OpenAI-compatible model server (vLLM, Ollama, llama.cpp, hosted APIs) and parses the answer. |
| `tests/test_q6_fewshot.py` | Automatic checks that keep every file consistent with the others. |

## Running on another server

Everything is self-contained — clone, verify, point at your model server:

```bash
git clone git@github.com:Asbetos/US-public-law-fewshot-agent.git
cd US-public-law-fewshot-agent
python3 -m venv .venv && source .venv/bin/activate   # Python 3.10+
python -m pip install -r requirements.txt            # pytest only
python -m pytest tests/ -v                           # 17 checks should pass
```

Then label sections against any server exposing an OpenAI-compatible API
(vLLM, Ollama, llama.cpp server, or a hosted provider) — stdlib only, nothing
else to install:

```bash
# vLLM example (default base URL is http://localhost:8000/v1)
python run_model.py --model meta-llama/Llama-3.1-8B-Instruct \
    --section-file section.txt

# Ollama example
python run_model.py --base-url http://localhost:11434/v1 \
    --model llama3.1 --section-file section.txt

# Batch: JSONL in, JSONL out (one {"id": ..., "text": ...} per line)
python run_model.py --model llama3.1 --base-url http://localhost:11434/v1 \
    --input-jsonl sections.jsonl --output results.jsonl
```

Each result carries `label`, `quoted_span`, `justification`, and the raw model
reply (or an `error` field if the request or parsing failed — batch runs keep
going and record the error per row).

## Usage from Python

```python
from q6_fewshot import build_messages, build_flat_prompt

section = "The Secretary shall construct a bridge across the Missouri River."

# Chat-style models (vLLM, Ollama, HF chat templates, Claude, OpenAI-compatible):
messages = build_messages(section)

# Completion-style models (single string):
prompt = build_flat_prompt(section)
```

The model's reply ends with one fenced ```json block containing exactly:

```json
{
  "label": "Yes",
  "quoted_span": "shall construct a bridge",
  "justification": "..."
}
```

### From the command line

```bash
# Print a ready-to-paste prompt for a section stored in section.txt
python q6_fewshot/build_prompt.py --section-file section.txt
```

## The labelling process, step by step

1. **Experts filled in the spreadsheet** (`data/Q6_examples.csv`) with 12 real
   statute sections. For each: the correct label, the exact sentence that
   proves it, why that answer is right, and why the wrong answer looks
   tempting.
2. **The importer validates and converts it** — `python
   q6_fewshot/extract_examples.py` produces `examples.json`, checking: exactly
   12 examples, labels balanced 6/6, every proof quote appears verbatim in its
   section, and none comes from Volume 95 (held out as the final exam, so it
   must never leak into the teaching materials).
3. **The assembler builds the request** — instructions → definition → the 12
   solved cases (each shown as *section → tempting wrong reading → why it's
   wrong → final answer*) → the new section. Cases are ordered easy-No,
   easy-Yes, then tricky ones alternating No/Yes to avoid position bias.
4. **You send it to any model** in whichever of the two formats it expects.
5. **The model imitates the solved cases**: names the tempting wrong reading,
   rebuts it, then emits the three-part JSON answer.
6. **Your code parses the JSON block** and records the label.

## Keeping files in sync

If the spreadsheet ever changes, refresh everything from the repo root:

```bash
python q6_fewshot/extract_examples.py                 # CSV -> examples.json
python q6_fewshot/build_prompt.py --write-markdown    # refresh the rendered document
python -m pytest tests/ -v                            # verify nothing drifted
```

The tests fail loudly if any generated file is out of step with its source.
