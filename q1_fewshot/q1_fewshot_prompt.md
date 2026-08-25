<!-- GENERATED FILE - do not hand-edit. -->
<!-- Regenerate: python q1_fewshot/build_prompt.py --write-markdown -->

# Q1 Few-Shot Prompt (rendered)

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

Be conservative: a matching keyword ("participation", "consultation",
"hearing", "petition") is not enough on its own - check WHO is involved. If
every actor involved in participation is inside the federal government, the
answer is "No" no matter how procedural the language sounds.

DEFINITION:
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


### Example 1
QUESTION:
Does this section recommend or require participation?

SECTION:
Appropriations available for permanent change-of-station travel of members of the Army are available for refunds under this Act.

Temptation: Nothing. It does not refer to people communicating with the government or participating in its decisionmaking.
Resolution: This provision explains that some funding can be used for various purposes.
```json
{
  "label": "No",
  "quoted_span": "Appropriations available for permanent change-of-station travel of members of the Army are available for refunds under this Act.",
  "justification": "This provision explains that some funding can be used for various purposes. Nothing. It does not refer to people communicating with the government or participating in its decisionmaking."
}
```

### Example 2
QUESTION:
Does this section recommend or require participation?

SECTION:
(a) Establishment.—There is established an estuary habitat restoration program under which the Secretary may carry out estuary habitat restoration projects and provide technical assistance in accordance with the requirements of this title. 
    (b) Origin of Projects.—A proposed estuary habitat restoration project shall originate from a non-Federal interest consistent with State or local laws. 
    (c) Selection of Projects.—

        (1) In general.—The Secretary shall select estuary habitat restoration projects from a list of project proposals submitted by the Estuary Habitat Restoration Council under section 105(b). 
        (2) Required elements.—Each estuary habitat restoration project selected by the Secretary must—

            (A) address restoration needs identified in an estuary habitat restoration plan; 
            (B) be consistent with the estuary habitat restoration strategy developed under section 106; 
            (C) include a monitoring plan that is consistent with standards for monitoring developed under section 107 to ensure that short-term and long-term restoration goals are achieved; and 
            (D) include satisfactory assurance from the non-Federal interests proposing the project that the non-Federal interests will have adequate personnel, funding, and authority to carry out items of local cooperation and properly maintain the project.  
        (3) Factors for selection of projects.—In selecting an estuary habitat restoration project, the Secretary shall consider the following factors:

            (A) Whether the project is part of an approved Federal estuary management or habitat restoration plan. 
            (B) The technical feasibility of the project. 
            (C) The scientific merit of the project. 
            (D) Whether the project will encourage increased coordination and cooperation among Federal, State, and local government agencies. 
            (E) Whether the project fosters public-private partnerships and uses Federal resources to encourage increased private sector involvement, including consideration of the amount of private funds or in-kind contributions for an estuary habitat restoration activity. 
            (F) Whether the project is cost-effective. 
            (G) Whether the State in which the non-Federal interest is proposing the project has a dedicated source of funding to acquire or restore estuary habitat, natural areas, and open spaces for the benefit of estuary habitat restoration or protection. 
            (H) Other factors that the Secretary determines to be reasonable and necessary for consideration.  
        (4) Priority.—In selecting estuary habitat restoration projects to be carried out under this title, the Secretary shall give priority consideration to a project if, in addition to meriting selection based on the factors under paragraph (3)—

            (A) the project occurs within a watershed in which there is a program being carried out that addresses sources of pollution and other activities that otherwise would reimpair the restored habitat; or 
            (B) the project includes pilot testing of or a demonstration of an innovative technology having the potential for improved cost-effectiveness in estuary habitat restoration.   
    (d) Cost Sharing.—

        (1) Federal share.—Except as provided in paragraph (2) and subsection (e)(2), the Federal share of the cost of an estuary habitat restoration project (other than the cost of operation and maintenance of the project) carried out under this title shall not exceed 65 percent of such cost. 
        (2) Innovative technology costs.—The Federal share of the incremental additional cost of including in a project pilot testing of or a demonstration of an innovative technology described in subsection (c)(4)(B) shall be 85 percent. 
        (3) Non-federal share.—The non-Federal share of the cost of an estuary habitat restoration project carried out under this title shall Include lands, easements, rights-of-way, and relocations and may include services, or any other form of in-kind contribution determined by the Secretary to be an appropriate contribution equivalent to the monetary amount required for the non-Federal share of the activity. 
        (4) Operation and maintenance.—The non-Federal interests shall be responsible for all costs associated with operating, maintaining, replacing, repairing, and rehabilitating all projects carried out under this section.  
    (e) Interim Actions.—

        (1) In general.—Pending completion of the estuary habitat restoration strategy to be developed under section 106, the Secretary may take interim actions to carry out an estuary habitat restoration activity. 
        (2) Federal share.—The Federal share of the cost of an estuary habitat restoration activity before the completion of the estuary habitat restoration strategy shall not exceed 25 percent of such cost.  
    (f) Cooperation of Non-Federal Interests.—

        (1) In general.—The Secretary may not carry out an estuary habitat restoration project until a non-Federal interest has entered into a written agreement with the Secretary in which the non-Federal interest agrees to—

            (A) provide all lands, easements, rights-of-way, and relocations and any other elements the Secretary determines appropriate under subsection (d)(3); and 
            (B) provide for maintenance and monitoring of the project.  
        (2) Nongovernmental organizations.—Notwithstanding section 221(b) of the Flood Control Act of 1970 (42 U.S.C. 1962d-5b(b)), for any project to be undertaken under this title, the Secretary, in consultation and coordination with appropriate State and local governmental agencies and Indian tribes, may allow a nongovernmental organization to serve as the non-Federal interest for the project.  
    (g) Delegation of Project Implementation.—In carrying out this title, the Secretary may delegate project implementation to another Federal department or agency on a reimbursable basis if the Secretary, upon the recommendation of the Council, determines such delegation is appropriate.

Temptation: Nothing. The text identifies that consultation with members of the public must occur before the federal government makes a decision on something.
Resolution: This provision means that, before the Secretary makes a decision about whether to "allow a nongovernmental organization to serve as the non-Federal interest for the project," the Secretary must consult or coordinate "with appropriate State and local governmental agencies and Indian tribes," which we consider to be public participants.
```json
{
  "label": "Yes",
  "quoted_span": "      (2) Nongovernmental organizations.—Notwithstanding section 221(b) of the Flood Control Act of 1970 (42 U.S.C. 1962d-5b(b)), for any project to be undertaken under this title, the Secretary, in consultation and coordination with appropriate State and local governmental agencies and Indian tribes, may allow a nongovernmental organization to serve as the non-Federal interest for the project.  ",
  "justification": "This provision means that, before the Secretary makes a decision about whether to \"allow a nongovernmental organization to serve as the non-Federal interest for the project,\" the Secretary must consult or coordinate \"with appropriate State and local governmental agencies and Indian tribes,\" which we consider to be public participants. Nothing. The text identifies that consultation with members of the public must occur before the federal government makes a decision on something."
}
```

### Example 3
QUESTION:
Does this section recommend or require participation?

SECTION:
(a) Study Required.—The Secretary of the Navy shall provide for a study to determine the effectiveness of current financing mechanisms for providing incentives for contractors to make shipbuilding capital expenditures, and to assess potential capital expenditure incentives that would lead to ship construction or life-cycle cost savings to the Federal Government. The study shall examine—
  (1) potential improvements in design tools and techniques, material management, technology insertion, systems integration and testing, and other key processes and functions that would lead to reduced construction costs; 
  (2) construction process improvements that would reduce procurement and life-cycle costs of the vessels under construction at the contractor’s facilities; and 
  (3) incentives for investment in shipyard infrastructure that support construction process improvements. 
  (b) Report.—Not later than October 1, 2008, the Secretary of the Navy shall submit to the congressional defense committees a report providing the results of the study under subsection (a). The report shall include each of the following:
  (1) An assessment of the shipbuilding industrial base, as measured by a 10-year history for major shipbuilders with respect to—
  (A) estimated value of shipbuilding facilities; 
  (B) critical shipbuilding capabilities; 
  (C) capital expenditures; 
  (D) major investments in process improvements; and 
  (E) costs for related Navy shipbuilding projects. 
  (2) A description of mechanisms available to the Government and industry to finance facilities and process improvements, including—
  (A) contract incentive and award fees; 
  (B) facilities capital cost of money; 
  (C) facilities depreciation; 
  (D) progress payment provisions; 
  (E) other contract terms and conditions; 
  (F) State and Federal tax provisions and tax incentives; 
  (G) the National Shipbuilding Research Program; and 
  (H) any other mechanisms available. 
  (3) A summary of potential shipbuilding investments that offer greatest reduction to shipbuilding costs, including, for each such investment—
  (A) a project description; 
  (B) an estimate of required investment; 
  (C) the estimated return on investment; and 
  (D) alternatives for financing the investment. 
  (4) The Navy’s strategy for providing incentives for contractors’ capital expenditures that would lead to ship construction or life-cycle savings to the Federal Government, including identification of any specific changes in legislative authority that would be required for the Secretary to execute this strategy. 
  (c) Utilization of Other Studies and Outside Experts.—The study shall build upon the results of the 2005 and 2006 Global Shipbuilding Industrial Base Benchmarking studies. Financial analysis associated with the report shall be conducted in consultation with financial experts independent of the Department of Defense.

Temptation: It looks like participation because it refers to "consultation with financial experts indepdendent of the Department"
Resolution: The consultation is about the contents of a government study, not a government decision.
```json
{
  "label": "No",
  "quoted_span": " (c) Utilization of Other Studies and Outside Experts.—The study shall build upon the results of the 2005 and 2006 Global Shipbuilding Industrial Base Benchmarking studies. Financial analysis associated with the report shall be conducted in consultation with financial experts independent of the Department of Defense.",
  "justification": "The consultation is about the contents of a government study, not a government decision. It looks like participation because it refers to \"consultation with financial experts indepdendent of the Department\""
}
```

### Example 4
QUESTION:
Does this section recommend or require participation?

SECTION:
"(a) Membership.—

        (1) Total membership.—The Agreement should provide for the Commission to be composed of 24 members, of which 12 members are appointed by the President and 12 members are appointed by the Government of Canada. 
        (2) General qualifications.—The Agreement should provide for the membership of the Commission, to the maximum extent practicable, to be representative of—

            (A) the interests of the local communities (including the governments of the communities), aboriginal peoples, and businesses that would be affected by the connection of the rail system in Alaska to the North American continental rail system; and 
            (B) a broad range of expertise in areas of knowledge that are relevant to the significant issues to be considered by the Commission, including economics, engineering, management of resources, social sciences, fish and game management, environmental sciences, and transportation.   
    (b)United States Membership.—If the United States and Canada enter into an agreement providing for the establishment of the Commission, the President shall appoint the United States members of the Commission as follows:

        (1) Two members from among persons who are qualified to represent the interests of communities and local governments of Alaska. 
        (2) One member representing the State of Alaska, to be nominated by the Governor of Alaska. 
        (3) One member from among persons who are qualified to represent the interests of Native Alaskans residing in the area of Alaska that would be affected by the extension of rail service. 
        (4) Three members from among persons involved in commercial activities in Alaska who are qualified to represent commercial interests in Alaska, of which one shall be a representative of the Alaska Railroad Corporation. 
        (5) One member representing United States Class I rail carriers and one member representing United States rail labor. 
        (6) Three members with relevant expertise, at least one of whom shall be an engineer with expertise in subarctic transportation and at least one of whom shall have expertise on the environmental impact of such transportation. 
        (7) Canadian membership.—The Agreement should provide for the Canadian membership of the Commission to be representative of broad categories of interests of Canada as the Government of Canada determines appropriate, consistent with subsection (a)(2)."

Temptation: It's not clear what this commission will do, or which government decisions it will be consulted on.
Resolution: This provision creates a Commission that will have several members and is intended "to be representative of" a series of interests.
```json
{
  "label": "Yes",
  "quoted_span": "(a) Membership.—\n\n        (1) Total membership.—The Agreement should provide for the Commission to be composed of 24 members, of which 12 members are appointed by the President and 12 members are appointed by the Government of Canada. \n        (2) General qualifications.—The Agreement should provide for the membership of the Commission, to the maximum extent practicable, to be representative of—\n\n            (A) the interests of the local communities (including the governments of the communities), aboriginal peoples, and businesses that would be affected by the connection of the rail system in Alaska to the North American continental rail system; and \n            (B) a broad range of expertise in areas of knowledge that are relevant to the significant issues to be considered by the Commission, including economics, engineering, management of resources, social sciences, fish and game management, environmental sciences, and transportation. ",
  "justification": "This provision creates a Commission that will have several members and is intended \"to be representative of\" a series of interests. It's not clear what this commission will do, or which government decisions it will be consulted on."
}
```

### Example 5
QUESTION:
Does this section recommend or require participation?

SECTION:
That whenever the Secretary of the Interior, acting through the Director of the Bureau of Mines or his duly authorized representative, shall, upon investigation or inspection of any coal mine, pursuant to the Act of May 7, 1941 (55 Stat. 177), find that the safety standards, set forth in the Federal Mine Safety Code for Bituminous Coal and Lignite Mines of the United States, adopted pursuant to an agreement dated May 29, 1946, between the Secretary of the Interior, acting as Coal Mines Administrator, and the United Mine Workers of America, as published in 11 Federal Register 9017 (title 32, CFR., pt. 304, secs. 304.1–304.15), with respect to ventilation, rock-dusting, storage and use of explosives, roof and rib support, the use of water or water with a wetting agent or other means of dust control where mining operations raise an excessive amount of dust, and prevention of fires in the underground workings of the mines, are not being observed, he shall forthwith notify the owner and the operator of such mine and the State agency charged with the enforcement of safety measures in such mine of his findings and recommendations thereon, and request such owner, operator, and State agency severally to report to the Director of the Bureau of Mines the action taken with respect to said recommendations.

Temptation: It looks like participation because it refers to an agreement "between the Secretary of the Interior, acting as Coal Mines Administrator, and the United Mine Workers of America"
Resolution: It refers to an agreement that happened in the past "between the Secretary of the Interior, acting as Coal Mines Administrator, and the United Mine Workers of America" but we are only interested in future participation
```json
{
  "label": "No",
  "quoted_span": "That whenever the Secretary of the Interior, acting through the Director of the Bureau of Mines or his duly authorized representative, shall, upon investigation or inspection of any coal mine, pursuant to the Act of May 7, 1941 (55 Stat. 177), find that the safety standards, set forth in the Federal Mine Safety Code for Bituminous Coal and Lignite Mines of the United States, adopted pursuant to an agreement dated May 29, 1946, between the Secretary of the Interior, acting as Coal Mines Administrator, and the United Mine Workers of America, as published in 11 Federal Register 9017 (title 32, CFR., pt. 304, secs. 304.1–304.15), with respect to ventilation, rock-dusting, storage and use of explosives, roof and rib support, the use of water or water with a wetting agent or other means of dust control where mining operations raise an excessive amount of dust, and prevention of fires in the underground workings of the mines, are not being observed, he shall forthwith notify the owner and the operator of such mine and the State agency charged with the enforcement of safety measures in such mine of his findings and recommendations thereon, and request such owner, operator, and State agency severally to report to the Director of the Bureau of Mines the action taken with respect to said recommendations.",
  "justification": "It refers to an agreement that happened in the past \"between the Secretary of the Interior, acting as Coal Mines Administrator, and the United Mine Workers of America\" but we are only interested in future participation It looks like participation because it refers to an agreement \"between the Secretary of the Interior, acting as Coal Mines Administrator, and the United Mine Workers of America\""
}
```

### Example 6
QUESTION:
Does this section recommend or require participation?

SECTION:
"(a) Section 220(d) (3) (B) (iii) of the National Housing Act is amended by inserting after and except that” the following: “with respect to rehabilitation projects involving not more than five family units, the Secretary may by regulation increase by 25 per centum any of the foregoing dollar amount limitations contained in this clause which are applicable to units with two, three, or four or more bedrooms: Provided, That”.
  
  (b) Section 220(d) (3) (B) (iii) of such Act is further amended—
 
  (1) 
 by inserting immediately before “by not to exceed 45 per centum” the following: “(as determined after the application of the preceding proviso)”; and
  
  (2) 
 by striking out “Provided, That nothing” and inserting in lieu thereof “Provided further, That nothing”."

Temptation: The word "may" makes the participation seem optional, and it probably is, but for our purposes we want to include this as participation.
Resolution: When a statute gives a federal agency the authority to issue a regulation, we could that as participation. We do this even when Congress gives the agency discretion about whether to use the authority, as signified by the with "may" in this text.
```json
{
  "label": "Yes",
  "quoted_span": "the Secretary may by regulation increase by 25 per centum any of the foregoing dollar amount limitations contained in this clause which are applicable to units with two, three, or four or more bedrooms",
  "justification": "When a statute gives a federal agency the authority to issue a regulation, we could that as participation. We do this even when Congress gives the agency discretion about whether to use the authority, as signified by the with \"may\" in this text. The word \"may\" makes the participation seem optional, and it probably is, but for our purposes we want to include this as participation."
}
```

### Example 7
QUESTION:
Does this section recommend or require participation?

SECTION:
 “Sec. 3. 
 (a) 
 The National Labor Relations Board (hereinafter called the ‘Board’) created by this Act prior to its amendment by the Labor Management Relations Act, 1947, is hereby continued as an agency of the United States, except that the Board shall consist of five instead of three members, appointed by the President by and with the advice and consent of the Senate. Of the two additional members so provided for, one shall be appointed for a term of five years and the other for a term of two years. Their successors, and the successors of the other members, shall be appointed for terms of five years each, excepting that any individual chosen to fill a vacancy shall be appointed only for the unexpired term of the member whom he shall succeed. The President shall designate one member to serve as Chairman of the Board. Any member of the Board may be removed by the President, upon notice and hearing, for neglect of duty or malfeasance in office, but for no other cause.
 
 
 “(b) 
 The Board is authorized to delegate to any group of three or more members any or all of the powers which it may itself exercise, A vacancy in the Board shall not impair the right of the remaining members to exercise all of the powers of the Board, and three members of the Board shall, at all times, constitute a quorum of the Board, except that two members shall constitute a quorum of any group designated pursuant to the first sentence hereof, The Board shall have an official seal which shall be judicially noticed.
 
 
 “(c) 
 The Board shall at the close of each fiscal year make a report in writing to Congress and to the President stating in detail the cases it has heard, the decisions it has rendered, the names, salaries, and duties of all employees and officers in the employ or under the supervision of the Board, and an account of all moneys it has disbursed.
 
 
 “(d) 
 There shall be a General Counsel of the Board who shall be appointed by the President, by and with the advice and consent of the Senate, for a term of four years. The General Counsel of the Board shall exercise general supervision over all attorneys employed by the Board (other than trial examiners and legal assistants to Board members) and over the officers and employees in the regional office. He shall have final authority, on behalf of the Board, in respect of the investigation of charges and issuance of complaints under section 10, and in respect of the prosecution of such complaints before the Board, and shall have such other duties as the Board may prescribe or as maybe provided by law.
 
 
 
 “Sec. 4. 
 
 (a) 
 Each member of the Board and the General Counsel of the Board shall receive a salary of $12,000 a year, shall be eligible for reappointment, and shall not engage in any other business, vocation, or employment. The Board shall appoint an executive secretary, and such attorneys, examiners, and regional directors, and such other employees as it may from time to time find necessary for the proper performance of its duties. The Board may not employ any attorneys for the purpose of reviewing transcripts of hearings or preparing drafts of opinions except that any attorney employed for assignment as a legal assistant to any Board member may for such Board member review such transcripts and prepare such drafts. No trial examiner’s report shall be reviewed, either before or after its publication, by any person other than a member of the Board or his legal assistant, and no trial examiner shall advise or consult with the Board with respect to exceptions taken to his findings, rulings, or recommendations. The Board may establish or utilize such regional, local, or other agencies, and utilize such voluntary and uncompensated services, as may from time to time be needed. Attorneys appointed under this section may, at the direction of the Board, appear for and represent the Board in any case in court. Nothing in this Act shall be construed to authorize the Board to appoint individuals for the purpose of conciliation or mediation, or for economic analysis.

Temptation: It looks like participation because it involves members of the public being appointed to a board.
Resolution: This statute creates an agency, and the people appointed to the agency's board will be paid employees of the federal government. We do not consider people employed by the government to be engaged in participation when they do their jobs.
```json
{
  "label": "No",
  "quoted_span": " “Sec. 3. \n (a) \n The National Labor Relations Board (hereinafter called the ‘Board’) created by this Act prior to its amendment by the Labor Management Relations Act, 1947, is hereby continued as an agency of the United States, except that the Board shall consist of five instead of three members, appointed by the President by and with the advice and consent of the Senate. Of the two additional members so provided for, one shall be appointed for a term of five years and the other for a term of two years. Their successors, and the successors of the other members, shall be appointed for terms of five years each, excepting that any individual chosen to fill a vacancy shall be appointed only for the unexpired term of the member whom he shall succeed. The President shall designate one member to serve as Chairman of the Board. Any member of the Board may be removed by the President, upon notice and hearing, for neglect of duty or malfeasance in office, but for no other cause.\n \n \n “(b) \n The Board is authorized to delegate to any group of three or more members any or all of the powers which it may itself exercise, A vacancy in the Board shall not impair the right of the remaining members to exercise all of the powers of the Board, and three members of the Board shall, at all times, constitute a quorum of the Board, except that two members shall constitute a quorum of any group designated pursuant to the first sentence hereof, The Board shall have an official seal which shall be judicially noticed.\n \n \n “(c) \n The Board shall at the close of each fiscal year make a report in writing to Congress and to the President stating in detail the cases it has heard, the decisions it has rendered, the names, salaries, and duties of all employees and officers in the employ or under the supervision of the Board, and an account of all moneys it has disbursed.\n \n \n “(d) \n There shall be a General Counsel of the Board who shall be appointed by the President, by and with the advice and consent of the Senate, for a term of four years. The General Counsel of the Board shall exercise general supervision over all attorneys employed by the Board (other than trial examiners and legal assistants to Board members) and over the officers and employees in the regional office. He shall have final authority, on behalf of the Board, in respect of the investigation of charges and issuance of complaints under section 10, and in respect of the prosecution of such complaints before the Board, and shall have such other duties as the Board may prescribe or as maybe provided by law.\n \n \n \n “Sec. 4. \n \n (a) \n Each member of the Board and the General Counsel of the Board shall receive a salary of $12,000 a year, shall be eligible for reappointment, and shall not engage in any other business, vocation, or employment. The Board shall appoint an executive secretary, and such attorneys, examiners, and regional directors, and such other employees as it may from time to time find necessary for the proper performance of its duties. The Board may not employ any attorneys for the purpose of reviewing transcripts of hearings or preparing drafts of opinions except that any attorney employed for assignment as a legal assistant to any Board member may for such Board member review such transcripts and prepare such drafts. No trial examiner’s report shall be reviewed, either before or after its publication, by any person other than a member of the Board or his legal assistant, and no trial examiner shall advise or consult with the Board with respect to exceptions taken to his findings, rulings, or recommendations. The Board may establish or utilize such regional, local, or other agencies, and utilize such voluntary and uncompensated services, as may from time to time be needed. Attorneys appointed under this section may, at the direction of the Board, appear for and represent the Board in any case in court. Nothing in this Act shall be construed to authorize the Board to appoint individuals for the purpose of conciliation or mediation, or for economic analysis.",
  "justification": "This statute creates an agency, and the people appointed to the agency's board will be paid employees of the federal government. We do not consider people employed by the government to be engaged in participation when they do their jobs. It looks like participation because it involves members of the public being appointed to a board."
}
```

### Example 8
QUESTION:
Does this section recommend or require participation?

SECTION:
"(a) There is hereby established a commission to be known as the Advisory Commission on Parcel Distribution Services (hereinafter referred to as the “Commission”). 
  (b) The Commission shall be composed of five members appointed by the President. Three members of the Commission shall constitute a quorum. The President shall designate one of the members to serve as Chairman of the Commission and one of the members to serve as Vice Chairman of the Commission. 
  (c) It shall be the duty of the Commission to make a full and complete study of small parcel distribution services, including parcel post, with a view to making recommendations with respect to—
 
  (1) 
 the adequacy of existing services in terms of the needs of the consumer and the shipper;
  
  (2) 
 the feasibility of integrating private and public small parcel distribution services through cooperative ventures;
  
  (3) 
 methods of improving, coordinating, strengthening, expanding, and making more efficient the private distribution system;
  
  (4) 
 simplification of the rate structure applicable to the parcel post system;
  
  (5) 
 standardization of containers for parcel post shipments;
  
  (6) 
 improvement of service under the parcel post system in terms of reliability, delivery, and handling of parcels;
  
  (7) 
 the ability of the Post Office Department to handle parcels in excess of seventy-eight inches length and girth combined in an efficient, economical, and businesslike manner;
  
  (8) 
 the effect that the size increases effective on July 1, 1971, will have on the financial stability and continued operation of common carriers primarily engaged in express service, and on such carriers’ ability to maintain existing employee rights, privileges, levels, and conditions of employment;
  
  (9) 
 the advisability in terms of the public interest and the needs of the consumer and the shipper generally to permit parcels in excess of seventy-eight inches in length and girth combined to be carried by parcel post;
  
  (10) 
 the necessity for and type of protection to be afforded common carriers primarily engaged in express service and their employees if the Commission finds that it is in the public interest to permit the carriage by parcel post of parcels in excess of seventy-eight inches length and girth combined;
  
  (11) 
 such other matters relating to small parcel distribution as the Commission may deem appropriate. 
  (d) On before January 1, 1968, the Commission shall submit to the President and the Congress an interim report concerning its activities during the preceding year, including such recommendations as it may deem appropriate. On or before January 1, 1969, the Commission shall submit to the President and the Congress its final report and recommendations. Such report shall include specific recommendations on the matters contained in paragraphs (8), (9), and (10) of subsection (c) of this section. If such Commission finds that the increases in parcel post size and weight limits established by this Act will seriously endanger the ability of common carriers primarily engaged in the express service to continue operations and are not in the public interest, Congress shall during the 91st Congress consider the advisability of further legislation to eliminate the increase in size limitations on parcel post to take effect on July 1, 1971, established by this Act. 
  (e) The Commission shall have the power to appoint and fix the compensation of an executive director and such other personnel as it deems advisable, in accordance with the provisions of the civil service laws and the Classification Act of 1949, as amended. The Commission may also procure, without regard to the civil service laws and the Classification Act of 1949, as amended, temporary and intermittent services to the same extent as is authorized for the departments by section 15 of the Act of August 2, 1946 (60 Stat. 810), but at rates not to exceed $100 per diem for individuals. 
  (f) The Commission is authorized to secure directly from any executive department, bureau, agency, board, commission, office, independent establishment, or instrumentality of the Federal Government information for the purposes of this section; and each such department, bureau, agency, board, commission, office, establishment, or instrumentality is authorized and directed to furnish such information directly to the Commission upon request made by the Chairman of the Commission. 
  (g) Members of the Commission shall each receive $100 per diem when engaged in the actual performance of duties vested in the Commission, including travel-time, and may receive travel expenses, includ-ing per diem in lieu of subsistence, as authorized by section 5 of the Administrative Expenses Act of 1946 (5 U.S.C. 73b–2) for persons in the Government service employed intermittently. 
  (h) There are hereby authorized to be appropriated to the Commission such sums, not to exceed $100,000 for any year, as may be necessary to carry out the provisions of this section. 
  (i) The Commission shall cease to exist thirty days after the submission of the final report provided for in subsection (d)."

Temptation: It is hard to tell if the Commission is made up of federal employees or members of the public, or a blend of the two. If it was made up of federal employees, this would not be public participation.
Resolution: This is a commission, and it contemplates people getting paid a "per diem" amount, which implies that the people participating are not federal employees.
```json
{
  "label": "Yes",
  "quoted_span": "(g) Members of the Commission shall each receive $100 per diem when engaged in the actual performance of duties vested in the Commission, including travel-time, and may receive travel expenses, includ-ing per diem in lieu of subsistence, as authorized by section 5 of the Administrative Expenses Act of 1946 (5 U.S.C. 73b–2) for persons in the Government service employed intermittently.",
  "justification": "This is a commission, and it contemplates people getting paid a \"per diem\" amount, which implies that the people participating are not federal employees. It is hard to tell if the Commission is made up of federal employees or members of the public, or a blend of the two. If it was made up of federal employees, this would not be public participation."
}
```

### Example 9
QUESTION:
Does this section recommend or require participation?

SECTION:
"The Agricultural Marketing Act of 1946 (7 U.S.C. 1621 et seq.) is amended by adding at the end the following:“Subtitle G—Hemp Production“SEC. 297A. DEFINITIONS. “In this subtitle:“(1) Hemp.—The term ‘hemp’ means the plant Cannabis sativa L. and any part of that plant, including the seeds thereof and all derivatives, extracts, cannabinoids, isomers, acids, salts, and salts of isomers, whether growing or not, with a delta-9 tetrahydrocannabinol concentration of not more than 0.3 percent on a dry weight basis.“(2) Indian tribe.—The term ‘Indian tribe’ has the meaning given the term in section 4 of the Indian Self-Determination and Education Assistance Act (25 U.S.C. 5304).“(3) Secretary.—The term ‘Secretary’ means the Secretary of Agriculture.“(4) State.—The term ‘State’ means—“(A) a State;“(B) the District of Columbia;“(C) the Commonwealth of Puerto Rico; and“(D) any other territory or possession of the United States.“(5) State department of agriculture.—The term ‘State department of agriculture’ means the agency, commission, or department of a State government responsible for agriculture in the State.“(6) Tribal government.—The term ‘Tribal government’ means the governing body of an Indian tribe.
 “SEC. 297B. STATE AND TRIBAL PLANS.“(a) Submission.—“(1) In general.—A State or Indian tribe desiring to have primary regulatory authority over the production of hemp in the State or territory of the Indian tribe shall submit to the Secretary, through the State department of agriculture (in consultation with the Governor and chief law enforcement officer of the State) or the Tribal government, as applicable, a plan under which the State or Indian tribe monitors and regulates that production as described in paragraph (2).“(2) Contents.—A State or Tribal plan referred to in paragraph (1)—“(A) shall only be required to include—“(i) a practice to maintain relevant information regarding land on which hemp is produced in the State or territory of the Indian tribe, including a legal description of the land, for a period of not less than 3 calendar years;“(ii) a procedure for testing, using post-decarboxylation or other similarly reliable methods, delta-9 tetrahydrocannabinol concentration levels of hemp produced in the State or territory of the Indian tribe;“(iii) a procedure for the effective disposal of—“(I) plants, whether growing or not, that are produced in violation of this subtitle; and“(II) products derived from those plants;“(iv) a procedure to comply with the enforcement procedures under subsection (e);“(v) a procedure for conducting annual inspections of, at a minimum, a random sample of hemp producers to verify that hemp is not produced in violation of this subtitle;“(vi) a procedure for submitting the information described in section 297C(d)(2), as applicable, to the Secretary not more than 30 days after the date on which the information is received; and“(vii) a certification that the State or Indian tribe has the resources and personnel to carry out the practices and procedures described in clauses (i) through (vi); and“(B) may include any other practice or procedure established by a State or Indian tribe, as applicable, to the extent that the practice or procedure is consistent with this subtitle.“(3) Relation to state and tribal law.—“(A) No preemption.—Nothing in this subsection preempts or limits any law of a State or Indian tribe that—“(i) regulates the production of hemp; and“(ii) is more stringent than this subtitle.“(B) References in plans.—A State or Tribal plan referred to in paragraph (1) may include a reference to a law of the State or Indian tribe regulating the production of hemp, to the extent that law is consistent with this subtitle.“(b) Approval.—“(1) In general.—Not later than 60 days after receipt of a State or Tribal plan under subsection (a), the Secretary shall—“(A) approve the State or Tribal plan if the State or Tribal plan complies with subsection (a); or“(B) disapprove the State or Tribal plan only if the State or Tribal plan does not comply with subsection (a).“(2) Amended plans.—If the Secretary disapproves a State or Tribal plan under paragraph (1)(B), the State, through the State department of agriculture (in consultation with the Governor and chief law enforcement officer of the State) or the Tribal government, as applicable, may submit to the Secretary an amended State or Tribal plan that complies with subsection (a).“(3) Consultation.—The Secretary shall consult with the Attorney General in carrying out this subsection.“(c) Audit of State Compliance.—“(1) In general.—The Secretary may conduct an audit of the compliance of a State or Indian tribe with a State or Tribal plan approved under subsection (b).“(2) Noncompliance.—If the Secretary determines under an audit conducted under paragraph (1) that a State or Indian tribe is not materially in compliance with a State or Tribal plan—“(A) the Secretary shall collaborate with the State or Indian tribe to develop a corrective action plan in the case of a first instance of noncompliance; and“(B) the Secretary may revoke approval of the State or Tribal plan in the case of a second or subsequent instance of noncompliance.“(d) Technical Assistance.—The Secretary may provide technical assistance to a State or Indian tribe in the development of a State or Tribal plan under subsection (a).“(e) Violations.—“(1) In general.—A violation of a State or Tribal plan approved under subsection (b) shall be subject to enforcement solely in accordance with this subsection.“(2) Negligent violation.—“(A) In general.—A hemp producer in a State or the territory of an Indian tribe for which a State or Tribal plan is approved under subsection (b) shall be subject to subparagraph (B) of this paragraph if the State department of agriculture or Tribal government, as applicable, determines that the hemp producer has negligently violated the State or Tribal plan, including by negligently—“(i) failing to provide a legal description of land on which the producer produces hemp;“(ii) failing to obtain a license or other required authorization from the State department of agriculture or Tribal government, as applicable; or“(iii) producing Cannabis sativa L. with a delta-9 tetrahydrocannabinol concentration of more than 0.3 percent on a dry weight basis.“(B) Corrective action plan.—A hemp producer described in subparagraph (A) shall comply with a plan established by the State department of agriculture or Tribal government, as applicable, to correct the negligent violation, including—“(i) a reasonable date by which the hemp producer shall correct the negligent violation; and“(ii) a requirement that the hemp producer shall periodically report to the State department of agriculture or Tribal government, as applicable, on the compliance of the hemp producer with the State or Tribal plan for a period of not less than the next 2 calendar years.“(C) Result of negligent violation.—A hemp producer that negligently violates a State or Tribal plan under subparagraph (A) shall not as a result of that violation be subject to any criminal enforcement action by the Federal Government or any State government, Tribal government, or local government.“(D) Repeat violations.—A hemp producer that negligently violates a State or Tribal plan under subparagraph (A) 3 times in a 5-year period shall be ineligible to produce hemp for a period of 5 years beginning on the date of the third violation.“(3) Other violations.—“(A) In general.—If the State department of agriculture or Tribal government in a State or the territory of an Indian tribe for which a State or Tribal plan is approved under subsection (b), as applicable, determines that a hemp producer in the State or territory has violated the State or Tribal plan with a culpable mental state greater than negligence—“(i) the State department of agriculture or Tribal government, as applicable, shall immediately report the hemp producer to—“(I) the Attorney General; and“(II) the chief law enforcement officer of the State or Indian tribe, as applicable; and“(ii) paragraph (1) of this subsection shall not apply to the violation.“(B) Felony.—“(i) In general.—Except as provided in clause (ii), any person convicted of a felony relating to a controlled substance under State or Federal law before, on, or after the date of enactment of this subtitle shall be ineligible, during the 10-year period following the date of the conviction—“(I) to participate in the program established under this section or section 297C; and“(II) to produce hemp under any regulations or guidelines issued under section 297D(a).“(ii) Exception.—Clause (i) shall not apply to any person growing hemp lawfully with a license, registration, or authorization under a pilot program authorized by section 7606 of the Agricultural Act of 2014 (7 U.S.C. 5940) before the date of enactment of this subtitle.“(C) False statement.—Any person who materially falsifies any information contained in an application to participate in the program established under this section shall be ineligible to participate in that program.“(f) Effect.—Nothing in this section prohibits the production of hemp in a State or the territory of an Indian tribe—“(1) for which a State or Tribal plan is not approved under this section, if the production of hemp is in accordance with section 297C or other Federal laws (including regulations); and“(2) if the production of hemp is not otherwise prohibited by the State or Indian tribe.
 “SEC. 297C. DEPARTMENT OF AGRICULTURE.“(a) Department of Agriculture Plan.—“(1) In general.—In the case of a State or Indian tribe for which a State or Tribal plan is not approved under section 297B, the production of hemp in that State or the territory of that Indian tribe shall be subject to a plan established by the Secretary to monitor and regulate that production in accordance with paragraph (2).“(2) Content.—A plan established by the Secretary under paragraph (1) shall include—“(A) a practice to maintain relevant information regarding land on which hemp is produced in the State or territory of the Indian tribe, including a legal description of the land, for a period of not less than 3 calendar years;“(B) a procedure for testing, using post-decarboxylation or other similarly reliable methods, delta-9 tetrahydrocannabinol concentration levels of hemp produced in the State or territory of the Indian tribe;“(C) a procedure for the effective disposal of—“(i) plants, whether growing or not, that are produced in violation of this subtitle; and“(ii) products derived from those plants;“(D) a procedure to comply with the enforcement procedures under subsection (c)(2);“(E) a procedure for conducting annual inspections of, at a minimum, a random sample of hemp producers to verify that hemp is not produced in violation of this subtitle; and“(F) such other practices or procedures as the Secretary considers to be appropriate, to the extent that the practice or procedure is consistent with this subtitle.“(b) Licensing.—The Secretary shall establish a procedure to issue licenses to hemp producers in accordance with a plan established under subsection (a).“(c) Violations.—“(1) In general.—In the case of a State or Indian tribe for which a State or Tribal plan is not approved under section 297B, it shall be unlawful to produce hemp in that State or the territory of that Indian tribe without a license issued by the Secretary under subsection (b).“(2) Negligent and other violations.—A violation of a plan established under subsection (a) shall be subject to enforcement in accordance with paragraphs (2) and (3) of section 297B(e), except that the Secretary shall carry out that enforcement instead of a State department of agriculture or Tribal government.“(3) Reporting to attorney general.—In the case of a State or Indian tribe covered by paragraph (1), the Secretary shall report the production of hemp without a license issued by the Secretary under subsection (b) to the Attorney General.“(d) Information Sharing for Law Enforcement.—“(1) In general.—The Secretary shall—“(A) collect the information described in paragraph (2); and“(B) make the information collected under subparagraph (A) accessible in real time to Federal, State, territorial, and local law enforcement.“(2) Content.—The information collected by the Secretary under paragraph (1) shall include—“(A) contact information for each hemp producer in a State or the territory of an Indian tribe for which—“(i) a State or Tribal plan is approved under section 297B(b); or“(ii) a plan is established by the Secretary under this section;“(B) a legal description of the land on which hemp is grown by each hemp producer described in subparagraph (A); and“(C) for each hemp producer described in subparagraph (A)—“(i) the status of—“(I) a license or other required authorization from the State department of agriculture or Tribal government, as applicable; or“(II) a license from the Secretary; and“(ii) any changes to the status.
 “SEC. 297D. REGULATIONS AND GUIDELINES; EFFECT ON OTHER LAW.“(a) Promulgation of Regulations and Guidelines; Report.—“(1) Regulations and guidelines.—“(A) In general.—The Secretary shall promulgate regulations and guidelines to implement this subtitle as expeditiously as practicable.“(B) Consultation with attorney general.—The Secretary shall consult with the Attorney General on the promulgation of regulations and guidelines under subparagraph (A).“(2) Report.—The Secretary shall annually submit to the Committee on Agriculture of the House of Representatives and the Committee on Agriculture, Nutrition, and Forestry of the Senate a report containing updates on the implementation of this subtitle.“(b) Authority.—Subject to subsection (c)(3)(B), the Secretary shall have sole authority to promulgate Federal regulations and guidelines that relate to the production of hemp, including Federal regulations and guidelines that relate to the implementation of sections 297B and 297C.“(c) Effect on Other Law.—Nothing in this subtitle shall affect or modify—“(1) the Federal Food, Drug, and Cosmetic Act (21 U.S.C. 301 et seq.);“(2) section 351 of the Public Health Service Act (42 U.S.C. 262); or“(3) the authority of the Commissioner of Food and Drugs and the Secretary of Health and Human Services—“(A) under—“(i) the Federal Food, Drug, and Cosmetic Act (21 U.S.C. 301 et seq.); or“(ii) section 351 of the Public Health Service Act (42 U.S.C. 262); or“(B) to promulgate Federal regulations and guidelines that relate to the production of hemp under the Act described in subparagraph (A)(i) or the section described in subparagraph (A)(ii).
 “SEC. 297E. AUTHORIZATION OF APPROPRIATIONS. “There are authorized to be appropriated such sums as are necessary to carry out this subtitle.”
 ."

Temptation: It looks like participation because it refers to consultation between the State department of agriculture, the Governor, and the chief law enforcement officer.
Resolution: The consultation is about a plan that a state or tribe will submit to the federal agency. The consultation is not on a policy that the federal agency is considering, so it is not participation.
```json
{
  "label": "No",
  "quoted_span": "(1) In general.—A State or Indian tribe desiring to have primary regulatory authority over the production of hemp in the State or territory of the Indian tribe shall submit to the Secretary, through the State department of agriculture (in consultation with the Governor and chief law enforcement officer of the State) or the Tribal government, as applicable, a plan under which the State or Indian tribe monitors and regulates that production as described in paragraph (2).",
  "justification": "The consultation is about a plan that a state or tribe will submit to the federal agency. The consultation is not on a policy that the federal agency is considering, so it is not participation. It looks like participation because it refers to consultation between the State department of agriculture, the Governor, and the chief law enforcement officer."
}
```

### Example 10
QUESTION:
Does this section recommend or require participation?

SECTION:
That, in commemoration of the designation by the President of the United States of Ellis Island as a part of the Statue of Liberty National Monument in New York City, New York, the Secretary of the Treasury is authorized and directed to strike and furnish to the New York City National Shrines Advisory Board a fourth medallion in the liberty series of no more than two hundred and fifty-five thousand medals with suitable emblems, devices, and inscriptions to be determined by the New York City National Shrines Advisory Board and subject to the approval of the Secretary of the Treasury. The medals shall be made and delivered at such times as may be required by the advisory board in quantities of not less than two thousand. The medals shall be considered to be national medals within the meaning of section 3551 of the Revised Statutes.

Temptation: We don't have information about who sits on this advisory board.
Resolution: The Secretary can produce medallions only after the advisory board determines that they are suitable.
```json
{
  "label": "Yes",
  "quoted_span": "the Secretary of the Treasury is authorized and directed to strike and furnish to the New York City National Shrines Advisory Board a fourth medallion in the liberty series of no more than two hundred and fifty-five thousand medals with suitable emblems, devices, and inscriptions to be determined by the New York City National Shrines Advisory Board ",
  "justification": "The Secretary can produce medallions only after the advisory board determines that they are suitable. We don't have information about who sits on this advisory board."
}
```

### Example 11
QUESTION:
Does this section recommend or require participation?

SECTION:
(a) 
 Every manufacturer of motor vehicles shall furnish notification of any defect in any motor vehicle or motor vehicle equip-ment produced by such manufacturer which he determines, in good faith, relates to motor vehicle safety, to the purchaser (where known to the manufacturer) of such motor vehicle or motor vehicle equipment, within a reasonable time after such manufacturer has discovered such defect.
  
  (b) The notification required by subsection (a) shall be accomplished—
 
  (1) 
 by certified mail to the first purchaser (not including any dealer of such manufacturer) of the motor vehicle or motor vehicle equipment containing such a defect, and to any subsequent purchaser to whom has been transferred any warranty on such motor vehicle or motor vehicle equipment; and
  
  (2) 
 by certified mail or other more expeditious means to the dealer or dealers of such manufacturer to whom such motor vehicle or equipment was delivered.
  
  (c) 
 The notification required by subsection (a) shall contain a clear description of such defect, an evaluation of the risk to traffic safety reasonably related to such defect, and a statement of the measures to be taken to repair such defect.
  
  (d) 
 Every manufacturer of motor vehicles shall furnish to the Secretary a true or representative copy of all notices, bulletins, and other communications to the dealers of such manufacturer or purchasers of motor vehicles or motor vehicle equipment of such manufacturer regarding any defect in such vehicle or equipment sold or serviced by such dealer. The Secretary shall disclose so much of the information contained in such notice or other information obtained under section 112(a) to the public as he deems will assist in carrying out the purposes of this Act, but he shall not disclose any information which contains or relates to a trade secret or other matter referred to in section 1905 of title 18 of the United States Code unless he determines that it is necessary to carry out the purposes of this Act.
  
  (e) 
 If through testing, inspection, investigation, or research carried out pursuant to this title, or examination or reports pursuant to subsection (d) of this section, or otherwise, the Secretary determines that any motor vehicle or item of motor vehicle equipment—
 
  (1) 
 does not comply with an applicable Federal motor vehicle safety standard prescribed pursuant to section 103; or
  
  (2) 
 contains a defect which relates to motor vehicle safety;
  then he shall immediately notify the manufacturer of such motor vehicle or item of motor vehicle equipment of such defect or failure to comply. The notice shall contain the findings of the Secretary and shall include all information upon which the findings are based. The Secretary shall afford such manufacturer an opportunity to present his views and evidence in support thereof, to establish that there is no failure of compliance or that the alleged defect does not affect motor vehicle safety. If after such presentation by the manufacturer the Secretary determines that such vehicle or item of equipment does not comply with applicable Federal motor vehicle safety standards, or contains a defect which relates to motor vehicle safety, the Secretary shall direct the manufacturer to furnish the notification specified in subsection (c) of this section to the. purchaser of such motor vehicle or item of motor vehicle equipment as provided in subsections (a) and (b) of this section.

Temptation: It looks like participation because it involves an opportunity for a person to present information to a federal agency.
Resolution: The "manufacturer's opportunity to present his views" is in response to an allegation from the agency that the manufacturer's product is defective. This is like an appeal rather than participation in a policy decision.
```json
{
  "label": "No",
  "quoted_span": "The Secretary shall afford such manufacturer an opportunity to present his views and evidence in support thereof, to establish that there is no failure of compliance or that the alleged defect does not affect motor vehicle safety. If after such presentation by the manufacturer the Secretary determines that such vehicle or item of equipment does not comply with applicable Federal motor vehicle safety standards, or contains a defect which relates to motor vehicle safety, the Secretary shall direct the manufacturer to furnish the notification specified in subsection (c) of this section to the. purchaser of such motor vehicle or item of motor vehicle equipment as provided in subsections (a) and (b) of this section.",
  "justification": "The \"manufacturer's opportunity to present his views\" is in response to an allegation from the agency that the manufacturer's product is defective. This is like an appeal rather than participation in a policy decision. It looks like participation because it involves an opportunity for a person to present information to a federal agency."
}
```

### Example 12
QUESTION:
Does this section recommend or require participation?

SECTION:
That there is hereby authorized to be appropriated not to exceed $11,000,000 for the acquisition of land and for the construction thereon of a research laboratory for the Quartermaster Corps, United States Army, at a location to be selected by the Secretary of Defense, and for such utilities and appurtenances thereto as, in the judgment of the Secretary of the Army, may be necessary in connection therewith. The site shall be chosen on the basis of recommendations of an impartial ad hoc committee of experts to be appointed by the Research and Development Board.

Temptation: It is not clear who sits on this board.
Resolution: The site is not chosen until after recommendations have been made by the Reserch and Development Board.
```json
{
  "label": "Yes",
  "quoted_span": "The site shall be chosen on the basis of recommendations of an impartial ad hoc committee of experts to be appointed by the Research and Development Board.",
  "justification": "The site is not chosen until after recommendations have been made by the Reserch and Development Board. It is not clear who sits on this board."
}
```

### Now label this section
QUESTION:
Does this section recommend or require participation?

SECTION:
<PASTE SECTION TEXT HERE>
