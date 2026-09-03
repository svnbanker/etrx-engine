# Policy-event ledger

The verified timeline of US tariff actions that ETRX commentary may cite. **Only `verified: yes` entries may be used for causal attribution** (see `.claude/skills/print-day/SKILL.md`). Entries drafted by an agent are `verified: no` until a human checks the primary source; `partial` means the fact is established but a detail (authority, exact rate, scope) still needs confirmation.

Data-month mapping: FT-900 data months record goods by month of entry, so an action effective mid-month appears partially in that month and fully in the next. Duties in Census calculated duty: tariff-schedule rates including Chapter 99 additions (232/301/IEEPA); AD/CVD excluded.

Conventions: `date` = effective date (announcement in `note` if different). `series` = ETRX series expected to show the effect. Newest at the bottom. Seeded 2026-08-24 from the maintainer's knowledge through January 2026 plus press for 2026 — the 2026 entries need primary-source verification.

---

- date: 2018-03-23
  action: Section 232 tariffs take effect — steel 25%, aluminum 10%; Canada, Mexico, EU and others temporarily exempted
  authority: Section 232 (Proclamations 9704, 9705 of 2018-03-08)
  scope: all origins except temporary exemptions
  status: superseded by later 232 actions
  series: ETRX-STEEL
  verified: yes
  source: Federal Register 83 FR 11619, 11625

- date: 2018-06-01
  action: 232 steel/aluminum exemptions for Canada, Mexico and the EU end; duties apply
  authority: Section 232 (Proclamations 9739, 9740 of 2018-05-31)
  scope: CA, MX, EU steel and aluminum
  status: CA/MX lifted 2019-05-20 (below)
  series: ETRX-STEEL, ETRX-CA-76
  verified: yes
  source: Federal Register 83 FR 25857, 25849

- date: 2018-07-06
  action: Section 301 List 1 — 25% on ~$34B of Chinese goods (machinery, electronics components)
  authority: Section 301
  scope: China, 818 tariff lines
  status: in force
  series: ETRX-CN-84, ETRX-CN-85
  verified: yes
  source: 83 FR 28710

- date: 2018-08-23
  action: Section 301 List 2 — 25% on ~$16B of Chinese goods
  authority: Section 301
  scope: China, 279 lines
  status: in force
  series: ETRX-CN-84, ETRX-CN-85
  verified: yes
  source: 83 FR 40823

- date: 2018-09-24
  action: Section 301 List 3 — 10% on ~$200B of Chinese goods; raised to 25% on 2019-05-10
  authority: Section 301
  scope: China, ~5,700 lines
  status: in force
  series: ETRX-CN-84, ETRX-CN-85
  verified: yes
  source: 83 FR 47974; 84 FR 20459

- date: 2019-05-20
  action: 232 steel/aluminum tariffs on Canada and Mexico removed
  authority: Section 232 (Proclamations 9893, 9894 of 2019-05-19)
  scope: CA, MX
  status: reimposed 2025-03-12
  series: ETRX-CA-76, ETRX-STEEL
  verified: yes
  source: 84 FR 23421, 23425

- date: 2019-09-01
  action: Section 301 List 4A — 15% on ~$112B of Chinese consumer goods (apparel, footwear, electronics, toys); cut to 7.5% on 2020-02-14
  authority: Section 301
  scope: China
  status: in force at 7.5%
  series: ETRX-CN-95, ETRX-CN-85, ETRX-APPAREL
  verified: yes
  source: 84 FR 43304; 85 FR 3741

- date: 2020-02-14
  action: Phase One agreement — List 4A rate reduced from 15% to 7.5%; List 4B suspended
  authority: Section 301
  scope: China
  status: in force
  series: ETRX-CN-95, ETRX-CN-85
  verified: yes
  source: 85 FR 3741

- date: 2024-09-27
  action: Section 301 four-year review increases — EVs 100%, solar cells 50%, syringes/needles 50%, steel and aluminum products 25%, ship-to-shore cranes 25%; semiconductors to 50% in 2025
  authority: Section 301
  scope: China, targeted lines
  status: in force
  series: ETRX-CN-85, ETRX-CN-84, ETRX-STEEL
  verified: yes
  source: 89 FR 76581

- date: 2025-02-04
  action: IEEPA "fentanyl" tariff — additional 10% on all imports from China; raised to 20% on 2025-03-04; cut to 10% on 2025-11-10 (EO 14357)
  authority: IEEPA (EO 14195 of 2025-02-01; EO 14357 of 2025-11-04)
  scope: China, all goods
  status: terminated 2026-02-24 (EO 14389) after the Supreme Court ruling of 2026-02-20; refunds via CAPE
  series: ETRX-CN-85, ETRX-CN-84, ETRX-CN-95
  verified: partial (2025 facts yes; the 2025-11-10 cut per research report, human check pending)
  source: 90 FR 9121; 90 FR 50725 (EO 14357, published 2025-11-07)

- date: 2025-03-04
  action: IEEPA tariffs on Canada and Mexico take effect — 25% (Canadian energy and potash 10%); USMCA-compliant goods exempted from 2025-03-07
  authority: IEEPA (EOs 14193, 14194)
  scope: CA, MX non-USMCA-compliant goods
  status: voided by Supreme Court 2026-02-20
  series: ETRX-CA-76, ETRX-CA-44, ETRX-CA-87, ETRX-MX-87
  verified: yes
  source: 90 FR 9113, 9117; amendments of 2025-03-06

- date: 2025-03-12
  action: Section 232 steel and aluminum restored to 25% on all origins; all country exemptions, product exclusions and quota deals terminated; derivative products added
  authority: Section 232 (Proclamations 10895, 10896 of 2025-02-10)
  scope: all origins
  status: raised to 50% on 2025-06-04
  series: ETRX-STEEL, ETRX-CA-76
  verified: yes
  source: 90 FR 9807, 9817

- date: 2025-04-03
  action: Section 232 autos — 25% on imported passenger vehicles and light trucks; parts from 2025-05-03; USMCA-compliant parts and US-content offsets
  authority: Section 232 (Proclamation 10908 of 2025-03-26)
  scope: all origins; EU, Japan, Korea later at 15% under deals (see 2025-08-07)
  status: in force
  series: ETRX-EU-87, ETRX-MX-87, ETRX-CA-87
  verified: yes
  source: 90 FR 14705

- date: 2025-04-05
  action: IEEPA "reciprocal" tariffs — 10% baseline on nearly all origins; country-specific rates in force 2025-04-09 then paused 90 days (except China) the same day
  authority: IEEPA (EO 14257 of 2025-04-02)
  scope: all origins; exemptions for USMCA-compliant goods, 232-covered goods, energy, certain electronics (2025-04-11)
  status: voided by Supreme Court 2026-02-20
  series: ETRX-US, ETRX-APPAREL, ETRX-EU-87
  verified: yes
  source: 90 FR 15041

- date: 2025-04-10
  action: China reciprocal rate escalated to 125% (total additional ~145% with the 20% fentanyl tariff)
  authority: IEEPA (EO 14266)
  scope: China
  status: reduced 2025-05-14
  series: ETRX-CN-85, ETRX-CN-84, ETRX-CN-95
  verified: yes
  source: 90 FR 15625

- date: 2025-05-14
  action: Geneva arrangement — China reciprocal rate cut to 10% (total additional IEEPA layer 30%, then 20% from 2025-11-10 when the fentanyl rate fell to 10%); extended 2025-08-11 and to 2026-11-10 by EO 14358
  authority: IEEPA (EO 14298; EO 14358 of 2025-11-04)
  scope: China
  status: terminated 2026-02-24 (EO 14389)
  series: ETRX-CN-85, ETRX-CN-84, ETRX-CN-95
  verified: partial (2025 facts yes; November details per research report, human check pending)
  source: 90 FR 21831; 90 FR 50729 (EO 14358)

- date: 2025-06-04
  action: Section 232 steel and aluminum raised to 50% (UK stays at 25%)
  authority: Section 232 (Proclamation 10947 of 2025-06-03)
  scope: all origins except UK
  status: in force
  series: ETRX-STEEL, ETRX-CA-76
  verified: yes
  source: 90 FR 24013

- date: 2025-08-01
  action: Section 232 copper — 50% on semi-finished copper and derivative products
  authority: Section 232 (Proclamation of 2025-07-30)
  scope: all origins
  status: in force
  series: (no ETRX series; HS 74 not covered)
  verified: yes
  source: Federal Register, 2025-07-31

- date: 2025-08-07
  action: Modified reciprocal rates take effect (10%–41% by origin); framework deals set EU 15%, Japan 15%, Korea 15%, UK 10%; EU/Japan/Korea autos at 15% under 232 deals
  authority: IEEPA (EO 14326 of 2025-07-31); 232 auto modifications
  scope: all non-exempt origins
  status: IEEPA component voided 2026-02-20; 232 auto deal rates continue
  series: ETRX-US, ETRX-EU-87, ETRX-APPAREL
  verified: yes
  source: 90 FR 37963

- date: 2025-08-29
  action: De minimis duty-free treatment ended for all origins (previously China/HK from 2025-05-02)
  authority: IEEPA (EO 14324 of 2025-07-30)
  scope: all low-value shipments
  status: structural break — low-value flows now enter imports for consumption (RULEBOOK §9)
  series: ETRX-US, ETRX-APPAREL, ETRX-CN-95
  verified: yes
  source: 90 FR 37345

- date: 2025-08-29
  action: Federal Circuit (en banc) rules IEEPA tariffs unlawful in V.O.S. Selections v. Trump; stayed pending Supreme Court review (argued 2025-11-05)
  authority: judicial
  scope: all IEEPA tariffs
  status: affirmed by Supreme Court 2026-02-20
  series: (all IEEPA-affected series)
  verified: yes
  source: Fed. Cir. No. 25-1812

- date: 2025-10-14
  action: Section 232 timber/lumber 10%; kitchen cabinets/vanities and upholstered wooden furniture 25% (scheduled 2026-01-01 increases to 50%/30% deferred to 2027-01-01 by Proclamation 11000); Section 232 medium/heavy-duty vehicles 25% and buses 10% from 2025-11-01 (Proclamation 10984). NOTE: the 2025-09-25 pharmaceutical announcement was never implemented in 2025 — see 2026-07-31
  authority: Section 232 (Proclamation 10976 of 2025-09-29; Proclamation 10984 of 2025-10-17; Proclamation 11000 of 2025-12-31)
  scope: all origins; deal-based rates for EU/Japan/UK
  status: in force at 25%/10%; increases deferred to 2027-01-01
  series: ETRX-CA-44
  verified: no (research report 2026-08; human check pending)
  source: 90 FR 48127; 90 FR 48451; 91 FR 1039

- date: 2025-11-14
  action: Tariff exemptions for certain agricultural imports (beef, coffee, tea, bananas, cocoa, spices, some fertilizers)
  authority: IEEPA (EO of 2025-11-14)
  scope: listed agricultural goods, all origins
  status: moot after 2026-02-20 ruling
  series: (no ETRX series)
  verified: yes
  source: EO 2025-11-14

- date: 2026-01-01
  action: Section 301 four-year-review step-ups on China — non-EV lithium-ion batteries 7.5%→25%, natural graphite 25%, permanent magnets 25%, medical/surgical gloves 100%, respirators/facemasks 50%
  authority: Section 301 (USTR notice of 2024-09-18)
  scope: China, listed lines (HTSUS 9903.91.06–.08)
  status: in force
  series: ETRX-CN-85
  verified: no (research report 2026-08)
  source: 89 FR 76581

- date: 2026-01-15
  action: Section 232 semiconductors — 25% on a narrow annex of advanced computing chips with broad end-use exemptions; companion critical-minerals proclamation orders negotiations only
  authority: Section 232 (Proclamation 11002 of 2026-01-14)
  scope: all origins, annexed chips
  status: in force; 232-covered chips exempt from the 2026-07-24 Section 301 duty
  series: (narrow; ETRX-CN-85 at most)
  verified: no (research report 2026-08)
  source: 91 FR 2443 (2026-01-20)

- date: 2026-02-07
  action: India — additional 25% "Russian oil" IEEPA duty removed under the 2026-02-06 interim framework (18% reciprocal envisaged; whether collected before 2026-02-24 unconfirmed); from 2026-02-24 India paid the uniform Section 122 10%, and from 2026-07-24 the Section 301 10%
  authority: IEEPA (EO 14384 of 2026-02-06)
  scope: India
  status: moot from 2026-02-24
  series: ETRX-US
  verified: no (research report 2026-08)
  source: 91 FR 6501 (2026-02-11); newsonair.gov.in 2026-02-21

- date: 2026-02-20
  action: Supreme Court holds IEEPA does not authorize tariffs — Learning Resources, Inc. v. Trump (No. 24-1287) with Trump v. V.O.S. Selections (No. 25-250), 6–3, Roberts. Collection ended 2026-02-24 (EO 14389; CSMS #67834313). CIT ordered universal refunds with interest 2026-03-04 (Atmus Filtration v. United States, No. 26-1259; government appeal filed 2026-06-02). CBP CAPE refund tool: Phase 1 2026-04-20, Phase 2 2026-06-29. ~$166B collected; as of 2026-07-31 $128.68B accepted, ~$100B certified/paid (Treasury MTS: $81B paid FYTD through June, >$100B through July)
  authority: judicial; EO 14389 of 2026-02-20
  scope: all IEEPA tariffs (fentanyl, reciprocal, Canada/Mexico, Brazil, India, secondary)
  status: refunds in progress; finally-liquidated entries (~$11.4B) contested; refund rights traded $0.50–0.90 (press)
  series: ETRX-US and every IEEPA-affected series
  verified: no (research report 2026-08: syllabus read via LII; EO 14389 and CSMS read; refund figures via press)
  source: 607 U.S. ___ (2026), supremecourt.gov/opinions/25pdf/24-1287_4gcj.pdf; 91 FR 9437 (EO 14389); CSMS #67834313, #68315804, #69035485; CBP declaration 2026-08-04 in Freestyle World v. United States (No. 26-01088) per Supply Chain Dive/CNBC

- date: 2026-02-24
  action: Section 122 temporary import surcharge — 10% ad valorem on all imports for 150 days (a 15% ceiling was announced but never proclaimed); de minimis suspension continued for all countries (EO 14388)
  authority: Section 122 of the Trade Act of 1974 (Proclamation 11012 of 2026-02-20); EO 14388
  scope: all origins; exempt: 232-covered goods, USMCA-qualifying goods, CAFTA-DR textiles, energy, critical minerals, bullion, fertilizers, beef/tomatoes/oranges, pharmaceuticals, certain electronics, aerospace, passenger vehicles and parts
  status: EXPIRED 12:01 a.m. EDT 2026-07-24; held unlawful by CIT 2026-05-07 (Slip Op. 26-47, relief to three plaintiffs only), stayed by Fed. Cir. 2026-06-11, appeal pending; replaced by the Section 301 forced-labor duties
  series: ETRX-US, ETRX-APPAREL, ETRX-CN-84, ETRX-CN-85, ETRX-CN-95 (not ETRX-EU-87/MX-87/CA-87 — autos exempt)
  verified: yes (signoff fondateur 2026-09-02: 10%, Section 122, 150 jours, fin 12:01 le 2026-07-24; passenger vehicles et biens 232 en annexe d'exemptions (le texte dit 'passenger vehicles'))
  source: 91 FR 9339 (Proclamation 11012); 91 FR 9433 (EO 14388); CSMS #67844987; CIT Slip Op. 26-47

- date: 2026-04-06
  action: Section 232 metals restructured — 50% on articles wholly/almost wholly of steel, aluminum or copper; 25% on derivative articles assessed on full customs value (metal-content method ended); temporary 15% on industrial machinery/electrical-grid equipment to 2027-12-31; UK 25%/15%; 10% for derivatives of US-origin metal
  authority: Section 232 (Proclamation 11021 of 2026-04-02)
  scope: all origins
  status: amended 2026-06-08; in force
  series: ETRX-STEEL, ETRX-CA-76
  verified: no (research report 2026-08)
  source: 91 FR 18201 (2026-04-09)

- date: 2026-06-08
  action: Section 232 metals adjusted — mobile industrial equipment 25%, or 15% inclusive of MFN for Argentina, Ecuador, El Salvador, Guatemala, Japan, Korea, Liechtenstein, Switzerland, Taiwan, UK and EU; USMCA-qualifying Canada/Mexico goods in Annex I-C dutiable at 25% on non-US content only with a 15% floor; agricultural equipment and residential HVAC to 15%; US-content threshold 95%→85%; sunset 2027-12-31; 50% primary tier unchanged
  authority: Section 232 (Proclamation 11032 of 2026-06-01)
  scope: all origins, annexed derivative categories
  status: in force to 2027-12-31
  series: ETRX-STEEL, ETRX-CA-76
  verified: no (research report 2026-08; USMCA rule wording to reconcile against the proclamation)
  source: 91 FR 34085 (2026-06-04)

- date: 2026-07-22
  action: Section 301 Brazil — 25% on all imports of Brazil with annexed exemptions (232 goods, civil aircraft, pulp, pig iron, scrap, seafood, instant coffee, certain pharmaceuticals, etc.); replaces the voided IEEPA 40%
  authority: Section 301 (USTR Notice of Action; Presidential Memorandum of 2026-07-15)
  scope: Brazil
  status: in force; Brazil also in the 12.5% forced-labor group from 2026-07-24 (stacking to confirm)
  series: ETRX-US
  verified: yes (signoff fondateur 2026-09-02: 25% effectif 2026-07-22; CUMUL CONFIRMÉ avec le 12,5% 301: 'products that are subject to the additional ad valorem rate of duty imposed by heading 9903.05.01 shall also be subject to any additional duty provided for in this subchapter or in subchapter IV of chapter 99')
  source: 91 FR 45516 (2026-07-20); 91 FR 33854 (2026-06-04)

- date: 2026-07-24
  action: Section 301 forced-labor duties on 60 economies take effect at 12:01 a.m. ET as the Section 122 surcharge expires — 10% (Argentina, Bangladesh, Cambodia, Canada, Ecuador, El Salvador, Guatemala, Honduras, India, Indonesia, Jordan, Malaysia, Mexico, Pakistan, Sri Lanka, Trinidad and Tobago, UK); 10% inclusive of MFN (EU, Taiwan); 12.5% inclusive of MFN (Japan, Korea, Switzerland); 12.5% flat (China, Vietnam, Brazil, Russia and 34 others); exempt: 232-covered goods, USMCA goods, CAFTA-DR textiles, civil aircraft, pharmaceuticals, annexed raw materials
  authority: Section 301 (USTR Notice of Actions of 2026-07-23; Presidential Memorandum of 2026-07-23)
  scope: 60 economies, ~99% of imports by partner
  status: in force, no time limit (first partial data month July 2026, printing 2026-09-03; first full month August 2026)
  series: ETRX-US, ETRX-APPAREL, ETRX-CN-84, ETRX-CN-85, ETRX-CN-95 (not ETRX-EU-87/MX-87/CA-87)
  verified: yes (signoff fondateur 2026-09-02: effet 2026-07-24; Chine 12,5%; UE 10% MFN inclus; biens USMCA en franchise exemptés)
  source: 91 FR 47318 (2026-07-28); 91 FR 34272 (2026-06-05); 91 FR 12884 (2026-03-17)

- date: 2026-07-31
  action: Section 232 pharmaceuticals phase 1 — 100% on patented drugs and associated APIs (Annex I) for Annex III companies; 20% with approved onshoring plans (→100% 2030-04-02); 15% inclusive of MFN for EU/Japan/Korea/Switzerland-Liechtenstein; UK 10% reduced to 0% the same day; 0% for orphan/specialty categories and MFN-pricing signatories (to 2029-01-20); generics and biosimilars excluded; phase 2 (all other companies) 2026-09-29
  authority: Section 232 (Proclamation 11020 of 2026-04-02; BIS notice of 2026-08-04 for the UK)
  scope: all origins, patented pharmaceuticals (HTS 29/30)
  status: in force (phase 1); phase 2 2026-09-29 (first partial data month July 2026)
  series: ETRX-PHARMA
  verified: yes (signoff fondateur 2026-09-02: phases 2026-07-31 (Annexe III) et 2026-09-29; génériques ET biosimilaires exclus)
  source: 91 FR 18183 (2026-04-09); CSMS #69395344 (2026-07-30); 91 FR 49406 (2026-08-04)

- date: 2026-08-22
  action: Section 338 — additional 50% on ~US$20B of Canadian goods (alcoholic beverages plus certain wood, paper and hockey equipment; dairy; and a broad consumer/industrial list — plywood, cement, furniture, cosmetics, apparel, toys, sporting goods, electrical equipment) after talks collapsed 2026-08-21; passenger vehicles/parts and other 232 goods excluded; no USMCA carve-out; originally 2026-08-19, delayed three days
  authority: Section 338 of the Tariff Act of 1930 (Proclamations 11046, 11047, 11048 of 2026-07-20; Proclamation 11056 of 2026-08-18)
  scope: Canada, annexed HTS lines
  status: in force from 12:01 a.m. ET 2026-08-22; USTR Greer: no further talks planned; Canada's countermeasures 2026-09-08
  series: ETRX-CA-44 (ETRX-CA-76 and ETRX-CA-87 not affected — 232 goods excluded); first partial data month August 2026
  verified: no (research report 2026-08: proclamation headings/rates read; annex lists via USTR/press)
  source: 91 FR 46639, 46653, 46663 (2026-07-23); 91 FR 54789 (2026-08-24); USTR statement 2026-08-22

- date: 2026-08-24 (ANNOUNCED ONLY — no instrument, no data effect)
  action: Reported threat of further tariffs on Canadian automobiles, parts and steel after talks collapsed. WSJ and NYT headlines say "threatens"; one WaPo headline says "announces". **No proclamation, executive order or Federal Register notice exists as of 2026-08-24**: a search of Federal Register documents published 2026-08-20→24 mentioning Canada returns only Proclamation 11056 (the three-day Section 338 delay, doc 2026-17294), an OMB notice about Proclamation 10984 steel/aluminum submissions, and an unrelated AD/CVD deadline notice.
  authority: none yet
  scope: none yet
  status: **announced/threatened, not in force.** Nothing enters at a new rate until an instrument exists, so no ETRX series can move on this. Re-check the Federal Register before any commentary treats it as an action.
  series: none
  verified: partial (absence of an instrument verified via the Federal Register API 2026-08-24; the statements themselves via press headlines)
  source: Federal Register API query, publication_date ≥ 2026-08-20, term "Canada tariff"; press: WSJ, NYT, Washington Post 2026-08-24

  **Naming trap worth knowing.** Proclamations 11046, 11047 and 11048 are named for the *Canadian practices* being retaliated against — provincial liquor bans, cheese quota administration, and Canada's tariff on non-USMCA-qualifying US vehicles — **not** for the US products being taxed. So "the motor vehicles proclamation" does not tax passenger vehicles; its annex is a broad consumer and industrial list, and Section 232 goods (including vehicles and metals) are excluded. This is very likely why coverage keeps describing the action as hitting Canadian cars and steel. It does not. Any ETRX commentary that repeats the press framing here would be wrong, and correcting it is a legitimate `/correction` target.

- date: 2026-09-03 (scheduled)
  action: Section 232 drones — 100% on UAS >25 kg, thermal-imaging UAS, docking stations and Annex I components; 25% on UAS ≤25 kg; allied caps 15% (UK 10%)
  authority: Section 232 (Proclamation 11055 of 2026-08-13)
  scope: all origins
  status: scheduled
  series: (none; HS 8806)
  verified: no (research report 2026-08)
  source: 91 FR 53699 (2026-08-19)

- date: 2026-09-08 (scheduled; not a US duty — context only)
  action: Canada's dollar-for-dollar countermeasures on ~C$20B of US goods (steel, dairy, appliances, agricultural equipment, pulp and paper, electronics); list and rates to be published
  authority: Canadian countermeasure order (pending)
  scope: US exports to Canada
  status: announced 2026-08-22
  series: (none)
  verified: no
  source: pm.gc.ca remarks 2026-08-22

- date: 2026-09-29 (scheduled)
  action: Section 232 pharmaceuticals phase 2 — rates extend to all other companies
  authority: Section 232 (Proclamation 11020)
  scope: all origins, patented pharmaceuticals
  status: scheduled (first partial data month September, full month October 2026)
  series: ETRX-PHARMA
  verified: no
  source: 91 FR 18183

- date: 2026-12-04 (scheduled)
  action: Section 232 polysilicon — minimum import prices enforced by specific duties plus 15% on derivatives (ingots, wafers, cells, modules); allied 15% inclusive; UK 10%
  authority: Section 232 (Proclamation 11052 of 2026-08-06)
  scope: all origins
  status: scheduled
  series: ETRX-CN-85 (HS 8541) when effective
  verified: no
  source: 91 FR 51975 (2026-08-11)

## Verification status and open questions

Full research with citations and confidence levels: `research/policy_research_2026-08.md` (2026-08-24). Every 2026 entry above is `verified: no` until the maintainer opens the cited primary source and flips it — the print-day skill will not attribute any move to an unverified entry.

Still unresolved after research: (1) whether India's 18% reciprocal rate was ever collected 2026-02-07→02-23; (2) whether the Brazil 25% and the 12.5% forced-labor duty stack on the same entry; (3) status of CAPE Phase 3 (finally-liquidated entries) and the government's Federal Circuit appeal of the refund order; (4) Canada's countermeasure list; (5) the U.S. Reports citation for Learning Resources.
