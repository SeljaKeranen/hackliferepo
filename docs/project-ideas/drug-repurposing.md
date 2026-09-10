# Drug Repurposing for Aging: Evidence, Pain Points, Current Programs, and Project Opportunities

## Summary

Drug repurposing asks whether an existing approved compound can act on an aging-related target or phenotype. For this hackathon it maps most directly onto Track 1's second challenge: from an ageing phenotype to a target and a chemical perturbation. The dataset library covers the supporting layers well — perturbation screens (LINCS 16, sci-Plex 21, JUMP 80), compound databases (ChEMBL 89, PubChem 90, ZINC 91), and knowledge graphs (Open Targets 8, PrimeKG 50, Hetionet 125) — but outcome labels are the bottleneck. The NIA Interventions Testing Program (87) is the cleanest mammalian intervention-outcome set (pre-registered protocols, negative results published), and it is mouse-only. Human trials measured on 2026-09-09 are small or use surrogate endpoints: MILES metformin (n=16), fisetin frailty studies still enrolling by invitation, and completed senolytic studies in disease settings, not lifespan.

| Priority candidates | Pain points and output | Core data and boundaries |
| --- | --- | --- |
| R1 Geroprotector candidate ranking validated against NIA ITP outcomes (Track 1, first choice) | Literature labels are heterogeneous and positive-biased; use ITP's negative-results-included labels as the yardstick | 40, 32 candidates; features from 89, 93, 94; labels from 87; one compound class held out |
| R2 Longevity claim evidence-chain audit (Track 3 alternative) | Cell or mouse results promoted as human aging effects; separate the evidence ladder with dated sources | 112, 138, 114; metformin as the worked claim; "nothing reliable found" states |
| R3 Aging-signature reversal via connectivity mapping (Track 1) | Direction of effect unclear from single databases; cross-check reversal direction against ITP outcomes | 82, 144 signature; 94, 164 query; 87 held-out labels |
| R4 Knowledge-graph repurposing ranker (Track 1) | Graph methods overclaim on co-occurrence benchmarks; evaluate on ITP-held-out compounds against a rule baseline | 125, 50, 8; targets from 82, 37; honesty citation 111 |
| R5 Purchasability and safety triage (companion) | Predicted hits cannot be bought or carry safety flags; deterministic identity, vendor, and adverse-event checks | 90, 135, 91, 133, 134, 92 |
| R6 Senescence phenotype to target to compound (Track 1 challenge 2 direct) | Senolytics are the best-studied case; predicted direction must match known senolytics before scaling | 88, 145, 44, 37, 21, 80; D+Q and fisetin as positive controls |
| R7 Drug repurposing research funding classifier (Track 3) | Repurposing versus de novo and aging-biology-direct versus disease framing conflated in project text | 141; manual labels, held-out by project |

Evidence retrieved 2026-09-09. This article follows the structure of the [Aging and Dementia Risks](aging-and-dementia.md) and [Nordic Elderly Care Industry](nordic-eldercare-industry.md) research, uses registry APIs and primary literature as dated evidence, and separates policy goals, research findings, and team recommendations. It is project-selection research, not medical advice; no statement here endorses any compound for human use.

## Assessment

The core contradiction: repurposing looks like a shortcut because approved drugs already have safety records, but the hard part is the outcome label. What counts as "working" for aging is contested. ITP (87) offers mouse lifespan with negative results published; DrugAge (40) and Geroprotectors.org (32) aggregate literature experiments of heterogeneous design and direction; human studies measure gene expression, frailty components, or biomarkers, never lifespan. A ranker validated only against literature co-occurrence inherits the literature's positive bias. The weekend's falsifiable target is therefore narrow: a method that beats a simple rule baseline on a held-out compound class using ITP's gold-standard labels.

## Why demand continues to grow

The demographic pressure is the same as for the eldercare topics, but the repurposing angle has its own driver: a new chemical entity takes over a decade and high cost to reach approval, while an approved compound with known human safety can be tested in older populations faster. Trial activity measured on 2026-09-09 confirms this: sirolimus is recruiting a functional-decline study in older adults (NCT05237687), fisetin frailty studies are enrolling by invitation (NCT03430037, NCT03675724), and the DREAM platform has completed observational drug-repurposing cohorts for Alzheimer's disease (NCT05635357, NCT05768945).

Demand growth does not mean any repurposing tool is useful. For computational geroscience, the challenge is a label set that penalizes failure; for research editors, it is an evidence ladder that separates cells, mice, and humans; for funders, it is distinguishing repurposing work from aging-biology research. The three use cases need different inputs and different success metrics.

## Pain Points and Corresponding Solutions

| Current pain points | Evidence or specific gaps | Existing or proposed solutions | Monitoring results needed |
| --- | --- | --- | --- |
| Literature intervention labels are heterogeneous and positive-biased | DrugAge and Geroprotectors.org aggregate heterogeneous experiments; ITP publishes pre-registered protocols and negative results | Use ITP (87) as the label yardstick; report which compounds failed, not only hits | Held-out accuracy versus a rule baseline; false discovery when trained on co-occurrence |
| Compound identity does not join cleanly across sources | DrugAge-style names and PubChem CIDs resolve ambiguously | Normalize names with RxNav/RxNorm (135), resolve to CIDs with PubChem PUG-REST (90) | Identity resolution rate; ambiguous-name error cases shown, not dropped |
| Predicted hits cannot be purchased or carry safety flags | ZINC15 (91) has vendor links; openFDA (133) has FAERS adverse-event reports | Deterministic triage before any candidate is called testable | Vendor availability; ADR and indication flags; excluded candidates with reasons |
| The evidence ladder is flattened in public claims | MILES (NCT02432287) is a 16-person pilot; senolytic trials use disease endpoints, not lifespan | Separate cells, mice, and humans; state sample size and endpoints next to every claim | Rate of unsupported claims; missing-endpoint flags; manual verification time |
| Models overclaim on benchmarks | Benchmark caution (111): deep perturbation models do not yet beat simple linear baselines | Compare every model against a rule baseline; hold out a compound class | Relative error versus baseline; negative results reported as deliverables |
| Human outcome labels are scarce | No completed human trial measures lifespan; biomarker changes are not health outcomes | Treat human trials as supporting evidence only; falsification against ITP | Claim boundaries stated in the demo; no clinical recommendations |
| Safety in older adults is under-documented | Off-label use in elderly populations appears in FAERS signals | Check openFDA (133), DrugCentral indications and ADRs (92), CompTox in-vitro safety (134) | Flagged safety conflicts; wrong-indication claims caught |
| Senescence target space is crowded but direction evidence is shallow | SenNet (88) and SASP Atlas (145) map senescence; direction predictions are mostly untested | Hold out the senolytic class as positive controls (D+Q, fisetin) | Direction concordance; false positives versus known senolytics |

## Key Intervention Research and Interpreting Boundaries

| Research or registry record | Design and status | What it actually shows | Implications for the project |
| --- | --- | --- | --- |
| MILES, NCT02432287 | Metformin in Longevity Study; completed; n=16; started 2014-10 | Small pilot with muscle gene-expression endpoints | Cannot support any longevity claim; the canonical example of a pilot promoted as proof. [Registry record, accessed 2026-09-09](https://clinicaltrials.gov/api/v2/studies/NCT02432287) |
| Antecedent Metabolic Health and Metformin Aging Study, NCT04264897 | Completed; n=166; started 2020-07 | Metformin in non-diabetic older adults with metabolic endpoints | Larger, but still biomarker and metabolic endpoints; no lifespan outcome. [Registry record, accessed 2026-09-09](https://clinicaltrials.gov/api/v2/studies/NCT04264897) |
| Fisetin frailty studies, NCT03430037, NCT03675724 | Enrolling by invitation; older women and adults | Recruitment-based design; no results guaranteed at submission time | Registry presence is not trial results; a good "registered but no results" demo state. [Registry records, accessed 2026-09-09](https://clinicaltrials.gov/api/v2/studies/NCT03675724) |
| D+Q in disease settings, NCT05506488, NCT04063124 | Completed; fibrotic NAFLD and Alzheimer's disease | Disease endpoints in defined patient groups | Senolytic direction evidence is disease-specific, not aging-general. [Registry records, accessed 2026-09-09](https://clinicaltrials.gov/api/v2/studies/NCT05506488) |
| Sirolimus functional decline, NCT05237687 | Recruiting; n=10; started 2026-03 | Functional outcomes in older adults | A current anchor for "what human geroprotection trials measure today". [Registry record, accessed 2026-09-09](https://clinicaltrials.gov/api/v2/studies/NCT05237687) |
| REPROGRAM protocol | Protocol paper, 2026 | Assessment of biological effect of geroprotectors in humans | Shows which biomarkers current trials use; biomarkers are not outcomes. [PMID 42308222](https://pubmed.ncbi.nlm.nih.gov/42308222/) |
| Metformin frailty randomized trial | Randomized trial, 2026 | Metformin to reduce frailty in older adults with glucose intolerance | Frailty is a legitimate endpoint, but population-restricted. [PMID 42620010](https://pubmed.ncbi.nlm.nih.gov/42620010/) |
| Revisiting metformin as a geroprotector | Review, 2026 | Mixed evidence across systems | Cite as the current "claims exceed evidence" reference. [PMID 41832079](https://pubmed.ncbi.nlm.nih.gov/41832079/) |
| Interventions that decrease epigenetic clocks | Comprehensive list, 2026 | Many interventions move clocks; few have outcome evidence | Clock reversal is a feature, not an outcome label. [PMID 42294499](https://pubmed.ncbi.nlm.nih.gov/42294499/) |
| Network-driven repurposing targeting hallmarks of aging | Methods paper, 2026, open access | Network methods propose candidates against aging hallmarks | Literature context for R4; its evaluation is co-occurrence, ours must be held-out labels. [PMID 42362889](https://europepmc.org/article/PMC/PMC13375550) |
| Precision repurposing with patient-specific knowledge-graph loss | Methods paper, 2026 | Patient-specific ranking on knowledge graphs | Shows the KG state of the art; supports the need for independent labels. [PMID 41974265](https://pubmed.ncbi.nlm.nih.gov/41974265/) |
| Synergistic geroprotector mapping with machine learning | Methods paper, 2026 | ML/GNN synergy mapping | Prior work to beat, with a rule baseline. [PMID 42376863](https://pubmed.ncbi.nlm.nih.gov/42376863/) |
| Gero-LLM | Methods paper, 2026 | Multimodal LLM for geroprotector discovery | Context for what reviewers will compare against. [PMID 42013268](https://pubmed.ncbi.nlm.nih.gov/42013268/) |
| Low-dose fisetin and chronic inflammation | Observational, 2026 | Supplementation association, not trial | Association evidence, ladder position below RCTs. [PMID 42633989](https://pubmed.ncbi.nlm.nih.gov/42633989/) |
| Advancements in longevity pharmacology | Review, 2026 | Clinical progression status of longevity pharmacology | Source for the "what trials exist today" section. [PMID 42397379](https://pubmed.ncbi.nlm.nih.gov/42397379/) |

## Which Solutions Have the Strongest Practical Foundation?

1. ITP-held-out ranking (R1). Real labels, open data, negative results included; the evaluation is the deliverable, so a negative result is still a finished project.
2. Claim audit (R2). Track 3 names PubMed and ClinicalTrials.gov; every check is manually verifiable by judges.
3. Signature reversal (R3). Runs end-to-end today through L1000CDS2 (94), but labels downstream are weak; keep it tied to ITP concordance.
4. Knowledge-graph rankers (R4). Implementable in hours, but evaluation on co-occurrence is circular; only worthwhile with the held-out ITP check.
5. Senolytics as a case study (R6). The best-documented direction evidence in the field; use D+Q and fisetin as positive controls before any scaling claim.

Anything promising a human aging effect needs target populations and long-term outcomes; no such label exists in the open data, so every claim in the demo stays at "candidate ranked" or "claim unsupported".

## Insights from this Hackathon

Track 1's second challenge (phenotype to target to chemical perturbation, with predicted direction, independent evidence layers, and a validation experiment) is the direct fit; R6 is its template. Track 1's third challenge (choose the next experiment with highest information gain) maps to the held-out compound-class design in R1 and R3. The briefs' suggested open-data stack — Tabula Muris Senis (81), Human Protein Atlas (24), JUMP (80), EUbOPEN (79), Guide to PHARMACOLOGY (78) — is open except EUbOPEN, which is JavaScript-only with no bulk download found; plan interactive queries for it.

Every Track 1 brief requires a falsification criterion and a held-out evaluation, and says biological validity scores above UI polish. Concretely: hold out one compound class (rapalogs or senolytics, decided before training), fix a rule baseline, and report the model's failure cases if it cannot beat the baseline. Entry 111 is the citation judges know about deep perturbation models; cite it when stating model uncertainty.

Track 3's evidence-chain audit challenge names PubMed and ClinicalTrials.gov; R2 and R7 fit it. Track 4 is not a fit for molecular repurposing without a confirmed clinical workflow; do not present ranking output as a clinician tool.

## Hackathon projects based on existing dataset candidates

R numbers are used only in this article; numbers in parentheses are dataset entries from [data-resources.md](../data-resources/data-resources.md) (1–81) and [data-resources-extended.md](../data-resources/data-resources-extended.md) (82–164). Candidates are independent; one is chosen to complete on the weekend.

| Priority | Project and target users | Pain points to optimizable solutions | Core data and minimum output |
| --- | --- | --- | --- |
| First choice | R1 Geroprotector candidate ranking validated against NIA ITP outcomes, computational geroscience researcher | Biased literature labels to ITP's negative-results-included yardstick | 40, 32 candidates; 89, 93, 94 features; 87 labels; one compound class held out |
| Track 3 alternative | R2 Longevity claim evidence-chain audit, research editor | Flattened evidence ladders to separated cells, mice, humans | 112, 138, 114; metformin as worked claim |
| Track 1 | R3 Aging-signature reversal via connectivity mapping, computational biologist | Unclear effect direction to ITP-concordance check | 82, 144 signature; 94, 164 query; 87 held-out |
| Track 1 | R4 Knowledge-graph repurposing ranker, ML engineer | Circular co-occurrence evaluation to held-out labels | 125, 50, 8; targets from 82, 37; baseline rules; 111 |
| Companion | R5 Purchasability and safety triage, wet-lab collaborator | Unbuyable or flagged hits to deterministic checks | 90, 135, 91, 133, 134, 92 |
| Track 1 challenge 2 | R6 Senescence phenotype to target to compound, geroscience researcher | Shallow direction evidence to held-out senolytic controls | 88, 145, 44, 37, 21, 80; D+Q, fisetin controls; 156 |
| Track 3 | R7 Drug repurposing research funding classifier, research policy analyst | Conflated project framings to label sets with held-out projects | 141; manual labels, project-level reserves |

### R1. Geroprotector candidate ranking validated against NIA ITP outcomes

The user is a computational geroscience researcher. The question is limited to: which literature candidates from DrugAge (40) and Geroprotectors.org (32) does the model rank as lifespan-extending, and does that ranking beat a simple rule when one compound class is held out?

Features come from ChEMBL bioactivity (89), BindingDB affinities (93), and L1000CDS2 characteristic-direction signatures (94). Labels come from ITP (87): lifespan extension outcomes across 54 compounds and 164 trials at three sites, with negative results included. The minimal demo ranks a fixed candidate list, shows the top candidates with per-layer evidence, and always shows the rule baseline (count of positive literature annotations) next to the model.

Verification: decide the held-out compound class before training (rapalogs or senolytics); report precision at k and AUC against the baseline; if the model cannot beat the literature-count rule, deliver the rules and the error analysis as the result. Falsification criterion: the model must beat the baseline on the held-out class or the claim "feature layers add signal" is rejected. Boundaries: mouse lifespan labels; a rank is not a prescription; purchasability and safety are handled separately in R5.

### R2. Longevity claim evidence-chain audit (Track 3 alternative)

The user is a research editor or evidence reviewer. The worked claim: "metformin slows aging in humans." The system extracts, for each supporting source, the study population, intervention, comparison, endpoint, time window, and sample size, and places it on a ladder: cell studies, worm or mouse lifespan, human biomarker studies, human randomized trials with clinical endpoints, and registered trials without results.

Probe-verified material from 2026-09-09: MILES (NCT02432287, n=16, completed), the Antecedent Metabolic Health study (NCT04264897, n=166, completed), the metformin frailty randomized trial (PMID 42620010), the healthspan-related outcomes analysis in type 2 diabetes (PMID 42310907), and the review "Revisiting metformin as a geroprotector" (PMID 41832079). The output for the claim is "no completed human trial measures lifespan; the claim exceeds the evidence" plus the ladder with every rung dated and linked.

Verification: manually check 20–30 claim-evidence pairs, reserved by study; compare a keyword baseline against structured extraction with source binding; report unsupported-claim rate, missing key evidence, and refusal rate. Falsification: the structured pipeline must reduce unsupported judgments without increasing omissions. Boundaries: an audit is not a clinical effectiveness judgment.

### R3. Aging-signature reversal via connectivity mapping

The user is a computational biologist. Build an aging gene signature from GenAge (82) and the conserved DR expression signature in GenDR (144), optionally extended with AgeAnno (126) tissue signatures, and query L1000CDS2 (94) or clue.io (164) for compounds whose signatures reverse it. Rank by concordance and sign direction.

The held-out check is ITP (87): do ITP-positive compounds receive systematically different reversal scores than ITP-negative ones? Falsification: if the reversal score cannot separate the two groups better than random on the held-out class, report that reversal concordance alone carries no signal. Boundaries: L1000 signatures come from human cell lines, mostly cancer lines; they are not organism-level aging, and L1000CDS2 is the working route because the iLINCS REST API serves metadata only.

### R4. Knowledge-graph repurposing ranker

The user is an ML engineer. Use Hetionet (125, CC0, static since 2016), PrimeKG (50), or Open Targets (8); seed aging targets from GenAge (82) and CellAge (37); score drug-to-aging-target paths or embeddings; rank candidates. Cite the KG state of the art as context (PMID 41974265, PMID 42362889).

Evaluation is the same held-out ITP design as R1, plus a degree or product-of-experts rule baseline, because co-occurrence benchmarks make KG methods look better than they are; entry 111 applies to the model claim. Falsification: if the KG score does not beat the rule baseline on the held-out class, submit the rules and boundary cases. Boundaries: KG edges are co-occurrence and citations, not causal evidence.

### R5. Purchasability and safety triage (companion pipeline)

Deterministic checks, no model: candidate name to RxNav/RxNorm (135), to PubChem CID (90), to ZINC15 vendor availability (91), to openFDA labels and FAERS signals (133), to CompTox Tox21/ToxCast flags (134), and to DrugCentral indications and adverse events (92). Output is a per-candidate card with identity, vendors, and safety flags. Resolution failures must be displayed, not silently dropped.

Verification: manually check about 20 candidates against the source pages and report resolution rate and flag accuracy. This pipeline has no learned component, so its success metric is verification accuracy; it exists to catch "the hit cannot be bought or is flagged unsafe" before R1 or R6 claims a candidate.

### R6. Senescence phenotype to target to compound (Track 1 challenge 2 direct)

The user is a geroscience researcher. Phenotype: cellular senescence. Maps from SenNet (88) and SASP Atlas (145), senescence-gene sets from CellAge (37) and SenOmic (44); compound perturbations from sci-Plex (21) and JUMP (80) with predicted direction. Positive controls are the known senolytics dasatinib + quercetin and fisetin, which have direction evidence in published trials (NCT05506488, NCT04063124).

The falsification criterion: the pipeline's predicted direction must match the known outcome for a held-out senolytic class before any novel candidate claim. The validation experiment is a written design, not a wet-lab run: name a cell line from Cellosaurus (156), a senescence readout (SA-beta-gal or SASP markers), and controls. Boundaries: in-silico direction prediction is not clinical translation.

### R7. Drug repurposing research funding classifier (Track 3)

The user is a research policy analyst. Using CORDIS (141) as the single core source, select projects matching repurposing, aging, longevity, and senescence queries within fixed framework programs and time ranges. Two labels: repurposing versus de novo, and aging-biology-direct versus disease-specific. Project texts mentioning aging do not imply studying aging mechanisms.

Output project classification and deduplication counts with target-text evidence; aggregate amounts only after the amount field semantics are verified. Plan to label 50–60 projects, reserve by project, compare keyword rules with classification models, and report multi-label F1, refusal, and misclassification. Falsification: if the model cannot beat the rules, the rules are the deliverable. Boundaries: CORDIS covers EU framework projects only, and Nordic participation is not Nordic funding.

## Data Filtering and Field Verification (updated 2026-09-09)

This round probed the registry and literature APIs live. ClinicalTrials.gov API v2 returned the NCT records listed above on 2026-09-09; PubMed E-utilities and Europe PMC REST returned the PMIDs listed above on the same day. One probe failed and is flagged rather than cited: PEARL (NCT04491648) returned HTTP 404; the sirolimus record cited instead is NCT05237687. TAME, the large metformin aging trial often named in reviews, was not confirmed against a registry record this round; MILES is cited as the verified small trial.

| Resource | Access and licence notes | Supported tasks and boundaries |
| --- | --- | --- |
| DrugAge (40), Geroprotectors.org (32) | HAGR TSV downloads; Geroprotectors.org is JavaScript-only, no bulk download found | Candidate lists and literature annotations; heterogeneous experiments, not outcome labels |
| NIA ITP (87) | Open via Mouse Phenome Database; SOPs and negative results included | Gold-standard mouse lifespan labels for R1, R3, R4 |
| ChEMBL (89) | CC BY-SA 3.0 | Bioactivity features; the standard activity source |
| PubChem (90) | Public domain; PUG-REST | Name-to-CID-to-bioassay resolution |
| ZINC15 (91) | Open | Purchasability checks for R5 |
| DrugCentral (92) | Non-commercial terms; verify before reuse | Indications, off-label use, adverse events |
| BindingDB (93) | Open | Ki, IC50, Kd features for potency ranking |
| LINCS (16), L1000CDS2 (94), clue.io (164) | iLINCS REST is metadata-only; gene-level data via L1000CDS2 JSON API; clue.io needs free academic registration | Signature and reversal features for R1, R3 |
| JUMP (80), sci-Plex (21), RxRx (15) | JUMP CC0; open downloads | Perturbation evidence layers |
| Guide to PHARMACOLOGY (78), EUbOPEN (79) | ODbL with CC BY-SA 4.0 contents; EUbOPEN JavaScript-only | Target-ligand reference; interactive queries only |
| Hetionet (125), PrimeKG (50), Open Targets (8), SPOKE (124) | Hetionet CC0, static 2016; PrimeKG open; SPOKE API only, no bulk | KG ranking inputs; co-occurrence edges, not causal |
| TxGNN (59) | Site returned 503 on 8 Sep; model and data on GitHub | Use only if the GitHub mirror loads |
| openFDA (133), CompTox (134), RxNav/RxNorm (135) | Public domain / open APIs | Safety and identity checks for R5 |
| SenNet (88), SASP Atlas (145), SenOmic (44) | Open; SenOmic files need a Google Drive confirm-token flow | Senescence maps for R6 |
| ClinicalTrials.gov (112), AACT (113), PubMed (138), Europe PMC (114) | Open APIs; AACT needs a free account | Trial and literature evidence for R2 |
| CORDIS (141) | Open CSV/JSON export; CC BY 4.0 for EU-owned content | R7 funding classification |
| Cellosaurus (156), PharmacoDB (158), Boltz (154) | CC BY 4.0 / open API / MIT | Cell-line identity, drug-sensitivity data, structure fallback when AlphaFold 3 (4) is rate-limited |

The same source rules as the other topic documents apply: record URL, licence, version, and access date per source; JavaScript-only items are interactive, not pipelined; restricted items stay out of the weekend plan. UK Biobank (143) and similar restricted cohorts cannot be assumed available.

## Demo Day Evidence Package to Deliver

Choose one main project. Deliverables: data ledger, field and label definitions, retrieval and processing scripts, recalculable metrics or baselines, frozen held-out or reserved sets, failure cases, and a screen recording. R1, R3, R4, R6 report held-out compound-class results; R2 and R7 report manual reserves by study or project; R5 reports manual source checks. A negative result, with the rules and error analysis, is a valid deliverable in Track 1 and often scores higher than an unsupported positive claim.

This advances the Demo Day sections "Issues and Target Users", "Data Sources, Licences and Evidence", "Results and Success Metrics", and "Limitations and Safety", corresponding to the Impact, Technical Execution, and Evidence and Responsible Use criteria in [playbook notes](../playbook.md). Synthetic fixtures are labeled and used only for error handling, not counted as performance.

## Scope of Evidence and Still Missing Data

Still missing, and therefore excluded from claims: human lifespan endpoints (none exist in open data), Nordic-specific repurposing evidence, pharmacokinetic data beyond cell-line screens in PharmacoDB (158), an EMA analogue of openFDA for European adverse events, and confirmation of the TAME trial registration (flagged above). Any demo statement stops at "candidate ranked against held-out labels" or "claim unsupported by the dated evidence ladder". No clinical recommendations, no efficacy claims for humans.
