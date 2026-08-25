<!-- GENERATED FILE - do not hand-edit. -->
<!-- Regenerate: python q6_fewshot/build_prompt.py --write-markdown -->

# Q6 Few-Shot Prompt (rendered)

Canonical data: `examples.json`; renderers: `build_prompt.py` (`build_messages()` for chat models, `build_flat_prompt()` for completion models). Everything below is the flat rendering.

---

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

DEFINITION:
Construction is text related to building, repairing, maintaining, or
deconstructing anything anchored to land or seabed - highways, roads,
bridges, pipelines, dams, houses, buildings, monuments, and similar
physical infrastructure.

Answer "Yes" when the SECTION involves ANY of the following:
  - building, erecting, rehabilitating, or RECONSTRUCTING a structure on land,
    anywhere in the world (not just the United States); monuments and
    memorials count, however small;
  - repair or maintenance of real property - including appropriations that
    fund the "operation, maintenance, and repair" (or similar language) of
    buildings or facilities;
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
    communications devices) - even when they are destined to be in a building;
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


### Example 1
QUESTION:
Does this section implicate physical construction?

SECTION:
The following sections of title 37, United States Code, are amended by striking “December 31, 2016” and inserting “December 31, 2017”:
  (1) Section 312(f), relating to special pay for nuclear-qualified officers extending period of active service. 
  (2) Section 312b(c), relating to nuclear career accession bonus. 
  (3) Section 312c(d), relating to nuclear career annual incentive bonus.

Temptation: It looks a small bit like construction because it refers to "nuclear," but this is not construction because these are people doing nuclear jobs, not nuclear plants.
Resolution: This section has no reference to physical construction, and reference to military does not necessarily implicate physical construction, so we do not include it.
```json
{
  "label": "No",
  "quoted_span": "The following sections of title 37, United States Code, are amended by striking “December 31, 2016” and inserting “December 31, 2017”:\n  (1) Section 312(f), relating to special pay for nuclear-qualified officers extending period of active service. \n  (2) Section 312b(c), relating to nuclear career accession bonus. \n  (3) Section 312c(d), relating to nuclear career annual incentive bonus.",
  "justification": "This section has no reference to physical construction, and reference to military does not necessarily implicate physical construction, so we do not include it. It looks a small bit like construction because it refers to \"nuclear,\" but this is not construction because these are people doing nuclear jobs, not nuclear plants."
}
```

### Example 2
QUESTION:
Does this section implicate physical construction?

SECTION:
(a) In General.—Subject to the availability of appropriations, the Secretary, acting through the Commissioner of Reclamation, shall plan, design, and construct 1 or more facilities to store water and support irrigation on the Reservation in accordance with 1 or more agreements between the Secretary and the Tribe. 
  (b) Lead Agency.—The Bureau of Reclamation shall serve as the lead agency with respect to any activity to design and construct the irrigation development and water storage facilities described in subsection (c). 
  (c) Scope.—
  (1) In general.—The scope of the design and construction under this section shall be as generally described in the document entitled “Blackfeet Water Storage, Development, and Project Report”, prepared by DOWL HKM, and dated March 13, 2013, as modified and agreed to by the Secretary and the Tribe, subject to the condition that, before commencing final design and construction activities, the Secretary shall—
  (A) review the design of the proposed construction; 
  (B) perform value engineering analyses; and 
  (C) perform appropriate Federal compliance activities. 
  (2) Modification.—The Secretary may modify the scope of construction for the projects described in the document referred to in paragraph (1), if—
  (A) the modified project is—
  (i) similar in purpose to the proposed projects; and 
  (ii) consistent with the purposes of this subtitle; and 
  (B) the Secretary has consulted with the Tribe regarding any modification. 
  (3) Negotiation with tribe.—On the basis of the review described in paragraph (1)(A), the Secretary shall negotiate with the Tribe appropriate changes, if any, to the final design—
  (A) to ensure that the final design meets applicable industry standards; 
  (B) to improve the cost-effectiveness of any construction; and 
  (C) to ensure that the projects may be constructed using only the amounts made available under section 3718. 
  (d) Nonreimbursability of Costs.—All costs incurred by the Secretary in carrying out this section shall be nonreimbursable. 
  (e) Funding.—The total amount of obligations incurred by the Secretary in carrying out this section, prior to any adjustment provided for in section 3718, shall not exceed $87,300,000. 
  (f) Ownership by Tribe.—Title to all facilities rehabilitated or constructed under this section shall be held by the Tribe, except that title to the Birch Creek Unit of the Blackfeet Indian Irrigation Project shall remain with the Bureau of Indian Affairs. 
  (g) Administration.—The Commissioner of Reclamation and the Tribe shall negotiate the cost of any oversight activity carried out by the Bureau of Reclamation under any agreement entered into under this section, subject to the condition that the total 
 cost for the oversight shall not exceed 4 percent of the total costs incurred under this section. 
  (h) OM&R Costs.—The Federal Government shall have no obligation to pay for the OM&R costs for the facilities rehabilitated or constructed under this section. 
  (i) Project Efficiencies.—If the total cost of planning, design, and construction activities relating to the projects described in this section results in cost savings and is less than the amounts authorized to be obligated, the Secretary, at the request of the Tribe, may—
  (1) use those cost savings to carry out a project described in section 3707(d), 3710, 3711, or 3713; or 
  (2) deposit those cost savings to the Blackfeet OM&R Trust Account. 
  (j) Applicability of ISDEAA.—At the request of the Tribe, and in accordance with the Indian Self-Determination and Education Assistance Act (25 U.S.C. 5301 et seq.), the Secretary shall enter into 1 or more agreements with the Tribe to carry out this section.

Temptation: A coder might be tempted to reject this case because it does not allocate funds or discuss a particular project.
Resolution: We classify this as construction because it discusses the construction of water facilities for storage and irrigation, which is physical construction.
```json
{
  "label": "Yes",
  "quoted_span": "(a) In General.—Subject to the availability of appropriations, the Secretary, acting through the Commissioner of Reclamation, shall plan, design, and construct 1 or more facilities to store water and support irrigation on the Reservation in accordance with 1 or more agreements between the Secretary and the Tribe. ",
  "justification": "We classify this as construction because it discusses the construction of water facilities for storage and irrigation, which is physical construction. A coder might be tempted to reject this case because it does not allocate funds or discuss a particular project."
}
```

### Example 3
QUESTION:
Does this section implicate physical construction?

SECTION:
(a) General Support.—
  (1) Use of funds.—During a covered public health emergency, the Secretary of Veterans Affairs may use amounts appropriated or otherwise made available to the Department of Veterans Affairs to carry out sections 2011, 2012, 2031, and 2061 of title 38, United States Code, to provide to homeless veterans and veterans participating in the program carried out under section 8(o)(19) of the United States Housing Act of 1937 (42 U.S.C. 1437f(o)(19)) (commonly referred to as “HUD-VASH”), as the Secretary determines is needed, the following:
  (A) Assistance required for safety and survival (such as food, shelter, clothing, blankets, and hygiene items). 
  (B) Transportation required to support stability and health (such as for appointments with service providers, conducting housing searches, and obtaining food and supplies). 
  (C) Communications equipment and services (such as tablets, smartphones, disposable phones, and related service plans) required to support stability and health (such as maintaining contact with service providers, prospective landlords, and family). 
  (D) Such other assistance as the Secretary determines is needed. 
  (2) Homeless veterans on land of the department.—
  (A) Collaboration.—During a covered public health emergency, to the extent possible, the Secretary may collaborate with one or more organizations to manage use of land of the Department for homeless veterans for living and sleeping. 
  (B) Elements.—Collaboration under subparagraph (A) may include the provision by either the Secretary or the organization of food services and security for property, buildings, and other facilities owned or controlled by the Department. 
  (b) Grant and Per Diem Program.—
  (1) Limits on rates for per diem payments.—Section 20013(b) of the Coronavirus Aid, Relief, and Economic Security Act (38 U.S.C. 2011 note; Public Law 116–136) is amended—
  (A) by redesignating paragraphs (1) and (2) as subparagraphs (A) and (B), respectively; 
  (B) in the matter preceding subparagraph (A), as so redesignated, by inserting “(1)” before “In the case”; and 
  (C) by adding at the end the following:“(2) If the Secretary waives any limit on grant amounts or rates for per diem payments under paragraph (1), notwithstanding section 2012(a)(2)(B) of such title, the maximum rate for per diem payments described in paragraph (1)(B) shall be three times the rate authorized for State homes for domiciliary care under section 1741 of such title.”. 
  (2) Modification of funding limits for grants.—Subsection (c)(2) of section 2011 of title 38, United States Code, shall not apply to any grant awarded during a covered public health emergency under such section for a project described in subsection (b)(1) of such section. 
  (3) Use of per diem payments.—During a covered public health emergency, a recipient of a grant or an eligible entity under the grant and per diem program of the Department (in this subsection referred to as the “program”) may use per diem payments under sections 2012 and 2061 of title 38, United States Code, to provide assistance required for safety and survival (such as food, shelter, clothing, blankets, and hygiene items) for—
  (A) homeless veterans; and 
  (B) formerly homeless veterans residing in a facility operated wholly or in part by such a recipient or eligible entity receiving per diem payments under section 2012 of such title. 
  (4) Additional transitional housing.—
  (A) In general.—During a covered public health emergency, under the program, the Secretary may provide amounts for additional transitional housing beds to facilitate access to housing and services provided to homeless veterans. 
  (B) Notice; competition; period of performance.—The Secretary may provide amounts under subparagraph (A)—
  (i) without notice or competition; and 
  (ii) for a period of performance determined by the Secretary. 
  (5) Inspections and life safety code requirements.—
  (A) In general.—During a covered public health emergency, the Secretary may waive any requirement under subsection (b) or (c) of section 2012 of title 38, United States Code, in order to allow the recipient of a grant or an eligible entity under the program—
  (i) to quickly identify temporary alternate sites of care for homeless veterans that are suitable for habitation; 
  (ii) to facilitate social distancing or isolation needs; or 
  (iii) to facilitate activation or continuation of a program for which a grant has been awarded. 
  (B) Limitation.—The Secretary may waive a requirement pursuant to the authority provided by subparagraph (A) with respect to a facility of a recipient of a grant or an eligible entity under the program only if the facility meets applicable local safety requirements, including fire safety requirements. 
  (6) Disposition of property relating to grants.—During a covered public health emergency, if the recipient of a grant awarded before or during such emergency under section 2011 of title 38, United States Code, for a project described in subsection (b)(1) of such section is no longer providing services in accordance with the terms of the grant, the recipient shall not be subject during such emergency to any property disposition requirements relating to the grant under subsection (c) or (f) of section 61.67 of title 38, Code of Federal Regulations, section 200.311(c) of title 2, Code of Federal Regulations, or successor regulations. 
  (c) Inspection and Life Safety Code Requirements for Therapeutic Housing.—
  (1) In general.—During a covered public health emergency, the Secretary may waive any inspection or life safety code requirement under subsection (c) of section 2032 of title 38, United States Code—
  (A) to allow quick identification of temporary alternate sites of care for homeless veterans that are suitable for habitation; 
  (B) to facilitate social distancing or isolation needs; or 
  (C) to facilitate the operation of housing under such section. 
  (2) Limitation.—The Secretary may waive a requirement pursuant to the authority provided by paragraph (1) with respect to a residence or facility referred to in such section 2032 only if the residence or facility, as the case may be, meets applicable local safety requirements, including fire safety requirements. 
  (d) Access to Department of Veterans Affairs Telehealth Services.—To the extent practicable, during a covered public health emergency, the Secretary shall ensure that veterans participating in or receiving services from a program under chapter 20 of title 38, United States Code, have access to telehealth services to which such veterans are eligible under the laws administered by the Secretary, including by ensuring that telehealth capabilities are available to—
  (1) such veterans; 
  (2) case managers of the Department of programs for homeless veterans authorized under such chapter; and 
  (3) community-based service providers for homeless veterans receiving funds from the Department through grants or contracts. 
  (e) Definitions.—In this section:
  (1) Covered public health emergency.—The term “covered public health emergency” means an emergency with respect to COVID–19 declared by a Federal, State, or local authority. 
  (2) Homeless veteran; veteran.—The terms “homeless veteran” and “veteran” have the meanings given those terms in section 2002 of title 38, United States Code. 
  (3) Telehealth.—
  (A) In general.—The term “telehealth” means the use of electronic information and telecommunications technologies to support and promote long-distance clinical 
 health care, patient and professional health-related education, public health, and health administration. 
  (B) Technologies.—For purposes of subparagraph (A), “telecommunications technologies” include video conferencing, the internet, streaming media, and terrestrial and wireless communications.

Temptation: It looks like construction because it has to do with putting things in a physical location.
Resolution: This covers procurement of physical objects for physical locations, here beds, but it does not implicate construction of any structures on land, so we do not include it.
```json
{
  "label": "No",
  "quoted_span": "(A) In general.—During a covered public health emergency, under the program, the Secretary may provide amounts for additional transitional housing beds to facilitate access to housing and services provided to homeless veterans.",
  "justification": "This covers procurement of physical objects for physical locations, here beds, but it does not implicate construction of any structures on land, so we do not include it. It looks like construction because it has to do with putting things in a physical location."
}
```

### Example 4
QUESTION:
Does this section implicate physical construction?

SECTION:
Not to exceed $5,000,000 of the amounts appropriated by this title under the heading “Operation and Maintenance, Army” may be used, notwithstanding any other provision of law, to fund the Commanders’ Emergency Response Program (CERP), for the purpose of enabling military commanders in Afghanistan to respond to urgent, small-scale, humanitarian relief and reconstruction requirements within their areas of responsibility: Provided, That each project (including any ancillary or related elements in connection with such project) executed under this authority shall not exceed $2,000,000: Provided further, That not later than 45 days after the end of each 6 months of the fiscal year, the Secretary of Defense shall submit to the congressional defense committees a report regarding the source of funds and the allocation and use of funds during that 6-month period that were made available pursuant to the authority provided in this section or under any other provision of law for the purposes described herein: Provided further, That, not later than 30 days after the end of each fiscal year quarter, the Army shall submit to the congressional defense committees quarterly commitment, obligation, and expenditure data for the CERP in Afghanistan: Provided further, That, not less than 15 days before making funds available pursuant to the authority provided in this section or under any other provision of law for the purposes described herein for a project with a total anticipated cost for completion of $500,000 or more, the Secretary shall submit to the congressional defense committees a written notice containing each of the following:
  (1) The location, nature and purpose of the proposed project, including how the project is intended to advance the military campaign plan for the country in which it is to be carried out. 
  (2) The budget, implementation timeline with milestones, and completion date for the proposed project, including any other CERP funding that has been or is anticipated to be contributed to the completion of the project. 
  (3) A plan for the sustainment of the proposed project, including the agreement with either the host nation, a non-Department of Defense agency of the United States Government or a third-party contributor to finance the sustainment of the activities and maintenance of any equipment or facilities to be provided through the proposed project.

Temptation: A coder might be tempted to reject this example because it refers to construction not in the United States. We count construction anywhere in the world.
Resolution: "Reconstruction" is sufficient to qualify as "implicating construction" by our definition. We count construction even when it is not in the United States.
```json
{
  "label": "Yes",
  "quoted_span": "Not to exceed $5,000,000 of the amounts appropriated by this title under the heading “Operation and Maintenance, Army” may be used, notwithstanding any other provision of law, to fund the Commanders’ Emergency Response Program (CERP), for the purpose of enabling military commanders in Afghanistan to respond to urgent, small-scale, humanitarian relief and reconstruction requirements within their areas of responsibility",
  "justification": "\"Reconstruction\" is sufficient to qualify as \"implicating construction\" by our definition. We count construction even when it is not in the United States. A coder might be tempted to reject this example because it refers to construction not in the United States. We count construction anywhere in the world."
}
```

### Example 5
QUESTION:
Does this section implicate physical construction?

SECTION:
The President may at any time in his discretion, transfer, or cause to be transferred, to the Administrator any right, title, or interest held by the Federal Government or any department or agency thereof in any land (including buildings thereon) which is surplus to the needs of the Government and which a local public agency certifies will be within the area of a project being planned by it. When such land is sold to the local public agency by the Administrator, it shall be sold at a price equal to its fair market value, and the proceeds from such sale shall be covered into the Treasury as miscellaneous receipts.

Temptation: The section vaguely suggests future construction on the land that the government is disposing of.
Resolution: This references land that may be used in future construction, but does not refer to any specific construction project.
```json
{
  "label": "No",
  "quoted_span": "The President may at any time in his discretion, transfer, or cause to be transferred, to the Administrator any right, title, or interest held by the Federal Government or any department or agency thereof in any land (including buildings thereon) which is surplus to the needs of the Government and which a local public agency certifies will be within the area of a project being planned by it. ",
  "justification": "This references land that may be used in future construction, but does not refer to any specific construction project. The section vaguely suggests future construction on the land that the government is disposing of."
}
```

### Example 6
QUESTION:
Does this section implicate physical construction?

SECTION:
Under the heading “Federal Emergency Management Agency—Federal Assistance”, for grants under paragraphs (1) and (2), the installation of communications towers is not considered construction of a building or other physical facility.

Temptation: A coder might reject this case because it limits when construction can occur, rather than requiring or funding construction.
Resolution: In response to whether the section "implicates construction," we answer yes even when construction is merely considered or limited, as in this case.
```json
{
  "label": "Yes",
  "quoted_span": "Under the heading “Federal Emergency Management Agency—Federal Assistance”, for grants under paragraphs (1) and (2), the installation of communications towers is not considered construction of a building or other physical facility.",
  "justification": "In response to whether the section \"implicates construction,\" we answer yes even when construction is merely considered or limited, as in this case. A coder might reject this case because it limits when construction can occur, rather than requiring or funding construction."
}
```

### Example 7
QUESTION:
Does this section implicate physical construction?

SECTION:
(a) Of the funds made available in this Act, not less than $43,100,000 shall be available for the Civil Air Patrol Corporation, of which—
  (1) $30,800,000 shall be available from “Operation and Maintenance, Air Force” to support Civil Air Patrol Corporation operation and maintenance, readiness, counter-drug activities, and drug demand reduction activities involving youth programs; 
  (2) $10,600,000 shall be available from “Aircraft Procurement, Air Force”; and 
  (3) $1,700,000 shall be available from “Other Procurement, Air Force” for vehicle procurement. 
  (b) The Secretary of the Air Force should waive reimbursement for any funds used by the Civil Air Patrol for counter-drug activities in support of Federal, State, and local government agencies.

Temptation: It looks like construction because this section includes the word "maintenance." If this referred to buildings, it would be construction by our definition. However, this is maintenance for motorized vehicles, so it does not count.
Resolution: While this section refers to maintenance of physical objects, we do not count as "construction" the building or maintenance of boats, planes, or other motor vehicles. We are interested exlusively in construction on real property.
```json
{
  "label": "No",
  "quoted_span": "(a) Of the funds made available in this Act, not less than $43,100,000 shall be available for the Civil Air Patrol Corporation, of which—\n  (1) $30,800,000 shall be available from “Operation and Maintenance, Air Force” to support Civil Air Patrol Corporation operation and maintenance, readiness, counter-drug activities, and drug demand reduction activities involving youth programs; \n  (2) $10,600,000 shall be available from “Aircraft Procurement, Air Force”; and \n  (3) $1,700,000 shall be available from “Other Procurement, Air Force” for vehicle procurement. \n  (b) The Secretary of the Air Force should waive reimbursement for any funds used by the Civil Air Patrol for counter-drug activities in support of Federal, State, and local government agencies.",
  "justification": "While this section refers to maintenance of physical objects, we do not count as \"construction\" the building or maintenance of boats, planes, or other motor vehicles. We are interested exlusively in construction on real property. It looks like construction because this section includes the word \"maintenance.\" If this referred to buildings, it would be construction by our definition. However, this is maintenance for motorized vehicles, so it does not count."
}
```

### Example 8
QUESTION:
Does this section implicate physical construction?

SECTION:
That the American Battle Monuments Commission is authorized to provide for the erection of a memorial to the late John J. Pershing, General of the Armies of the United States, and to the officers and men under his command, such memorial to be erected—
 
  (1) 
 in accordance with a design to be submitted by the American Battle Monuments Commission and approved by the President’s Temporary Commission on Pennsylvania Avenue or its successor in interest; and
  
  (2) 
 on that parcel of federally owned land in the northwest section of the District of Columbia, bounded on the north by Pennsylvania Avenue, on the south by E Street, on the west by Fifteenth Street, and on the east by Fourteenth Street.

Temptation: A coder might reject this case because the scope of the construction -- a monument -- is quite small.
Resolution: As our definition for "implicate construction" includes building structures on land, we include construction of monuments.
```json
{
  "label": "Yes",
  "quoted_span": "That the American Battle Monuments Commission is authorized to provide for the erection of a memorial to the late John J. Pershing, General of the Armies of the United States,",
  "justification": "As our definition for \"implicate construction\" includes building structures on land, we include construction of monuments. A coder might reject this case because the scope of the construction -- a monument -- is quite small."
}
```

### Example 9
QUESTION:
Does this section implicate physical construction?

SECTION:
For lighting, heating, and power (including the purchase of electrical energy) for the Capitol, Senate and House Office Buildings, Supreme Court Building, Congressional Library Buildings, and the grounds about the same, Botanic Garden, Senate garage, and for airconditioning refrigeration not supplied from plants in any of such buildings; for heating the Government Printing Office, Washington City Post Office, and Folger Shakespeare Library, reimbursement for which shall be made and covered into the Treasury; personal and other services, fuel, oil, materials, waterproof wearing apparel, and all other necessary expenses in connection with the maintenance and operation of the plant; $2,778,000: Provided, That not to exceed $25,000 of the unobligated balance of the appropriation under this head for the fiscal year 1966 is hereby continued available until June 30, 1967.

Temptation: The example suggests physical construction with the word maintenance and refers to physical property on real estate.
Resolution: This act provides funding for ongoing operations of a physical plant. It therefore does not fit our definition of construction because ongoing operations do not necessarily include contructing anything on property.
```json
{
  "label": "No",
  "quoted_span": "For lighting, heating, and power (including the purchase of electrical energy) for the Capitol, Senate and House Office Buildings, Supreme Court Building, Congressional Library Buildings, and the grounds about the same, Botanic Garden, Senate garage, and for airconditioning refrigeration not supplied from plants in any of such buildings; for heating the Government Printing Office, Washington City Post Office, and Folger Shakespeare Library, reimbursement for which shall be made and covered into the Treasury; personal and other services, fuel, oil, materials, waterproof wearing apparel, and all other necessary expenses in connection with the maintenance and operation of the plant; $2,778,000: Provided, That not to exceed $25,000 of the unobligated balance of the appropriation under this head for the fiscal year 1966 is hereby continued available until June 30, 1967.",
  "justification": "This act provides funding for ongoing operations of a physical plant. It therefore does not fit our definition of construction because ongoing operations do not necessarily include contructing anything on property. The example suggests physical construction with the word maintenance and refers to physical property on real estate."
}
```

### Example 10
QUESTION:
Does this section implicate physical construction?

SECTION:
Section 604 (42 U.S.C. 5403) is amended—

    (1) by striking subsections (a) and (b) and inserting the following:

“(a) Establishment.—
“(1) Authority.—The Secretary shall establish, by order, appropriate Federal manufactured home construction and safety standards, each of which—
“(A) shall.—
“(i) be reasonable and practical;
“(ii) meet high standards of protection consistent with the purposes of this title; and
“(iii) be performance-based and objectively stated, unless clearly inappropriate; and
“(B) except as provided in subsection (b), shall be established in accordance with the consensus standards development process.
“(2) Consensus standards and regulatory development process.—
“(A) Initial agreement.—Not later than 180 days after the date of the enactment of the Manufactured Housing Improvement Act of 2000, the Secretary shall enter into a contract with an administering organization. The contractual agreement shall—
“(i) terminate on the date on which a contract is entered into under subparagraph (B); and
“(ii) require the administering organization to—
“(I) recommend the initial members of the consensus committee under paragraph (3);
“(II) administer the consensus standards development process until the termination of that agreement; and

“(III) administer the consensus development and interpretation process for procedural and enforcement regulations and regulations specifying the permissible scope and conduct of monitoring until the termination of that agreement.
“(B) Competitively procured contract.—Upon the expiration of the 4-year period beginning on the date on which all members of the consensus committee are appointed under paragraph (3), the Secretary shall, using competitive procedures (as such term is defined in section 4 of the Office of Federal Procurement Policy Act), enter into a competitively awarded contract with an administering organization. The administering organization shall administer the consensus process for the development and interpretation of the Federal standards, the procedural and enforcement regulations, and regulations specifying the permissible scope and conduct of monitoring, in accordance with this title.
“(C) Performance review.—The Secretary—
“(i) shall periodically review the performance of the administering organization; and
“(ii) may replace the administering organization with another qualified technical or building code organization, pursuant to competitive procedures, if the Secretary determines in writing that the administering organization is not fulfilling the terms of the agreement or contract to which the administering organization is subject or upon the expiration of the agreement or contract.
“(3) Consensus committee.—
“(A) Purpose.—There is established a committee to be known as the ‘consensus committee’, which shall, in accordance with this title—
“(i) provide periodic recommendations to the Secretary to adopt, revise, and interpret the Federal manufactured housing construction and safety standards in accordance with this subsection;
“(ii) provide periodic recommendations to the Secretary to adopt, revise, and interpret the procedural and enforcement regulations, including regulations specifying the permissible scope and conduct of monitoring in accordance with subsection (b);
“(iii) be organized and carry out its business in a manner that guarantees a fair opportunity for the expression and consideration of various positions and for public participation; and
“(iv) be deemed to be an advisory committee not composed of Federal employees.
“(B) Membership.—The consensus committee shall be composed of—
“(i) twenty-one voting members appointed by the Secretary, after consideration of the recommendations of the administering organization, from among individuals who are qualified by background and experience to participate in the work of the consensus committee; and

“(ii) one nonvoting member appointed by the Secretary to represent the Secretary on the consensus committee.
“(C) Disapproval.—The Secretary shall state, in writing, the reasons for failing to appoint any individual recommended under paragraph (2)(A)(ii)(I).
“(D) Selection procedures and requirements.—Each member of the consensus committee shall be appointed in accordance with selection procedures, which shall be based on the procedures for consensus committees promulgated by the American National Standards Institute (or successor organization), except that the American National Standards Institute interest categories shall be modified for purposes of this paragraph to ensure equal representation on the consensus committee of the following interest categories:
“(i) Producers.—Seven producers or retailers of manufactured housing.
“(ii) Users.—Seven persons representing consumer interests, such as consumer organizations, recognized consumer leaders, and owners who are residents of manufactured homes.
“(iii) General interest and public officials.—Seven general interest and public official members.
“(E) Balancing of interests.—
“(i) In general.—In order to achieve a proper balance of interests on the consensus committee, the Secretary, in appointing the members of the consensus committee—
“(I) shall ensure that all directly and materially affected interests have the opportunity for fair and equitable participation without dominance by any single interest; and
“(II) may reject the appointment of any one or more individuals in order to ensure that there is not dominance by any single interest.
“(ii) Dominance defined.—In this subparagraph, the term ‘dominance’ means a position or exercise of dominant authority, leadership, or influence by reason of superior leverage, strength, or representation.
“(F) Additional qualifications.—
“(i) Financial independence.—No individual appointed under subparagraph (D)(ii) shall have, and three of the individuals appointed under subparagraph (D)(iii) shall not have—
“(I) a significant financial interest in any segment of the manufactured housing industry; or
“(II) a significant relationship to any person engaged in the manufactured housing industry.
“(ii) Post-employment ban.—Each individual described in clause (i) shall be subject to a ban disallowing compensation from the manufactured housing industry during the period of, and during the 1-year following, the membership of the individual on the consensus committee.
“(G) Meetings.—

“(i) Notice; open to public.—The consensus committee shall provide advance notice of each meeting of the consensus committee to the Secretary and cause to be published in the Federal Register advance notice of each such meeting. All meetings of the consensus committee shall be open to the public.
“(ii) Reimbursement.—Members of the consensus committee in attendance at meetings of the consensus committee shall be reimbursed for their actual expenses as authorized by section 5703 of title 5, United States Code, for persons employed intermittently in Government service.
“(H) Administration.—The consensus committee and the administering organization shall—
“(i) operate in conformance with the procedures established by the American National Standards Institute for the development and coordination of American National Standards; and
“(ii) apply to the American National Standards Institute and take such other actions as may be necessary to obtain accreditation from the American National Standards Institute.
“(I) Staff And technical support.—The administering organization shall, upon the request of the consensus committee—
“(i) provide reasonable staff resources to the consensus committee; and
“(ii) furnish technical support in a timely manner to any of the interest categories described in subparagraph (D) represented on the consensus committee, if—
“(I) the support is necessary to ensure the informed participation of the consensus committee members; and
“(II) the costs of providing the support are reasonable.
“(J) Date of initial appointments.—The initial appointments of all the members of the consensus committee shall be completed not later than 90 days after the date on which a contractual agreement under paragraph (2)(A) is entered into with the administering organization.
“(4) Revisions of standards.—
“(A) In general.—Beginning on the date on which all members of the consensus committee are appointed under paragraph (3), the consensus committee shall, not less than once during each 2-year period—
“(i) consider revisions to the Federal manufactured home construction and safety standards; and
“(ii) submit proposed revised standards, if approved in a vote of the consensus committee by two-thirds of the members, to the Secretary in the form of a proposed rule, including an economic analysis.
“(B) Publication of proposed revised standards.—
“(i) Publication by the secretary.—The consensus committee shall provide a proposed revised 
standard under subparagraph (A)(ii) to the Secretary who shall, not later than 30 days after receipt, cause such proposed revised standard to be published in the Federal Register for notice and comment in accordance with section 553 of title 5, United States Code. Unless clause (ii) applies, the Secretary shall provide an opportunity for public comment on such proposed revised standard in accordance with such section 553 and any such comments shall be submitted directly to the consensus committee, without delay.
“(ii) Publication of rejected proposed revised standards.—If the Secretary rejects the proposed revised standard, the Secretary shall cause to be published in the Federal Register the rejected proposed revised standard, the reasons for rejection, and any recommended modifications set forth.
“(C) Presentation of public comments; publication of recommended revisions.—
“(i) Presentation.—Any public comments, views, and objections to a proposed revised standard published under subparagraph (B) shall be presented by the Secretary to the consensus committee upon their receipt and in the manner received, in accordance with procedures established by the American National Standards Institute.
“(ii) Publication by the secretary.—The consensus committee shall provide to the Secretary any revision proposed by the consensus committee, which the Secretary shall, not later than 30 calendar days after receipt, cause to be published in the Federal Register a notice of the recommended revisions of the consensus committee to the standards, a notice of the submission of the recommended revisions to the Secretary, and a description of the circumstances under which the proposed revised standards could become effective.
“(iii) Publication of rejected proposed revised standards.—If the Secretary rejects the proposed revised standard, the Secretary shall cause to be published in the Federal Register the rejected proposed revised standard, the reasons for rejection, and any recommended modifications set forth.
“(5) Review by the secretary.—
“(A) In general.—The Secretary shall either adopt, modify, or reject a standard, as submitted by the consensus committee under paragraph (4)(A).
“(B) Timing.—Not later than 12 months after the date on which a standard is submitted to the Secretary by the consensus committee, the Secretary shall take action regarding such standard under subparagraph (C).
“(C) Procedures.—If the Secretary—
“(i) adopts a standard recommended by the consensus committee, the Secretary shall—
“(I) issue a final order without further rulemaking; and
“(II) cause the final order to be published in the Federal Register;

“(ii) determines that any standard should be rejected, the Secretary shall—
“(I) reject the standard; and
“(II) cause to be published in the Federal Register a notice to that effect, together with the reason or reasons for rejecting the proposed standard; or
“(iii) determines that a standard recommended by the consensus committee should be modified, the Secretary shall—
“(I) cause to be published in the Federal Register the proposed modified standard, together with an explanation of the reason or reasons for the determination of the Secretary; and
“(II) provide an opportunity for public comment in accordance with section 553 of title 5, United States Code.
“(D) Final order.—Any final standard under this paragraph shall become effective pursuant to subsection (c).
“(6) Failure to act.—If the Secretary fails to take final action under paragraph (5) and to cause notice of the action to be published in the Federal Register before the expiration of the 12-month period beginning on the date on which the proposed revised standard is submitted to the Secretary under paragraph (4)(A)—
“(A) the Secretary shall appear in person before the appropriate housing and appropriations subcommittees and committees of the House of Representatives and the Senate (referred to in this paragraph as the ‘committees’) on a date or dates to be specified by the committees, but in no event later than 30 days after the expiration of that 12-month period, and shall state before the committees the reasons for failing to take final action as required under paragraph (5); and
“(B) if the Secretary does not appear in person as required under subparagraph (A), the Secretary shall thereafter, and until such time as the Secretary does appear as required under subparagraph (A), be prohibited from expending any funds collected under authority of this title in an amount greater than that collected and expended in the fiscal year immediately preceding the date of the enactment of the Manufactured Housing Improvement Act of 2000, indexed for inflation as determined by the Congressional Budget Office.
“(b) Other Orders.—
“(1) Regulations.—The Secretary may issue procedural and enforcement regulations and revisions to existing regulations as necessary to implement the provisions of this title. The consensus committee may submit to the Secretary proposed procedural and enforcement regulations and recommendations for the revision of such regulations.
“(2) Interpretative bulletins.—The Secretary may issue interpretative bulletins to clarify the meaning of any Federal manufactured home construction and safety standard or procedural and enforcement regulation. The consensus committee may submit to the Secretary proposed interpretative bulletins 
to clarify the meaning of any Federal manufactured home construction and safety standard or procedural and enforcement regulation.
“(3) Review by consensus committee.—Before issuing a procedural or enforcement regulation or an interpretative bulletin—
“(A) the Secretary shall.—
“(i) submit the proposed procedural or enforcement regulation or interpretative bulletin to the consensus committee; and
“(ii) provide the consensus committee with a period of 120 days to submit written comments to the Secretary on the proposed procedural or enforcement regulation or the interpretative bulletin; and
“(B) if the Secretary rejects any significant comment provided by the consensus committee under subparagraph (A), the Secretary shall provide a written explanation of the reasons for the rejection to the consensus committee; and
“(C) following compliance with subparagraphs (A) and (B), the Secretary shall—
“(i) cause the proposed regulation or interpretative bulletin and the consensus committee’s written comments, along with the Secretary’s response thereto, to be published in the Federal Register; and
“(ii) provide an opportunity for public comment in accordance with section 553 of title 5, United States Code.
“(4) Required action.—Not later than 120 days after the date on which the Secretary receives a proposed regulation or interpretative bulletin submitted by the consensus committee, the Secretary shall—
“(A) approve the proposal and cause the proposed regulation or interpretative bulletin to be published for public comment in accordance with section 553 of title 5, United States Code; or
“(B) reject the proposed regulation or interpretative bulletin and—
“(i) provide to the consensus committee a written explanation of the reasons for rejection; and
“(ii) cause to be published in the Federal Register the rejected proposed regulation or interpretive bulletin, the reasons for rejection, and any recommended modifications set forth.
“(5) Authority to act and emergency.—If the Secretary determines, in writing, that such action is necessary to address an issue on which the Secretary determines that the consensus committee has not made a timely recommendation following a request by the Secretary, or in order to respond to an emergency that jeopardizes the public health or safety, the Secretary may issue an order that is not developed under the procedures set forth in subsection (a) or in this subsection, if the Secretary—
“(A) provides to the consensus committee a written description and sets forth the reasons why action is necessary and all supporting documentation; and

“(B) issues the order after notice and an opportunity for public comment in accordance with section 553 of title 5, United States Code, and causes the order to be published in the Federal Register.
“(6) Changes.—Any statement of policies, practices, or procedures relating to construction and safety standards, regulations, inspections, monitoring, or other enforcement activities that constitutes a statement of general or particular applicability to implement, interpret, or prescribe law or policy by the Secretary is subject to subsection (a) or this subsection. Any change adopted in violation of subsection (a) or this subsection is void.
“(7) Transition.—Until the date on which the consensus committee is appointed pursuant to section 604(a)(3), the Secretary may issue proposed orders, pursuant to notice and comment in accordance with section 553 of title 5, United States Code, that are not developed under the procedures set forth in this section for new and revised standards.”;
 
    (2) in subsection (d), by adding at the end the following: “Federal preemption under this subsection shall be broadly and liberally construed to ensure that disparate State or local requirements or standards do not affect the uniformity and comprehensiveness of the standards promulgated under this section nor the Federal superintendence of the manufactured housing industry as established by this title. Subject to section 605, there is reserved to each State the right to establish standards for the stabilizing and support systems of manufactured homes sited within that State, and for the foundations on which manufactured homes sited within that State are installed, and the right to enforce compliance with such standards, except that such standards shall be consistent with the purposes of this title and shall be consistent with the design of the manufacturer.”; 
    (3) by striking subsection (e); 
    (4) in subsection (f), by striking the subsection designation and all of the matter that precedes paragraph (1) and inserting the following:

“(e) Considerations in Establishing and Interpreting Standards and Regulations.—The consensus committee, in recommending standards, regulations, and interpretations, and the Secretary, in establishing standards or regulations or issuing interpretations under this section, shall—”;
 
    (5) by striking subsection (g); 
    (6) in the first sentence of subsection (j), by striking “subsection (f)” and inserting “subsection (e)”; and 
    (7) by redesignating subsections (h), (i), and (j), as subsections (f), (g), and (h), respectively.

Temptation: A coder might reject this section because it does not require construction.
Resolution: If a section includes the regulation of construction, as in this regulation that asks the Secretary of Housing and Urban Development to make standards for manufactured housing construction, we mark as yes.
```json
{
  "label": "Yes",
  "quoted_span": "“(i) provide periodic recommendations to the Secretary to adopt, revise, and interpret the Federal manufactured housing construction and safety standards in accordance with this subsection;",
  "justification": "If a section includes the regulation of construction, as in this regulation that asks the Secretary of Housing and Urban Development to make standards for manufactured housing construction, we mark as yes. A coder might reject this section because it does not require construction."
}
```

### Example 11
QUESTION:
Does this section implicate physical construction?

SECTION:
The enactment of this joint resolution shall not be construed as establishing a policy of the United States Government to furnish building sites for Red Cross chapters or any eleemosynary institution at any other place.

Temptation: Coders might want to mark this as yes because the language refers to a "building site." However, this is only a site, and not a structure and we require something that more directly implicates the building of a structure or infrastructure.
Resolution: We do not code this as physical construction because the statute does not discuss funding or building a structure.
```json
{
  "label": "No",
  "quoted_span": "The enactment of this joint resolution shall not be construed as establishing a policy of the United States Government to furnish building sites for Red Cross chapters or any eleemosynary institution at any other place.",
  "justification": "We do not code this as physical construction because the statute does not discuss funding or building a structure. Coders might want to mark this as yes because the language refers to a \"building site.\" However, this is only a site, and not a structure and we require something that more directly implicates the building of a structure or infrastructure."
}
```

### Example 12
QUESTION:
Does this section implicate physical construction?

SECTION:
Salaries and expenses: For necessary expenses in connection with the assessment and collection of internal-revenue taxes and the administration of the internal-revenue laws, including the administration of such provisions of other laws as are authorized by or pursuant to law to be administered by or under the direction of the Commissioner of Internal Revenue, including one stamp agent (to be reimbursed by the stamp manufacturers) and the employment of experts; the securing of evidence of violations of the Acts, the cost of chemical analyses made by others than employees of the United States and expenses incident to such chemists testifying when necessary; necessary expenses incurred in making investigations in connection with the enrollment or disbarment of practitioners before the Treasury Department in internal-revenue matters, expenses of seizure and sale, and contract stenographic reporting services; for the acquisition of property under the provisions of title III of the Liquor Law Repeal and Enforcement Act, approved August 27, 1935 (49 Stat. 872–881), and the operation, maintenance, and repair of property acquired under such title III; purchase (not to exceed thirty-four) and hire of passenger motor vehicles; printing and binding (not to exceed $2,530,000); stationery (not to exceed $1,500,000), and ammunition, $188,000,000, of which amount not to exceed $16,530,000 may be expended for personal services in the District of Columbia and not to exceed $100,000 for detecting and bringing to trial persons guilty of violating the internal-revenue laws or conniving at the same, including payments for information and detection of such violation.
 Additional income tax on railroads in Alaska: For the payment to the Treasurer of Alaska of an amount equal to the tax of 1 per centum collected on the gross annual income of all railroad corporations doing business in Alaska, on business done in Alaska, which tax is in addition to the normal income tax collected from such corporations on net income, the amount of such additional tax to be applicable to general Territorial purposes, $3,500.
 Refunding internal-revenue collections: For refunding internal-revenue collections, as provided by law, including the payment of claims for the prior fiscal years and payment of accounts arising under “Allowance or draw-back (Internal Revenue)”, “Redemption of stamps (Internal Revenue)”, “Refunding legacy taxes, Act of March 30, 1928”, “Repayment of taxes on distilled" spirits destroyed by casualty”, and “Refunds and payments of processing and related taxes”, $1,231,000,000: 
 Provided, That a report shall be made to Congress by internal-revenue districts and alphabetically arranged of all disbursements hereunder in excess of $500 as required by section 3 of Act of May 29, 1928 (sec. 3776, I. R. C.), including the names of all the persons and corporations to whom such payments are made, together with the amount paid to each.

Temptation: A coder might reject this section because it is largely about employment at the IRS.
Resolution: The statute implicates physical construction because it discusses funding of operation, mainenance and repair of physical property.
```json
{
  "label": "Yes",
  "quoted_span": "and the operation, maintenance, and repair of property acquired under such title ",
  "justification": "The statute implicates physical construction because it discusses funding of operation, mainenance and repair of physical property. A coder might reject this section because it is largely about employment at the IRS."
}
```

### Now label this section
QUESTION:
Does this section implicate physical construction?

SECTION:
<PASTE SECTION TEXT HERE>
