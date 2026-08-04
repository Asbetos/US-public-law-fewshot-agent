"""Constant prompt blocks for the Q6 few-shot kit (model-agnostic, stdlib only).

The definition encodes the rules distilled from the SME exemplars in
data/Q6_examples.csv ("Explain why" / "What makes it look tempting?").
"""

QUESTION_TEXT = "Does this section implicate physical construction?"

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

Be conservative: a matching keyword ("construction", "building", "maintenance",
"nuclear") is not enough on its own - check the SECTION against the
DEFINITION's inclusions and exclusions before answering.
"""

CONSTRUCTION_DEFINITION = """\
Construction is text related to building, repairing, maintaining, or
deconstructing anything anchored to land - highways, roads, bridges,
pipelines, dams, houses, buildings, monuments, and similar physical
infrastructure.

Answer "Yes" when the SECTION involves ANY of the following:
  - building, erecting, rehabilitating, or RECONSTRUCTING a structure on land,
    anywhere in the world (not just the United States); monuments and
    memorials count, however small;
  - repair or maintenance of real property - including appropriations that
    fund the "operation, maintenance, and repair" of buildings or facilities;
  - money authorised for construction (even if unspent), and exclusions from
    or limits on construction funding;
  - REGULATION of construction (e.g. issuing construction and safety
    standards), even though the section itself builds nothing;
  - construction that is merely considered, limited, defined, or excluded by
    the text (e.g. "the installation of X is not considered construction");
  - claims arising from construction; environmental restoration;
    weatherization.

Answer "No" for these common traps:
  - procurement or maintenance of MOVABLE things: planes, ships, cars,
    rockets, other conveyances, furniture, and equipment (e.g. beds,
    communications devices) - even when they are destined for a building;
  - transfer, sale, or disposal of land that only vaguely suggests a future
    or unspecified construction project;
  - funding the ONGOING OPERATIONS of a physical plant or facility (power,
    heating, fuel, supplies, personal services) where nothing is built or
    repaired on the real property itself;
  - a mere "building site" or land reference with no structure being built;
  - research, development, or planning that might lead to construction later;
  - establishing laboratories or programs, unless the text clearly authorises
    building a physical site; cybersecurity "infrastructure"; naming
    buildings; people who merely work at or around facilities;
  - the verb "construe" / "construed" (legal interpretation, not building).

The hardest distinction: funding that includes REPAIR of real property (e.g.
"operation, maintenance, and repair of property") is "Yes", but a facility's
pure operating budget (e.g. "maintenance and operation of the plant" covering
power, fuel, and services) is "No" - operating a building is not constructing
one.
"""
