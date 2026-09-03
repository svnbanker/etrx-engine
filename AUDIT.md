# AUDIT — append-only

Dated log of every bug, verification, and decision — including decisions to change nothing. Newest entries at the bottom.

## 2026-08-23 — repo created; planning-time verification summary

Facts verified during planning (live probes + Census documentation), which this build relies on:

- Key required for all data queries; failure mode is HTTP 302 → HTML with header `X-DataWebAPI-KeyError` (not a JSON error). Engine sets `allow_redirects=False` and treats it as a distinct FATAL. Metadata endpoints remain keyless.
- HTTP 204 = month not published — used as the new-month probe signal.
- `CTY_CODE='-'` returns a real "TOTAL FOR ALL COUNTRIES" row, tagged `SUMMARY_LVL=DET` (filtering DET does NOT remove it). Design pins an explicit CTY_CODE on every call; no summing across countries anywhere.
- EU aggregate exists as Census grouping `0003`; composition changed in-window (Croatia 2013-07, UK 2020-02) — handled in RULEBOOK §10.
- History floor contested in docs (2010 vs 2013) — backfill discovers it empirically.
- Ch. 99 duty (301/232 actions) is attributed to underlying chapters 1–97; Ch. 98 is material and duty-free → headline settles ex-98/99 (RULEBOOK §3).
- FT-900 2026 schedule fetched from census.gov (releases as late as the 29th during catch-up) → daily cron, not a windowed one.
- `--selftest` passes: gate, compute, validate, jump logic, month arithmetic on fixtures.

## 2026-08-23 — day-one key-gated checks: ALL PASS

Key activated ~15:45 UTC. Incidentally, the unactivated key earlier today exercised the 302/`X-DataWebAPI-KeyError` FATAL path against the live API — the failure drill passed for free.

1. **History floor: 2010-01** — data present with duty variables populated (2010-01 headline-incl = 1.36%). Backfill covers 2010→present, 18 months more than the guaranteed 2013 floor.
2. **Chapter scan 2026-06: 98 chapter rows, zero non-chapter rows.** Ch. 98: $10.6B value, $14M duty (material, ~duty-free — as designed). Ch. 99: $3.2B value, **zero** calculated duty. Ex-98/99 headline design empirically justified: $13.9B of duty-free value would otherwise dilute the denominator.
3. **Checksum: exact.** Scan sums equal the grand-total row to the dollar (0.000% off) on both customs value and calculated duty. The 0.5%/1.0% tolerances stay as revision-timing headroom.
4. **CN-85 cell: exactly 1 row** (no RP split); June 2026 rate 19.62%.
5. **EU grouping 0003: exactly 1 row** ("EUROPEAN UNION"); EU-87 June 2026 rate 13.92%.
6. **`LAST_UPDATE` returns the string "0"** on this endpoint — populated but uninformative; stored as-is, vintage_date carries provenance instead. No code change.
7. **2026-07 probe: HTTP 204** — new-month detection confirmed against reality (July data due Sept 3).
8. Headline-incl June 2026 = **6.81%**, consistent with Penn Wharton's ~7.1% (methodology differs slightly; ballpark reconciles).
9. Smoke test (3 months from floor): gate 3/3, and the 2010 baseline is economically coherent — apparel ~12% (high-MFN chapter), EU-87 dutiable-value rate 2.52% ≈ the statutory 2.5% car tariff, Mexico/Canada ~0 (NAFTA), pharma 0.0%.

Backfill battery results + the three manual DataWeb spot-checks: recorded below after the full run.

## 2026-08-23 — backfill attempt 1 aborted by API timeout streak; retries hardened

First full backfill FATALed at month ~60 of ~198: three consecutive 60s read-timeouts (~650 calls had succeeded before it). The fail-loud design held: no ledger write, no publish. Diagnosis: transient Census-side flakiness under sustained sequential load; 3 retries × short backoff (~7s total) cannot ride out a multi-minute blip. Fix: shared `requests.Session` (connection reuse) + retries 3→5 with backoff 2·2^n capped at 45s (~1 min of backoff + up to 5×60s timeouts ≈ 6 min tolerance per call). Also a tooling lesson: the run was invoked as `backfill.py | tail`, so the shell reported tail's exit 0 and masked Python's exit 1 — background runs are now invoked bare so exit codes are truthful. Selftest re-passed after the change.

## 2026-08-23 — backfill attempt 2 failed identically; diagnosis upgraded to throttling

Attempt 2 (session + 5 retries, ~45s backoff cap) died the same way at ~72 months (~800 calls, ~12 min of sustained traffic): five consecutive 60s read-timeouts. Two failures at similar depth is not random flakiness — Census appears to throttle sustained query streams by stalling connections rather than returning 429s. Fixes for attempt 3: (a) timeouts now back off in minutes (15s→60s→240s→300s→300s ≈ 16 min tolerance — a stall is a cooldown signal, not a retry-fast signal); (b) steady pace slowed (`POLITE_PAUSE` 0.2→0.35s); (c) `backfill.py` now checkpoints each completed month to `backfill_checkpoint.jsonl` (gitignored) and resumes from it, so a failure never again costs completed work. Checkpoint deletes itself after a successful ledger write. Selftest re-passed.

## 2026-08-23 — attempt 3: the wall is call-volume, not pacing; supervisor loop deployed

Attempt 3 (0.35s pace, minutes-long cooldowns) died at month 63 (~650 calls) after riding out ~20 minutes of stalls — same depth as attempts 1 (~650) and 2 (~800) despite different pacing. Conclusion: an undocumented per-key/per-IP call-volume wall around 600–800 calls per window; cooldowns of minutes don't clear it. The checkpoint held: 62 months banked, reruns resume instantly. Remedy: an auto-resuming supervisor (rerun `backfill.py` until exit 0, 10-min cooldowns between attempts, max 10) — each window banks another ~60 months. **The daily print engine is immune** (~10 calls on no-op days, ~40 on print days — two orders of magnitude below the wall). Backfill is a once-ever event; no engine changes warranted beyond what's already in.

## 2026-08-24 — backfill COMPLETE on supervisor attempt 5; battery PASS

198 months (2010-01 → 2026-06), 2,574 ledger rows, all stamped `backfill`. Full report in `backfill_report.md` (code b66f19d). Verdicts:
- **Annual reconciliation (ETRX-US-INCL):** 2013–2017 1.39–1.52%, 2018 1.82%, 2019 2.65%, 2020 2.76%, 2021 2.96%, 2022 2.78%, 2023 2.35%, 2024 2.36% — every full year inside its band. 2025 **7.65%**; 2026 H1 7.52%.
- **Regime checks:** China-85 0.74% (2018-01) → 6.79% (2019-12) PASS; China-85 2025 peak **46.4%** PASS; headline-incl 2025 peak 10.8% PASS.
- **Parity:** 2010-01, 2018-04, 2026-06 re-fetched through the live path — exact match.
- **Plausibility:** no series above 60% in any month.
- **External cross-check:** June 2026 headline ex-98/99 = **7.13%** vs Penn Wharton's independently modeled ~7.1% — reconciles.
- **Methodology finding:** ETRX-CA-44 (Canadian wood) prints 4.6% despite large softwood-lumber AD/CVD orders → confirms Census calculated duty excludes AD/CVD (assessed separately by CBP). Added as an explicit scope statement to RULEBOOK §3. No code change.
- **Spot-checks: CLOSED 2026-08-24 (5/5 exact).** USITC DataWeb requires an account and blocks automated access, so instead of re-reading the same HS2 rows through a second interface, each published figure was rebuilt from a **finer aggregation level** of the source — a stricter test, since it exercises a different set of API rows and catches aggregation, filtering and level-selection errors, which are the plausible failure modes. Results, all matching to the dollar (0.0000% difference on both customs value and calculated duty):
  - 2019-06 ETRX-CN-85: published $10,061,236,828 / $583,524,343 = 5.7997%; rebuilt from 46 HS4 lines — exact; rebuilt again from 262 HS6 lines — exact.
  - 2023-03 ETRX-US-INCL: published $262,734,765,807 / $5,649,479,698 = 2.1503%; rebuilt from the 98-chapter scan — exact; rebuilt from 1,231 HS4 lines — exact.
  - 2025-09 ETRX-STEEL: published $4,893,860,187 / $1,733,950,153 = 35.4311%; rebuilt from 55 HS4 lines in chapters 72–73 — exact.
  A DataWeb UI confirmation remains available as a third path if a licensee ever asks for one; it would test the same source through a different front end rather than a different aggregation.

## 2026-08-24 — launch plumbing shipped (plan v2 steps 1–4)

Site rebuilt as a static multi-page set from one generator: index, series list + 13 series pages (deep-linkable, each with cite-as block and stats), methodology (rulebook rendered from the versioned markdown), verify (worked example with real dollar inputs + one-URL API reproduction + DataWeb route), data (downloads, dictionary, license), calendar (FT-900 dates + signup slot), about (brand-first, independence statement), press (boilerplate, chart pack), revisions log. Credited standalone chart SVGs for every series, rendered to PNG via rsvg-convert (CI installs librsvg2-bin; local brew). Per-series JSON + `llms.txt` for machine consumers. `/print-day` skill (draft-only, ledger-grounded) and `policy_events.md` seeded with 26 actions 2018→2026 (2026 entries flagged for primary-source verification). Visual verification: index, series, verify, methodology pages screenshot-checked at 1440px; PNG headline chart inspected. 55 artifacts + 13 PNGs per publish; publish remains deterministic from the ledger.

## 2026-08-24 — agent seats, launch package, products, ledger rebuild

- **Seats built:** `scout.py` (Google News RSS + `--input` fallback for sandboxed runs), `/newsjack`, `/citations` (+ `research/citations.md`), `cut.py` + `/cut` (HS2/4/6/10), `client_index.py` + `/client-index`, `/dossier`. Cloud routines created: newsjack scout (13/17/21 UTC), citation tracker (Mon 14 UTC). Test run of the scout in the cloud: repo clone + skill execution worked; Google News is blocked by the sandbox egress (403) → the skill now falls back to the agent's web-search tool. The scout also found this weekend's Canada/India actions before any of us did.
- **Launch package:** `launch/story.md` (the finding: the ruling clawed back 41% of the 2025 increase, 59% retained because Section 122 then Section 301 replaced the IEEPA layers within days; steel/aluminum untouched — 232), `launch/pitches.md` (exclusive, embargo, Canada, thread, LinkedIn, bios), `heatmap.py` → `docs/charts/heatmap-2026-06.png` (12 origins × 24 chapters; China copper 73.6%, aluminum 65.2%).
- **Products:** `feed.py` (Product 1: all chapters × top-60 origins + EU + all, 2010→, checkpointed; build running), `feed/README.md`, `research/feed_onepager.md` (pricing anchors, first-ten targets); `client_index.py` (Product 2; illustrative retailer mix: 16.32% client vs 10.24% pooled, peak 28.85% May 2025); `research/licensing/contract_concept.md` + `swap_term_sheet.md` (Product 3 concepts). Site data page gained a "Data products" section + a public Vietnam all-chapters sample (17,837 rows).
- **Research:** `research/press_list.md` (46 names, top-10 for the exclusive); `research/policy_research_2026-08.md` → `policy_events.md` rebuilt: Feb 24 duty = Section 122 (10%, expired Jul 24, CIT held unlawful May 7, stayed); Section 301 forced-labor duties from Jul 24 (10/12.5%, 232 + USMCA goods exempt); pharma 232 = Proclamation 11020, phase 1 Jul 31 2026 (the 2025-10-01 pharma entry was wrong — consistent with ETRX-PHARMA at 0.16% in June); Section 338 50% on Canada Aug 22 excludes 232 goods and vehicles (only ETRX-CA-44 should register); China fentanyl cut to 10% Nov 2025; 232 metals restructurings Apr 6 / Jun 8; Brazil 301 25% Jul 22; scheduled: drones Sep 3, pharma phase 2 Sep 29, polysilicon Dec 4. All 2026 entries remain `verified: no` pending the maintainer's primary-source check.

## 2026-08-24 — print-day dress rehearsal: all checks pass

Full live path exercised in an isolated copy of the repo (June rows removed from a copied ledger so the engine would discover 2026-06 as a new month). Nothing was posted, deployed or written to the real repo.

- **New-month detection → gate → compute → validate → publish → ledger append**: all executed in order; 13 rows appended with `first_print: true`, `vintage_note: "live"`.
- **Live path reproduces backfill exactly**: all 13 series matched the backfilled June values on rate, rate_dutiable, duty_free_share, con_val, cal_dut and dut_val — **zero mismatches**. The settlement record therefore does not depend on which code path produced a value.
- **Idempotency**: second run printed "No new data month (latest settled: 2026-06). No-op."
- **Site**: 59 artifacts + 14 charts regenerated; headline 7.13% on the page; `latest.json` carried `vintage_note: "live"`.
- **X thread**: composes to 4 posts, all inside the 280-character limit; not sent.
- **Failure drill, bad key**: `FATAL: Census API rejected the key (302/X-DataWebAPI-KeyError)…`, exit 1, nothing written.
- **Failure drill, missing required chapter**: gate reported "required chapter 72 missing from scan" and refused to compute.

Package format approved and kept as `drafts/REHEARSAL-2026-06.md` — the shape `/print-day` produces on release day. Also wired: the newsletter signup line renders on every page when `SITE["signup_url"]` is set and is omitted entirely when empty (both states verified).

## 2026-08-24 — Canada "vehicles and steel" reports: threat, not action

Press on 2026-08-24 (WaPo "announces", WSJ and NYT "threatens") described new US tariffs on Canadian vehicles and steel. Checked against the Federal Register API for documents published 2026-08-20→24 mentioning Canada: the only hits are Proclamation 11056 (doc 2026-17294, the three-day Section 338 delay already in the ledger, confirmed via govinfo), an OMB collection notice under Proclamation 10984, and an unrelated AD/CVD deadline notice. **No instrument exists**, so nothing enters at a new rate and no ETRX series can move on it. Logged in `policy_events.md` as announced-only with no data effect.

Also recorded there: Proclamations 11046/11047/11048 are named for the *Canadian practices* being retaliated against (liquor bans, cheese quotas, Canada's tariff on non-USMCA US vehicles), not for the US products being taxed — which is very likely why coverage keeps saying the action hits Canadian cars and steel when 232 goods and vehicles are excluded. Good `/correction` target, and a case where ETRX's realized-versus-announced distinction is the story.

## 2026-08-24 — document de référence (« la bible ») rédigé

`docs-internal/etrx-bible.html` + `ETRX-bible.pdf` : document pédagogique complet en français, de « qu'est-ce qu'un droit de douane » jusqu'à la défense de chaque choix méthodologique. Sept parties : le problème (douane US, autorités légales, chronologie 2018–2026, les trois mesures concurrentes), ce qu'est un indice (recherche vs règlement, IOSCO, économie des indices), la méthodologie ETRX (formule, droits calculés vs perçus, exclusion 98/99, limites, 13 séries, premier print, millésimes, fallbacks), la machine (source, architecture, garde-fous, automatisation, vérification), les données (2010–2026 avec tous les chiffres du panneau), le modèle d'affaires, et les références (glossaire de 20 termes, 5 objections traitées). Tous les chiffres proviennent du panneau ETRX ; aucun n'est arrondi différemment du registre. Interne et pédagogique — le RULEBOOK reste la méthodologie officielle et prévaut.

## 2026-08-25 — le flux est un panneau creux : précision de description corrigée

La session Claude « école/carrière » a repéré que le CV présentait 946 807 observations comme le produit de 62 × 98 × 198, qui vaut 1 203 048. Vérification empirique sur les fichiers réels : 946 807 lignes pour 1 203 048 cellules théoriques, soit **78,7 % de remplissage et 256 241 cellules vides**. Le panneau est creux par nature — tous les pays n'importent pas dans tous les chapitres tous les mois (le fichier le moins garni est à 21 % de remplissage ; le total tous pays est plein à 19 404 = 98 × 198). Les lignes absentes sont des absences de commerce, omises plutôt que remplies de zéros : une ligne manquante signifie « aucun commerce enregistré », jamais « taux de zéro ».

Deuxième imprécision corrigée dans la foulée : « 62 pays d'origine » est faux — ce sont **60 pays**, plus le regroupement UE (code 0003) et le total tous pays, dont ni l'un ni l'autre n'est un pays.

Descriptions corrigées dans `feed/README.md`, `research/feed_onepager.md` et la bible. Règle retenue : ne jamais présenter le chiffre comme une multiplication, toujours comme un compte d'observations non vides.

## 2026-08-25 — KEY-FIGURES.md : supprimer la possibilité de citer un chiffre faux

Trois chiffres ETRX inexacts ont circulé en deux jours (« droits réellement payés » dans un courriel destiné à la presse, puis 62 pays au lieu de 60 et une multiplication de panneau creux sur le CV). Le point commun : ils ont tous été reconstitués de mémoire plutôt que comptés.

Réponse structurelle plutôt que disciplinaire : `figures.py` génère `KEY-FIGURES.md`, où chaque chiffre citable est **compté sur les fichiers réels** et accompagné de sa source. Régénéré automatiquement à chaque publication (branché dans `publish()`), donc jamais périmé. Contient un avertissement explicite contre la multiplication du panneau creux, et la formulation correcte à réutiliser telle quelle.

Règle qui en découle : ne jamais citer un chiffre ETRX sans l'avoir lu dans ce fichier. Si un chiffre n'y figure pas, il n'est pas vérifié.

## 2026-08-25 — quatre vérifications croisées en deux jours, et ce qu'elles enseignent

Bilan de la coordination entre sessions Claude sur ces deux jours : **quatre fois, une vérification a changé la réponse**, et aucune n'aurait été trouvée si l'une des parties avait fait confiance à l'autre.

1. Un agent a décrit l'indice comme « net des remboursements » dans un courriel destiné à une journaliste couvrant précisément les remboursements — l'inverse exact de la méthodologie. Intercepté avant envoi → `DESCRIBING_ETRX.md` créé et rendu obligatoire.
2. Le CV portait la même inversion (« droits réellement payés »). Corrigé après lecture du fichier canonique.
3. Le CV présentait 946 807 observations comme le produit 62 × 98 × 198, qui vaut 1 203 048. Vérification sur les fichiers : panneau creux à 78,7 %. Au passage, « 62 pays » était faux — 60 pays plus deux agrégats.
4. Un chiffre arrondi à « ~950 000 » alors que le compte exact donne 947 000, sur un projet dont l'argument est *mesuré, pas estimé*.

Réponse structurelle plutôt que disciplinaire : `figures.py` → `KEY-FIGURES.md`, chiffres comptés sur les fichiers, régénérés à chaque publication. Règle : ne jamais citer un chiffre ETRX sans l'avoir lu dans ce fichier.

**Bénéfice inattendu de l'échange** : la meilleure réponse à l'objection « et si les tarifs redescendent » est sortie de ce va-et-vient. L'année la plus basse après la marche (2,45 % en 2023) dépasse l'année la plus haute avant elle (1,58 % en 2015) de 55 %. C'est min contre max — aucune année de base à contester — et ça ne prédit rien, ça constate. Ajouté à la bible (§33) et au plan de distribution.

À noter, parce que c'est exactement ce que l'indice vend : la vérifiabilité radicale ne vaut que si quelqu'un vérifie effectivement.
