# Q1 scoring with Qwen3.6-27B: results on the 3,000-section sample

*11 November 2026. This is the first half of the Q1 two-coder study (Claude Opus 5.5 against Qwen3.6-27B, see
[the plan](Q1_CLAUDE_VS_QWEN_PLAN.md)). The Claude run has not started yet, so everything here is about Qwen alone.
The interactive version, with every disagreement and Qwen's reasons, is the dashboard at
[`results/q1_panel3k/dashboard.html`](../results/q1_panel3k/dashboard.html) (download it and open it in a browser).*

## Summary

- **Coverage.** Qwen answered 2,984 of the 3,000 sections. The 16 it never answered are mostly long sections that
  the coders marked Yes.
- **Against the coders' final labels.** Qwen matches the final label on 95.7% of sections, but that figure is
  inflated by the many easy No sections: answering No to everything would score 95.6%. On the rare Yes sections,
  which are what matter here:
  - it catches **57 of the 132** final-Yes sections it answered (43%);
  - **51%** of its Yes calls are right;
  - its kappa, agreement after discounting chance, is **0.45** ("moderate").
- **Against a single coder.** Before reconciliation, Qwen agrees with one coder's first answer about as well as
  a second human coder does.
- **Five observations**, each in section 4:
  1. **The prompt layout changes Qwen's answers a lot.** With the worked examples given as one block of text,
     the way Claude receives them, Qwen caught 16 of 19 final-Yes sections instead of 9.
  2. **Qwen often sees the participation language and reasons it away.**
  3. **Many of its false alarms follow the written definition word for word.** Some may be coder misses.
  4. **Long sections are where it goes wrong.**
  5. **Its stated confidence is a useful flag for review; its token probability, P(Yes), is not.**

---

## 1. What was done

| | |
|---|---|
| Sections | 3,000 drawn at random from the coded panel: 19 volumes, 1,159 laws. Excluded: the held-out test volumes, a few quarantined volumes, and the 24 sections used as worked examples in the prompt. |
| Reference label | The **final label**: the label in the final, reconciled coding workbook. A section is Yes when every coder's final answer is Yes. The sample has **143 Yes (4.8%)** and 2,857 No. The 4 sections still split in the final workbook count as Yes, as the team decided; 19 sections have only one coder's answer. |
| Model | Qwen3.6-27B (4-bit version) on the group's single L4 GPU. Temperature 0, so the same input gives the same answer. |
| Prompt | The SME-approved Q1 few-shot kit unchanged: instructions, the definition and 12 worked examples. Qwen returns a label, the passage it relies on, a short reason and a confidence from 0 to 1. |
| Also recorded | **P(Yes)**: Qwen's own probability for the word "Yes" at the moment it writes the label. |
| Run time | 12 hours for the first pass (about 250 sections an hour) plus 1.4 hours of retries. |

---

## 2. How to read the results

### 2.1 Every answered section lands in one of four boxes

Each of the 2,984 answered sections is compared with its final label:

| | **Final label Yes** | **Final label No** | **Total** |
|---|---:|---:|---:|
| **Qwen says Yes** | **57** caught | **54** false alarms | 111 |
| **Qwen says No** | **75** missed | **2,798** correct No | 2,873 |
| **Total** | 132 | 2,852 | 2,984 |

A real section from the sample in each box:

- **Caught** (final Yes, Qwen Yes). *Public Law 90–72, volume 81:* "…the Secretary … shall consult with local
  interests who may be affected by the construction … through public hearings…". Qwen: Yes, confidence 1.0. Its
  reason: the section requires consulting outside parties, with public hearings named as the method.
- **Missed** (final Yes, Qwen No). *Public Law 96–87, volume 93:* "The Secretary of the Interior is authorized, in
  cooperation with the Appalachian Trail Conference and the State of Maryland, to design and erect … an appropriate
  marker…". Qwen: No, confidence 0.8. Its reason: the cooperation concerns carrying out a decision Congress
  already made, not consultation before a decision.
- **False alarm** (final No, Qwen Yes). *Public Law 89–401, volume 80:* "The medals … shall be of such size or sizes
  and of such various metals as shall be determined by the Secretary of the Treasury in consultation with the
  American Numismatic Association." Qwen: Yes, confidence 1.0. Its reason: a decision made after consulting an
  outside organization.
- **Correct No** (final No, Qwen No). *Public Law 80-337, volume 61:* "That this Act may be cited as the 'Army-Navy
  Medical Services Corps Act of 1947'." Qwen: No, confidence 1.0. Its reason: a short title, with no
  participation mechanism.

### 2.2 What each row of the results table means

Every measure divides one box, or a sum of boxes, by another:

| Row in the table | What it counts | Worked out from the boxes | How to read it |
|---|---|---|---|
| **Final-Yes sections Qwen also called Yes** (catch rate; also called hit rate or recall) | caught ÷ all final-Yes sections | 57 ÷ 132 = **43.2%** | Of every 100 sections the coders mark Yes, Qwen finds about 43. The other 75 are misses. |
| **False alarms on final-No sections** (false-alarm rate) | false alarms ÷ all final-No sections | 54 ÷ 2,852 = **1.9%** | Of every 100 sections the coders mark No, Qwen wrongly says Yes on about 2. The rate is small only because No sections are so many: 54 false alarms is almost as many as the 57 catches. |
| **Qwen's Yes calls that are right** (precision) | caught ÷ all of Qwen's Yes calls | 57 ÷ 111 = **51.4%** | When Qwen says Yes, the coders agree about half the time. |
| **How often it says Yes** (Yes rate) | Qwen's Yes calls ÷ all sections | 111 ÷ 2,984 = **3.7%**, against 132 ÷ 2,984 = **4.4%** for the final label | Qwen says Yes a little less often than the coders. This shows whether a model leans towards Yes or No, whatever it gets right. |
| **Agreement** | (caught + correct No) ÷ all sections | (57 + 2,798) ÷ 2,984 = **95.7%** | The share of sections where the two labels match. It looks impressive but is not: a coder who answered No to every section would score 2,852 ÷ 2,984 = **95.6%** while catching nothing. That is why the next row exists. |
| **Kappa** | agreement beyond what chance alone would give | chance agreement = **92.2%** (see below); kappa = (95.7 − 92.2) ÷ (100 − 92.2) = **0.45** | 0 means no better than chance, 1 means perfect. By a common rule of thumb, 0.41–0.60 is "moderate" agreement. |
| **AC1** | another chance-corrected agreement score | **0.95** | Like kappa, but it assumes less chance agreement when one answer dominates, so it stays high whenever both say No on most sections. It is listed because other project reports use it; read the catch rate and kappa first. |

**Where "chance agreement = 92.2%" comes from.** Suppose Qwen had made its 111 Yes calls at random instead of
reading the sections. It says Yes on 3.7% of sections and the final label says Yes on 4.4%. They would then agree
by luck:

- on Yes about 3.7% × 4.4% = 0.16% of the time;
- on No about 96.3% × 95.6% = 92.0% of the time;
- 92.2% in all.

Kappa asks how much of the remaining gap between 92.2% and a perfect 100% Qwen actually closes:
(95.7 − 92.2) ÷ (100 − 92.2) = 3.5 ÷ 7.8 = 0.45.

### 2.3 The 95% interval in brackets

Each number comes from one random draw of sections. A different draw would give a slightly different number. The
interval shows how far it would plausibly move. For example, the catch rate is 43%, with an interval of 35% to
52%.

How it is computed:

1. The laws in the sample are re-drawn at random 2,000 times. Each law keeps all its sections together, because
   sections of the same law tend to be coded alike.
2. The measure is recomputed for each re-draw.
3. The middle 95% of those 2,000 results is reported as the interval.

### 2.4 The secondary comparison: one coder's first answer

The first answers are what each coder put down before the coders discussed and reconciled. Take the
Appalachian Trail section above. Coder A first answered No, Coder B first answered Yes, and they later settled on
Yes.

The *coder replacement* check asks a different question from everything above: **if Qwen took one coder's seat,
would it agree with the other coder as often as the two coders agreed with each other?** Over all sections:

| Pair | Agreement | Kappa |
|---|---:|---:|
| Coder vs coder (first answers) | 95.6% | 0.34 |
| Qwen vs a coder (first answers) | 95.4% | 0.33 |
| **Difference** | −0.3 points | **−0.02** (95% interval −0.11 to +0.07) |

Qwen is on par with a second coder by this measure. The low kappa on both rows shows how often the coders' first
answers differ on Q1. That is why the final, reconciled label is the reference everywhere else. These numbers are
on a different footing from the final-label ones, so the two sets are not compared with each other.

---

## 3. Results

| Measure (against the final label) | Qwen | 95% interval |
|---|---:|---|
| Sections answered | 2,984 of 3,000 | — |
| Final-Yes sections Qwen also called Yes (catch rate) | 43.2% (57 of 132) | 34.6% to 51.9% |
| False alarms on final-No sections | 1.9% (54 of 2,852) | 1.4% to 2.5% |
| Qwen's Yes calls that are right (precision) | 51.4% (57 of 111) | 42.1% to 60.6% |
| How often it says Yes (final label: 4.4%) | 3.7% | its rate ÷ the final label's: 0.84 (0.69 to 1.01) |
| Agreement | 95.7% | 94.8% to 96.5% |
| Kappa | 0.45 | 0.36 to 0.52 |
| AC1 | 0.95 | 0.94 to 0.96 |
| *Secondary:* kappa with a coder's first answer (coders with each other: 0.34) | 0.33 | difference −0.11 to +0.07 |

Of the 3 still-disputed sections it answered, Qwen called all 3 No. Under the team's rule they count as Yes, so
they are among the misses.

---

## 4. Key observations

### 4.1 The prompt layout changes Qwen's answers a lot

The main run gave Qwen the 12 worked examples **as a conversation**. Each example section came as a user turn and
its answer as Qwen's own turn. Claude cannot be given examples that way through its software kit, so it receives
the same instructions, definition and examples **as one block of text**, with the section at the end.

To see whether the layout alone matters, a random 300 sections were labelled again by Qwen in the one-block
layout. Of these, 298 were answered in both layouts, 19 of them final Yes:

| | Chat layout (main run) | One-block layout (how Claude gets it) |
|---|---:|---:|
| Final-Yes sections caught | 9 of 19 (47%) | **16 of 19 (84%)** |
| False alarms on final-No sections | 10 of 279 (3.6%) | 16 of 279 (5.7%) |
| Yes calls that are right | 9 of 19 (47%) | 16 of 32 (50%) |
| Kappa with the final label | 0.44 | 0.60 |
| Replies that wrote a reasoning paragraph before answering | 298 of 298 | 28 of 298 |

- **All 13 answers that changed went from No to Yes**: 7 on final-Yes sections, 6 on final-No sections. None went
  the other way.
- The gain in catches is unlikely to be chance:
  - an exact test on the changed answers gives p = 0.016;
  - the catch rate rises by 37 points, with an interval of +16 to +59 points.
  - It rests on only 19 Yes sections, though, so its size is uncertain.
- The rise in kappa, from 0.44 to 0.60, could still be chance (interval −0.01 to +0.35).

The likely mechanism is the kit's instruction to state "the tempting-but-wrong reading" before answering.

- In the chat layout, Qwen follows the worked examples and writes that paragraph every time.
- Arguing against the obvious reading appears to talk it out of Yes calls (see 4.2).
- In the one-block layout it mostly skips the paragraph and answers directly.

What this means:

- **Part of any difference between Claude and Qwen may come from the layout, not the model.**
- Changing the reasoning step might raise Qwen's catch rate considerably. That is worth a proper test before a
  setup is chosen.

A side effect of the one-block layout: 159 of the 300 one-block answers came back without the code fence the kit
asks for. The answers themselves were valid. They were read from the saved replies, and the parser now accepts
this form.

### 4.2 Qwen often sees the participation language and reasons it away

In **25 of its 75 misses**, the passage Qwen itself quotes contains a participation word: consult, comment,
hearing, cooperate, coordinate, concur or rulemaking. Even so, it answered No. A read-through of a sample of misses
shows its reasons stretching the definition's exclusions:

- **The "applications for benefits or grants" exclusion, applied to consultation inside a grant programme.**
  Example (Public Law 111–340): a state plan must "describe how the State library administrative agency will work
  with other State agencies…".
- **Outside involvement called "implementation", "a study" or "permissive".** Examples: the Appalachian Trail
  marker built "in cooperation with" a private conference and a State; an advisory board that "may consult with
  industry, academia, or nonprofits" (Public Law 115–1). Calling that "permissive" contradicts the definition,
  which begins "the federal government **may or must** consult or coordinate with people outside of the
  government".
- **Outside parties treated as resources rather than participants.** Example (Public Law 112–205): "Before
  establishing a BEST unit, the Secretary shall consider … the availability of Federal, State, local, tribal, and
  foreign law enforcement resources to participate…".
- **Hearings and opportunities to present views called adjudication or due process**, not participation.

Qwen's stated confidence on these misses is usually 0.9 or 0.95 rather than 1.0 (see 4.5).

### 4.3 Many false alarms follow the written definition word for word

**32 of the 54 false alarms** quote a participation word. Several read like a Yes under the definition as written,
which lists "requiring a public comment period, or requiring rulemaking" and "consultation or coordination with
states, tribes, local governments, or other outside entities before a federal action". Examples the final sheet
marks **No**:

- "provide public notice and an opportunity for comment before designating a database" (Public Law 112–248, an
  11,528-character section);
- "The order establishing the dispute resolution program shall be issued after notice and opportunity for public
  comment in accordance with section 553…" (Public Law 106–569);
- "regulations closing areas … shall be made in consultation with the appropriate agency of the State of
  Colorado…" (Public Law 106–530);
- medal sizes set "in consultation with the American Numismatic Association" (Public Law 89–401).

Some of these may be coder misses, especially in long sections. Others may reflect an unwritten rule the coders
apply, for example that trivial decisions do not count. **An expert look at the 54 false alarms would show which,
and would make every model's score more accurate, Claude's included.** All of them are in the dashboard's list of
sections that differ from the final label.

### 4.4 Long sections are where it goes wrong

| Quarter of the sample by length | Sections | Final Yes | Disagreements with the final label |
|---|---:|---:|---:|
| Shortest (up to 299 characters) | 754 | 2 | 4 (0.5%) |
| Second (299–672) | 749 | 11 | 16 (2.1%) |
| Third (672–1,618) | 747 | 32 | 27 (3.6%) |
| Longest (over 1,618) | 750 | 98 | 82 (11.1%) |

- **Most Yes sections, and most errors, are in the longest quarter.**
- **Running out of reply room.** A reply has a length limit of 768 tokens, about 550 words. A model that is still
  reasoning when it reaches the limit never writes its answer.
  - On the first try, 101 sections failed this way, 39 of them final Yes.
  - A plain retry rescued 25 of them.
  - A retry with twice the room (1,536 tokens) rescued 60 more.
- **Rescued answers are close to coin flips.** They matched the final label only 55% of the time (9 caught,
  19 missed, 19 false alarms, 38 correct No).
- **16 sections were never answered.** 11 of them are final Yes; their median length is 4,381 characters. They are
  reported as "no answer" and left out of the numbers above, not counted as No.

### 4.5 Stated confidence is a useful flag for review; P(Yes) is not

**Stated confidence.** Qwen reports 1.0 on 71% of its answers and never goes below 0.7, so the scale is coarse.
48 answers (1.6%) gave no usable confidence. The scale still tracks reliability:

| Stated confidence | Answers | Match the final label |
|---|---:|---:|
| 1.00 | 2,082 | 99.1% |
| 0.95–0.99 | 593 | 94.6% |
| 0.90–0.94 | 235 | 74.5% |
| 0.80–0.89 | 24 | 50.0% |

That makes it a workable triage rule if Qwen is used, with a person checking every answer stated below a
cut-off:

| A person checks answers stated… | Sections to read | Disagreements they would see |
|---|---:|---:|
| below 1.00, or with none | 902 (30%) | 110 of 129 (65 of 75 misses, 45 of 54 false alarms) |
| below 0.95, or with none | 309 (10%) | 78 of 129 |
| below 0.90, or with none | 74 (2.5%) | 18 of 129 |

**P(Yes), Qwen's token probability**, turned out not to be a graded score in this setup:

- **Almost all 0 or 1.** All but 1 of the 2,984 answers have P(Yes) below 0.01 or above 0.99: 2,870 sit below
  0.001 and 110 above 0.99. Every one of the 75 misses has P(Yes) below 0.01.
- **Why.** Qwen writes its reasoning before the label, so the decision is made in that text and the probability at
  the label is all but settled.
- **Moving the cut-off does not help.**
  - Lowering it from 0.5 to 0.01 changes nothing: 111 Yes calls either way.
  - Cutting at the point where Qwen says Yes as often as the final label (P(Yes) ≥ 0.00005) gives a catch rate of
    45% with 2.5% false alarms, and kappa 0.43 instead of 0.45.

### 4.6 Against one coder's first answer, Qwen is on par with a second coder

See section 2.4: kappa 0.33 against the coders' 0.34, a difference of −0.02 (interval −0.11 to +0.07). The coders'
first answers often disagree on Q1; the reconciled final label removes much of that noise.

---

## 5. What this suggests

1. **Test the prompt layout and the reasoning step properly before choosing a setup.** The 300-section check
   suggests the one-block layout, or dropping the "tempting-but-wrong reading" step, may catch far more Yes
   sections at a modest cost in false alarms. It needs a larger sample with more Yes sections.
2. **Have an expert review the 54 false alarms and a sample of the 75 misses.** This separates model errors from
   label issues and may sharpen the written definition (for example on rulemaking and on consultation within
   grant programmes).
3. **Start with the larger reply limit (1,536 tokens).** Short sections cost nothing extra, and most of the 101
   first-try failures would not have happened. The 16 longest sections may need more room still.
4. **If Qwen is used for coding, send every answer stated below 1.0 for review.** That is 30% of sections and
   catches 85% of the disagreements.
5. **The Claude run is next.** It is ready to start once its API key is in place. The dashboard and this report
   will then add Claude beside Qwen.

---

## 6. Read with care

- **Descriptive, not pre-registered.** This is a descriptive comparison, not a pre-registered test. The Q1 plan's
  gates are separate.
- **The reference is itself coding.** The catch and false-alarm rates measure agreement with the coders' final
  sheet, not with an absolute truth, and section 4.3 suggests the sheet has some errors.
- **Unanswered sections are left out.** The 16 sections Qwen never answered (11 of them final Yes) are excluded
  from the numbers, not counted as No.
- **Confidence is a claim, not a probability.** Stated confidence is the model's own claim, not a measured
  probability.
- **The keyword counts are crude.** The "participation word" counts in 4.2 and 4.3 come from a keyword flag. It
  marks passages; it does not judge them.
- **The layout check is small.** It covers 300 sections and only 19 Yes sections, so its numbers are less certain
  than the main ones.

---

## 7. Files

| File | What it holds |
|---|---|
| [`results/q1_panel3k/dashboard.html`](../results/q1_panel3k/dashboard.html) | The interactive dashboard, self-contained. Open it in any browser. |
| [`results/q1_panel3k/qwen_output.jsonl`](../results/q1_panel3k/qwen_output.jsonl) | Qwen's answer for each of the 3,000 sections, one per line: label, confidence, P(Yes), quoted passage, reason, full reply and number of attempts. |
| [`results/q1_panel3k/q1_two_coder_sheet.xlsx`](../results/q1_panel3k/q1_two_coder_sheet.xlsx) (and `.csv`) | One row per section with the models as coders: label, confidence, reason and quoted passage. The Claude columns are empty until its run. |
| [`docs/Q1_CLAUDE_VS_QWEN_PLAN.md`](Q1_CLAUDE_VS_QWEN_PLAN.md) | The study plan. |

To rebuild every number and the dashboard from the raw run files:

```bash
python eval/compare_models.py        # comparison.json, sheets, per-section CSVs, qwen_output.jsonl
python eval/compare_dashboard.py     # dashboard.html
```

## Glossary

- **Final label**: the label in the final, reconciled coding workbook. Yes when every coder's final answer is Yes.
- **First answers**: each coder's answer before the coders reconciled.
- **Catch rate (hit rate, recall)**: the share of final-Yes sections the model also calls Yes.
- **False-alarm rate**: the share of final-No sections the model calls Yes.
- **Precision**: the share of the model's Yes calls that are final Yes.
- **Kappa**: agreement corrected for the agreement chance alone would give. 0 = chance, 1 = perfect.
- **AC1**: a variant of kappa that is less affected by how rare Yes is.
- **95% interval**: the range a number would plausibly fall in with a different random draw of laws.
- **Token**: the unit a language model reads and writes, roughly three quarters of a word.
- **P(Yes)**: the model's internal probability for the word "Yes" at the moment it writes its label.
- **Stated confidence**: the 0–1 number the model writes about its own answer.
- **Chat layout / one-block layout**: the worked examples given as a back-and-forth conversation, or as one block
  of text.
