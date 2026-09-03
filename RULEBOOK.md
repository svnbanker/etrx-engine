# ETRX Rulebook

**US Effective Tariff Rate Index** · version 1.0 · effective 2026-08 (draft until first live print)

## 1. Purpose and benchmark statement

ETRX measures the realized effective duty rate on US imports for consumption — calculated duties as a share of customs value — by country of origin and HS chapter, monthly. It is designed to be usable as a settlement reference: fully rules-based, computed solely from official published US government data, with a published calendar, an immutable first-print convention, and a written fallback policy. No discretion enters the calculation.

## 2. Series definitions

All series use the same formula (§3) over different slices of US imports for consumption.

| Series | Origin (Census CTY_CODE) | HS chapters | Note |
|---|---|---|---|
| ETRX-US | all countries (`-`) | 01–97 | settlement headline; excludes special-provision chapters 98/99 |
| ETRX-US-INCL | all countries (`-`) | 01–99 | companion; published, not intended for settlement |
| ETRX-STEEL | all countries (`-`) | 72+73 | iron and steel + articles thereof |
| ETRX-PHARMA | all countries (`-`) | 30 | pharmaceutical products |
| ETRX-APPAREL | all countries (`-`) | 61+62 | knit + woven apparel |
| ETRX-CN-85 | China (5700) | 85 | electrical machinery and electronics |
| ETRX-CN-84 | China (5700) | 84 | machinery and mechanical appliances |
| ETRX-CN-95 | China (5700) | 95 | toys, games, sports equipment |
| ETRX-EU-87 | European Union (0003) | 87 | vehicles |
| ETRX-MX-87 | Mexico (2010) | 87 | vehicles |
| ETRX-CA-76 | Canada (1220) | 76 | aluminum and articles thereof |
| ETRX-CA-44 | Canada (1220) | 44 | wood and articles thereof |
| ETRX-CA-87 | Canada (1220) | 87 | vehicles |

New series may be added under §11; existing series definitions are never changed in place.

**Settlement classification.** ETRX-US, ETRX-CN-85, ETRX-CN-84, ETRX-STEEL, ETRX-APPAREL, ETRX-CA-76 and ETRX-EU-87 are **settlement-eligible**: they cover slices with substantial monthly customs value and are the series offered as references for financial products. ETRX-US-INCL is **informational** (published for reconciliation, not for settlement). ETRX-CN-95, ETRX-PHARMA, ETRX-MX-87, ETRX-CA-44 and ETRX-CA-87 are **informational pending review**: they are published on the same rules but cover narrower slices whose concentration and month-to-month behaviour are assessed before any product may reference them. Classification changes are methodology changes under §11.

## 3. Formulas

For a slice S (origin × chapters) in statistical month M:

- **Effective rate** = calculated duties(S, M) ÷ customs value of imports for consumption(S, M)
- **Rate on dutiable value** (companion) = calculated duties(S, M) ÷ dutiable value(S, M)
- **Duty-free share** (companion) = 1 − dutiable value(S, M) ÷ customs value(S, M)

Rates are stored rounded to six decimal places (one hundredth of a basis point). Aggregates sum the underlying dollar values before dividing; they are value-weighted, never averages of rates.

**Why calculated duty, not collected cash.** Calculated duty is computed by Census from the duty rates applicable at entry. It is fixed at entry and is never restated by later refund litigation or collections timing. The February 2026 Supreme Court ruling that voided the 2025 IEEPA tariffs triggered a refund process exceeding $100B; cash-collections measures will be distorted by those flows for years, while the calculated-duty series records what importers actually owed at entry, cleanly, through the discontinuity.

**Scope of "calculated duty."** Census computes calculated duty from the tariff-schedule rates applicable at entry, including the additional duties imposed through HTS Chapter 99 provisions (Sections 232 and 301, IEEPA and successor actions). Antidumping and countervailing duties (AD/CVD) are assessed separately by CBP and are **not** included. ETRX therefore measures the tariff-schedule burden; series on goods with large AD/CVD orders (e.g., Canadian softwood lumber within ETRX-CA-44) understate the total trade-remedy burden, by design and by disclosure.

**Why the headline excludes chapters 98/99.** HS chapters 98 and 99 are special-provision classifications (US goods returned, repairs, temporary imports), largely duty-free, carrying material customs value. Including them dilutes the measured duty intensity of commercial trade. The settlement headline is chapters 01–97; the inclusive rate is published beside it for reconciliation with totals-based external measures.

## 4. Data source and provenance

- Source: US Census Bureau International Trade API, monthly imports (HS) dataset — `https://api.census.gov/data/timeseries/intltrade/imports/hs`.
- Variables: `CAL_DUT_MO` (calculated duty), `CON_VAL_MO` (customs value, imports for consumption), `DUT_VAL_MO` (dutiable value), by `CTY_CODE` × `I_COMMODITY` at `COMM_LVL=HS2`.
- Every print stores the API's `LAST_UPDATE` stamp for the month used, plus the print's own vintage date, in the public ledger (`prints.jsonl`).
- The full calculation code path is deterministic; a completeness gate refuses to compute if any required cell is missing, any value is absent, or the chapter-level sum fails to reconcile to the published all-imports total within 0.5% (customs value) / 1.0% (calculated duty). The index is computed whole or not at all — never from partial data.

## 5. Publication calendar

Census publishes monthly trade data with the FT-900 release, typically 35–40 days after the statistical month, at 8:30 a.m. ET on the scheduled date. **ETRX publishes no later than 12:00 noon ET on the day of the release** (the engine's scheduled run lands well before that; the print is normally available within two hours of the release). Where a print is not published by that time, the delay and its reason are stated on the site. The engine probes daily, so catch-up releases (several months at once, off-schedule dates) print on detection, under the same noon-ET commitment for the day detected. "Business day" means a day on which US Federal Reserve Banks are open. The site footer and `latest.json` always carry the next expected release date from the official Census schedule.

## 6. First-print settlement rule

The first value ETRX publishes for a (series, statistical month) is that month's **settlement value**, permanently. It is recorded in an append-only ledger with its vintage date and is never edited, deleted, or restated.

**Backfill caveat (honesty rule):** values for months before the first live print were built retroactively from current Census data and therefore embed all Census revisions to date. They are stamped `backfill` in the ledger and are suitable as history, not as evidence of real-time settlement behavior. True first-print vintages begin with the first live print.

## 7. Revision policy

- Census revises recent months with each release and restates a full year in an annual revision (typically June).
- After each new print, ETRX re-fetches the trailing three settled months; any changed values are appended to the ledger as dated **revision vintages** and published in `revisions.csv`. Settled values are never restated.
- Once a year, after the annual Census revision, a full-history revision sweep is run and logged the same way.
- The public panel (`etrx.csv`) contains settlement values only; the revision file shows what later vintages would have said.

## 8. Fallbacks

- **Delayed release / government shutdown:** ETRX delays. No estimate, no interpolation, no carry-forward is ever published as an index value. The site states the delay and the last settled month.
- **API outage:** the engine retries with backoff and otherwise makes no print; publication resumes on detection.
- **Data defects:** if the completeness gate fails on a published month (missing cells, reconciliation failure), no print occurs; the failure is investigated and documented in the public audit log before any print for that month.

## 9. HS composition changes

HS chapter definitions are stable at the 2-digit level; chapter-level series are robust to sub-heading reclassification within a chapter. Two structural notes are on record:

- **De minimis elimination (2025):** low-value shipments formerly outside the duty system now enter imports for consumption. This is a real change in the measured universe, not an artifact; it is flagged as a structural note on affected series rather than adjusted away.
- Any future WCO HS revision that materially moves goods across chapter boundaries will be documented as a series note with the effective month.

## 10. Country and grouping changes

- Country series use Census Schedule C codes as published.
- ETRX-EU uses Census grouping `0003` ("European Union") **as published by Census**, meaning membership changes flow through at the date Census applies them (Croatia joined 2013-07; the UK left 2020-02). These composition-change dates are series notes; the backfill cross-checks grouping totals against member-state sums around them.
- If Census retires or redefines a code, the affected series is frozen and a successor series is launched under §11 — codes are never silently remapped.

## 11. Methodology-change governance

- The rulebook is versioned. Changes to formulas, series definitions, source, or settlement conventions require a new rulebook version, published with at least one full monthly print cycle of notice before taking effect. No change is ever applied to already-settled values.
- Additions of new series are non-breaking and take effect at announcement.
- Every change, its rationale, and its effective date is recorded in the public audit log.

## 12. IOSCO alignment statement

ETRX is administered with the IOSCO Principles for Financial Benchmarks (July 2013) as its reference standard: the methodology is public and rules-based; input data is official government statistics that the administrator cannot influence; the calculation is deterministic and reproducible by any third party from public data; conflicts of interest are structurally minimal (the administrator holds no positions referencing the index); and this rulebook, the calendar, the fallback policy, and the audit trail are published. A formal IOSCO self-assessment will accompany any use of the index as a settlement reference in a listed or cleared product.

## 13. License, contact, disclaimer

- The published index series, their charts, and this rulebook are licensed CC BY 4.0: free to use, cite and republish, including in commercial research, with attribution ("ETRX — US Effective Tariff Rate Index"). *(Amended 2026-09-03: an earlier non-commercial clause was removed because it made citation in bank and broker research ambiguous.)*
- Commercial redistribution of the data feed, and any use of the index as the settlement reference of a financial product, require a license from the administrator.
- Research and commentary. Not investment advice. Values are derived from official US government data; the administrator does not warrant fitness for any particular purpose.
