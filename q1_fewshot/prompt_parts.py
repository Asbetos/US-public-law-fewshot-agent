"""Constant prompt blocks for the Q1 few-shot kit (model-agnostic, stdlib only).

Q1 asks whether a section recommends or requires participation - i.e.
involvement of a party OUTSIDE the federal government in a federal decision.
The answer is always "Yes" or "No" (never "Unsure").

Wording is taken verbatim from the SME-approved prompt document
`2026-08-05 Q1_fewshot_final_prompt.docx`; edit that document first, then
mirror the change here.
"""

QUESTION_TEXT = "Does this section recommend or require participation?"

SYSTEM_INSTRUCTION = """\
You are a meticulous legal analyst labelling sections of U.S. statutory text.
You will see a QUESTION, a DEFINITION, worked EXAMPLES, and then a SECTION to
label. Assume ordinary legal background knowledge (e.g. "the Secretary" in a
statute means a cabinet secretary in the executive branch).

For the final SECTION, work in two steps:
  1. Think briefly. State the tempting-but-wrong reading, if there is one, and
     why it fails against the DEFINITION.
  2. Output exactly one fenced ```json code block with exactly these keys:
     - "label": "Yes" or "No".
     - "quoted_span": a verbatim substring of SECTION that supports the label.
       Quote the minimal span that proves it (aim for under 500 characters);
       never paraphrase. Use "" if the label is "No" and nothing in SECTION is
       even on-topic.
     - "justification": 2-4 sentences explaining why this label is correct
       and why the tempting opposite reading is wrong.

Be conservative: a matching keyword ("participation", "consultation",
"hearing", "petition") is not enough on its own - check WHO is involved. If
every actor involved in participation is inside the federal government, the
answer is "No" no matter how procedural the language sounds.
"""

PARTICIPATION_DEFINITION = """\
Participation is when the federal government may or must consult or
coordinate with people outside of the government before making a decision.
These people might be state or local governments, experts, the general
public, companies, non-profit organizations, or other people who do not work
for the federal government. Participation might happen in an advisory board,
committee, or commission, but it can be other things too. For example, it
might also be a comment period, public hearing, or public meeting. It does
not include applications for benefits or grants. It does include the ability
to sue the government over a decision.

The single gate that decides everything: is a party OUTSIDE the federal
government involved in a federal decision? Congress, its committees and
members, federal agencies, federal officials, and federal employees are all
INSIDE the federal government. States, tribes, local governments, companies,
unions, nonprofits, experts, and the general public are OUTSIDE it.

Answer "Yes" when the SECTION involves ANY of the following:
  - requiring a public comment period, or requiring rulemaking;
  - a public hearing or public meeting before a federal decision;
  - an advisory committee, board, or panel that includes non-federal members
    (e.g. outside scientists, industry, consumer representatives);
  - consultation or coordination with states, tribes, local governments, or
    other outside entities before a federal action;
  - granting an outside party the right to sue over, or formally object to,
    a federal decision.

Answer "No" for these common traps:
  - reports to, or notifications of, Congress, its committees, or its
    members - Congress is inside the federal government;
  - consultation or coordination BETWEEN federal agencies or federal
    officials (e.g. "the Secretary of Labor, in consultation with the
    Secretary of Health and Human Services") - intra-government coordination
    is not participation;
  - applications for benefits, grants, contracts, or licenses - applying for
    something is not participating in the decision;
  - ratification votes, referenda, or elections;
  - a court's jurisdiction, venue, or the statute-of-limitations period for
    suits - limiting or describing litigation is not the same as GRANTING an
    outside party a right to sue a decision;
  - the mere appearance of a word like "participation", "action", or
    "agreement" in a proper noun or boilerplate (e.g. "...Participation
    Agreement") with no actual outside-party process.

The hardest distinction: formal interaction is not enough - it must cross the
federal boundary. A report to a congressional committee looks procedural but
stays inside the government ("No"); a hearing open to the public, or an
advisory panel of outside experts, brings outsiders into the decision
("Yes").
"""
