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
| `data/fewshot_q1q6/` | **The experiment corpus** (Q1+Q6): a 12,514-row exemplar **pool** and a 1,791-row held-out **test set** (volumes 62, 91, 132), derived from the curated SME training dataset. See its own README for columns and leakage caveats. Kept on the group folder, not in git. |
| `run_model.py` | The runner: sends the prompt to any OpenAI-compatible model server (vLLM, Ollama, llama.cpp, hosted APIs) and parses the answer. |
| `verify_no_test_leakage.py` | Gate: verifies no exemplar in either prompt comes from the held-out test set, checking volume + unique_key + **text** (text catches recurring boilerplate the other two miss). Exit 1 on leakage. |
| `tests/test_q6_fewshot.py` | Automatic checks that keep every file consistent with the others. |
| `serving/serve_vllm.sh` | Launches the local model server (vLLM) with the flags this GPU needs. |
| `eval/make_test_jsonl.py` | Held-out parquet → the `{"id", "text"}` JSONL the runners consume. |
| `eval/run_batch.py` | Concurrent, resumable labelling client — `run_model.py` with N requests in flight. |
| `eval/score.py` | Predictions + SME labels → `results/metrics.json` (with bootstrap CIs). |
| `eval/compare_thinking.py` | A/B of the model's native reasoning mode on identical rows. |
| `eval/collect_infra.py` | Measured infrastructure cost — GPU memory split, KV geometry, per-row timing. |
| `eval/dashboard_assets/` | Markup, styles and chart code — **the single source of truth**, shared by the offline build and the local app. |
| `eval/dashboard.py` | Inlines those assets + `results/*.json` → one self-contained offline HTML file. |
| `dashboard-app/` | Local Next.js viewer: serves the same dashboard live from `results/`, so you refresh a tab instead of re-downloading HTML (`./serving/serve_dashboard.sh`). |
| `eval/run_all.sh` | Runs the whole experiment end to end. |
| `docs/Q1_CLAUDE_VS_QWEN_PLAN.md` | **Q1 two-coder study**: the plan for scoring the same 3,000 coded sections with Claude Opus 5.5 and the local Qwen3.6-27B. |
| `docs/Q1_QWEN_SCORING_REPORT.md` | The Qwen results in plain language, with every measure explained on a worked example. |
| `eval/make_panel_sample.py` | Draws the study's random sample from the coded panel (test volumes and prompt examples excluded). |
| `eval/final_labels.py` | Attaches the final reconciled Q1 label: Yes when every coder's final answer is Yes. |
| `eval/run_claude.py` | Labels the sample with Claude through the Claude Agent SDK (no tools, one turn, answer keys checked by a schema). |
| `eval/run_q1_compare.sh` | Runs the study stage by stage: `sample`, `final-labels`, `qwen`, `qwen-flat`, `claude-probe`, `claude`, `claude-repeat`, `compare`, `dashboard`. |
| `eval/compare_models.py` | Every number in the study: each model against the final label, the two models against each other, the coders' first answers, prompt layout, confidence, and per-section outputs. |
| `eval/compare_dashboard.py`, `eval/compare_assets/` | The study's self-contained dashboard. |
| `results/q1_panel3k/` | Study outputs. In git: `dashboard.html`, `qwen_output.jsonl` (Qwen's answer for every section) and `q1_two_coder_sheet.{csv,xlsx}`; the rest is regenerated by `eval/compare_models.py`. |

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

## Running the full experiment locally (vLLM on one GPU)

The kit is model-agnostic; this is the recipe for scoring an **open-weights model on
the held-out test set** rather than labelling one section at a time.

```bash
python3 -m venv .venv-vllm && .venv-vllm/bin/pip install vllm   # Python 3.12+
./serving/serve_vllm.sh                                          # starts on :8000
python eval/make_test_jsonl.py                                   # build the inputs
./eval/run_all.sh                                                # label, score, render
open results/dashboard.html
```

`run_all.sh` is resumable at every stage — re-running it skips rows already present
in the output JSONL, so an interrupted run continues instead of starting over.

### Three things that decide whether this is tractable on a small GPU

The prompt is the expensive part: **each request carries ~12,000 tokens** of
instructions and worked examples for a section that is typically ~340 tokens. Across
1,791 sections × 2 questions that is 44M prompt tokens if nothing is shared.

1. **Prefix caching is mandatory, and may not be on by default.** The few-shot prefix
   is byte-identical across every request, so the server should prefill it once.
   For hybrid linear-attention models (Qwen3.5/3.6) vLLM defaults
   `enable_prefix_caching` to **off** — pass `--enable-prefix-caching` explicitly and
   confirm a non-zero "Prefix cache hit rate" in the server log. Without it the run is
   roughly ten times slower.
2. **Concurrency comes from sharing, not from raising `--max-num-seqs`.** Those models
   also force a large attention block (1,568 tokens, to match the mamba page size), so
   an uncached 12k-token prompt claims eight blocks and only two requests fit at once.
   Cached, those blocks are shared and the same memory holds eight.
3. **Turn the model's thinking mode off.** The prompt already asks for an explicit
   Temptation/Resolution before the JSON answer. Qwen chat templates open a `<think>`
   block unless told otherwise, which multiplies output tokens several-fold;
   `eval/run_batch.py` sends `chat_template_kwargs: {"enable_thinking": false}` unless
   you pass `--thinking`. Use `eval/compare_thinking.py` to check what that costs.

### Reading the infrastructure panel

`eval/collect_infra.py` reads the measured cost back out of the server's own logging,
the GPU, the model on disk and the per-row timings — nothing is estimated — and the
dashboard renders it. On a 23 GB card it is the most useful panel in the report:
the weights take 18.5 GiB, which leaves **2.03 GiB of KV cache** (50,972 tokens, and
only 32 blocks because this model's mamba page size forces a 1,568-token attention
block). That single number sets the concurrency, and therefore the throughput.

The per-row timings show where the wall-clock actually goes: the shortest sections
(~170 chars) still cost ~56 s and the longest (~1,900 chars) ~73 s, so **generating the
answer dominates, not reading the section**. Shortening the input would not help much;
shortening the *output*, or fitting more requests in the KV cache, would.

### Reading the scores

Both questions are heavily imbalanced — the experts marked Yes on 3.9% of test rows
for Q1 and 11.3% for Q6 — so **accuracy is not a meaningful headline**: answering "No"
to everything scores 96% on Q1. `eval/score.py` leads with Yes-class
precision/recall/F1 and MCC, each with a 95% bootstrap interval, and reports the
always-No baseline beside them. It also scores the run two ways: *strict* (unparseable
replies dropped) and *deployed* (unparseable forced to No, which is what a pipeline
must actually do with a non-answer).

Because the kit asks for a verbatim supporting quote, the scorer also checks whether
that quote really appears in the section and how far it overlaps the coder's own span
— a right answer for the wrong reason is visible rather than hidden.

## Keeping files in sync

If the spreadsheet ever changes, refresh everything from the repo root:

```bash
python q6_fewshot/extract_examples.py                 # CSV -> examples.json
python q6_fewshot/build_prompt.py --write-markdown    # refresh the rendered document
python -m pytest tests/ -v                            # verify nothing drifted
```

The tests fail loudly if any generated file is out of step with its source.
