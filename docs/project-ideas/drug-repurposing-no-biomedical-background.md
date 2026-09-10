# Drug Repurposing Directions: Team-Fit Guide and New Data Resources

## Summary

This document reframes the seven repurposing directions from [drug-repurposing.md](drug-repurposing.md) for a team without biomedical training: each direction is an information-processing task with a narrow, checkable deliverable, not a biology research program. It adds the datasets found online on 2026-09-10 that the existing catalogs ([data-resources.md](../data-resources/data-resources.md) 1–81, [data-resources-extended.md](../data-resources/data-resources-extended.md) 82–164) do not cover, and records which direction each new source supports.

| Direction | Plain-language question | AI difficulty | Biology threshold | Weekend friendliness |
| --- | --- | ---: | ---: | ---: |
| R1 Geroprotector candidate ranking | Which existing drugs deserve an aging experiment? | high | high | high |
| R2 Longevity claim evidence audit | Does the claim have evidence, and how far does it go? | medium | low | high |
| R3 Aging-signature reversal | Which compounds push the aging gene state backward? | high | high | medium |
| R4 Knowledge-graph repurposing | Which drugs connect to aging through many graph paths? | high | medium | medium-high |
| R5 Purchasability and safety triage | Can the candidate be bought, and is it flagged? | low | low | high |
| R6 Senescence phenotype to compound | From senescent cells to a candidate molecule | high | very high | medium |
| R7 Repurposing funding classifier | Which funded projects count as repurposing, which study aging? | medium | low | high |

For a zero-biology team the suggested order is R2 > R1 > R5 > R4 > R7 > R3 > R6, with R1 and R2 the two to seriously consider. This is delivery judgment, not a verified user requirement. New-source probes this round: 15 resources reached HTTP 200, two are paper-verified with no live site, two are unreachable from this network, and one is browser-only.

## Assessment

The hackathon does not ask the team to become biologists. The materials turn longevity into several computation tasks: find candidates (R1), audit claims (R2), find reversal signals (R3), reason over graphs (R4), screen safety (R5), trace mechanism (R6), classify projects (R7). The judges score falsifiability, independent validation, held-out tests, and failure cases, not how convincing the model sounds, per [playbook notes](../playbook.md).

One distinction carries the whole topic: living longer is not the same as a biological marker looking younger. Most published studies measure gene expression, frailty components, or biomarkers, not lifespan, so a marker change cannot be reported as lifespan extension. Every direction in this document inherits that boundary.

## The biology words needed, and nothing more

- drug = an existing compound; target = the protein or gene a drug acts on; phenotype = the observable biological state; lifespan = how long the organism lives.
- positive / negative = whether an experiment showed an effect; a label set with published negative results is worth more than one with only hits.
- signature reversal = a drug whose effect direction opposes the aging gene-expression pattern; a reversed signature in a dish is not a younger organism.
- senolytic = an intervention that selectively removes senescent cells; dasatinib + quercetin (D+Q) and fisetin are the reference cases.
- knowledge-graph edge = co-occurrence or citation, not causation; two drugs appearing in papers with the same gene does not prove the drug changes aging through that gene.

## The seven directions in plain language

Every example below is illustrative unless marked otherwise: scores are invented, and no example states a real finding. Gene names are placeholders; the actual signatures must come from dated sources (MSigDB S8, GenAge 82).

### R1. Geroprotector candidate ranking — the ranking problem

R1 is the most conventional AI project: score a set of existing drugs from activity, target, expression, and past lifespan data, then check the ranking against real mouse lifespan outcomes from NIA ITP (87), holding out one compound class. Most of the work is data cleaning, features, a ranking model, and evaluation.

A worked pipeline for one candidate:

```text
rapamycin
  -> DrugAge (40): literature annotation, lifespan extension reported
  -> ChEMBL (89): known activity against mTOR
  -> L1000CDS2 (94): expression signature direction
  -> NIA ITP (87): real outcome label, lifespan extended = positive
```

The model turns those layers into one score per candidate:

```text
Candidate   Score   ITP outcome (the check)
A           0.87    positive
B           0.79    positive
C           0.74    negative
```

The demo question is not "is A a geroprotector" but "does the score order match the real outcomes, including the negatives". A model that ranks C above B is wrong in a way judges can see. The falsification rule: if the scores do not beat a simple baseline (for example, the count of positive literature annotations) on the held-out compound class, the feature layers add no signal.

How to build it: pull the candidate lists as TSV files from DrugAge (40) and Geroprotectors.org (32); normalize names with RxNav (135) and PubChem (90); join ChEMBL (89) and BindingDB (93) activity counts and L1000CDS2 (94) signature similarities into one feature matrix; train gradient boosting (LightGBM or XGBoost) against ITP (87) labels with a held-out compound class; report the rule baseline (literature annotation count) beside the model, plus precision at k and AUC. Stack: pandas + scikit-learn or LightGBM; an LLM is optional and only for text cleanup, never for the prediction itself.

### R2. Longevity claim evidence audit — the fact-checker

R2 is the easiest to explain to judges: take a claim and walk the evidence ladder. Worked claim: "metformin slows human aging."

```text
cell studies                       found
worm or mouse lifespan             found
human biomarker changes            found
human randomized trials            found (MILES, NCT02432287, n=16)
human lifespan outcome             not found
```

The system then outputs: "no completed human trial measures lifespan; the claim exceeds the evidence." The value is the ladder, not the verdict: every rung links to a dated source, and a claim stops at its highest occupied rung. The demo is an evidence-chain auditor built from PubMed (138), Europe PMC (114), and ClinicalTrials.gov (112), spot-checked against 20–30 manually reviewed claim-evidence pairs.

How to build it: a NotebookLM-like interface plus a scientific fact checker and RAG. The user pastes a claim; the system retrieves sources from PubMed (138), Europe PMC (114), and ClinicalTrials.gov (112); extracts population, intervention, comparison, endpoint, time window, and sample size as structured JSON with quote-level source binding; places each study on the ladder with deterministic rules; and answers support / supports a narrower claim / insufficient information / nothing found. Compare against a keyword baseline on 20–30 manually labeled claim-evidence pairs; report extraction accuracy, key-evidence omissions, unsupported judgments, and refusal rate.

### R3. Aging-signature reversal — the reversal problem

R3 asks which compounds reverse an aging gene signature, queried through L1000CDS2 (94) or clue.io (164). An illustrative signature and reversal:

```text
aging signature (illustrative)
CDKN1A (p21)   up
CDKN2A (p16)   up
LMNB1          down

Drug X
CDKN1A   down
CDKN2A   down
LMNB1    up      -> Drug X reverses the signature
```

The trap is over-reading: a reversed expression profile in a dish is not a younger organism, so the direction must be checked against independent labels (ITP 87, or the known senolytics in R6).

How to build it: read a signature from MSigDB (S8) or GenAge (82) GMT files, POST the gene set to the L1000CDS2 (94) JSON API or SigCom (S9), take back the ranked concordant or reversing signatures, score direction with cosine or weighted concordance, and check the resulting drug order against ITP (87) outcomes. No training is required; the work is API plumbing, gene-set choice, and evaluation. Stack: requests + pandas; if signatures come from Harmonizome (S10), record the source of every gene set.

### R4. Knowledge-graph repurposing — the graph problem

R4 ranks drugs by their paths to aging targets in a knowledge graph (Hetionet 125, PrimeKG 50, Open Targets 8). An illustrative path:

```text
metformin -> AMPK -> mTOR -> cellular aging
```

The ranker scores how many and how strong such paths are:

```text
drug        paths to aging nodes   score
metformin   17                      0.83
drug X       4                      0.31
```

The trap is co-occurrence: metformin and rapamycin both appear in papers with AMPK, which does not mean metformin acts like rapamycin. Graph edges are citations, not causality, so the evaluation must use held-out labels (ITP 87), not path counts alone.

How to build it: load DRKG (S11) triples and its released TransE/RotatE splits, or Hetionet (125); seed aging targets from GenAge (82) and CellAge (37); compute metapath counts as the rule baseline; train TransE or RotatE embeddings or a CompGNN link-prediction head on drug-to-aging-target edges; rank candidates and evaluate on the held-out compound class. Stack: PyTorch with PyG or DGL, networkx for path counting; DRKG ships benchmark code, which shortens the weekend path.

### R5. Purchasability and safety triage — the due-diligence engine

R5 is a deterministic due-diligence pipeline: candidate name to identity, to vendor availability, to indications and adverse-event flags. Almost no machine learning; it produces a reliable product-like demo and catches unbuyable or flagged hits before other directions claim them. An illustrative card:

```text
Drug X

Identity:      PubChem CID resolved
Availability:  supplier found on ZINC (91)
Safety:        FAERS signal flagged (openFDA 133)
Approved use:  diabetes
Decision:      exclude from the R1 shortlist, safety conflict
```

The pipeline is a chain of named checks (RxNav 135, PubChem 90, ZINC 91, openFDA 133, CompTox 134, DrugCentral 92, plus the European side S15–S17). Resolution failures are displayed, never silently dropped; a drug the pipeline cannot identify is an output, not an error to hide.

How to build it: a scripted chain of API calls — RxNav (135) and GSRS (S16) for identity, PubChem PUG-REST (90) for the CID, ZINC15 (91) for vendors, openFDA (133) for labels and FAERS signals, EMA (S15) for the European side, CompTox (134) and DrugCentral (92) for safety and indications — with a rules file defining pass or fail, one JSON schema per candidate, and test fixtures for the failure cases (unknown name, ambiguous match, no vendor, safety flag). No model to train; the deliverable is the pipeline plus its verification report. Stack: requests + pydantic; resolution failures stay visible in the output.

### R6. Senescence to compound — the mechanism chain

R6 follows cellular senescence through its genes, targets, and perturbations to candidate compounds, with D+Q and fisetin as direction controls. The chain, illustratively:

```text
cellular senescence
  -> senescence genes (p16, p21; SenMayo S18)
  -> protein targets
  -> chemical perturbations (sci-Plex 21, JUMP 80)
  -> candidate compounds
```

For example: the pipeline predicts compound Y reduces p21 expression in senescence-relevant cell lines. Before calling Y senolytic-like, the same pipeline must flag the known senolytics D+Q and fisetin with the expected direction; if it does not, the direction logic is rejected. This is the most biomedical direction and the worst fit for someone starting from zero.

How to build it: build the senescence gene set from the SenMayo paper supplementary (S18, since the GitHub repo is missing), optionally adding SenNet (88) and SASP Atlas (145) data; score each candidate's perturbation signature from sci-Plex (21) or JUMP (80) against that set; require D+Q and fisetin to receive the expected direction before any new claim; write the validation experiment design with a named cell line from Cellosaurus (156) and a SA-beta-gal or SASP readout. Stack: scanpy or pandas for matrices, weighted-overlap scoring; the heaviest bioinformatics, worth doing only with the Track 1 challenge 2 template.

### R7. Funding classifier — the text classification problem

R7 classifies funded projects along two axes: repurposing versus de novo, and direct aging biology versus disease-specific. It is NLP classification plus extraction on CORDIS (141), with almost no cell biology required. Worked inputs and labels:

```text
Project 1: "Investigating cellular senescence in aged tissues"
  -> not repurposing, direct aging biology
Project 2: "Novel small molecules for cancer kinase X"
  -> de novo, disease-specific
Project 3: "Reusing approved compounds against age-related fibrosis"
  -> repurposing, aging-adjacent (disease-specific)
```

The demo compares a keyword baseline with an LLM classifier on manually labeled projects, reserved by project ID, and reports precision, recall, F1, and refusals; amounts are aggregated only after the money fields are verified.

How to build it: export CORDIS (141) JSON or CSV for a fixed query set, deduplicate by project ID, then either train a small classifier (TF-IDF + logistic regression) or use an LLM few-shot prompt with structured output for the two labels; keep keyword rules as the baseline; manually label 50–60 projects reserved by project ID; report multi-label precision, recall, F1, and refusals; aggregate amounts only after the money fields are verified. Stack: sentence-transformers or OpenAI embeddings + scikit-learn; the keyword rules double as the interpretable fallback.

## New data resources found online, verified 2026-09-10

Local IDs S1–S20; catalog resources keep their numbers in parentheses. Status is what this round's probes returned; a reachable page does not mean downloaded, licensed, or analyzed data.

| ID | Resource | Status 2026-09-10 | Access and licence notes | Supports |
| --- | --- | --- | --- | --- |
| S1 | Caenorhabditis Intervention Testing Program (CITP) | Paper-verified; program website not confirmed this round | Multi-site worm lifespan tests with negative results published; cite [PMID 42694712](https://pubmed.ncbi.nlm.nih.gov/42694712/), [DOI 10.17912/micropub.biology.002343](https://doi.org/10.17912/micropub.biology.002343) | R1: worm-level labels alongside NIA ITP (87) |
| S2 | [Mouse Phenome Database lifespan surveys](https://phenome.jax.org/) | HTTP 200 | Open; lifespan across inbred strains; cite per survey | R1: strain-level mouse lifespan background |
| S3 | [DepMap PRISM Repurposing Primary Screen](https://depmap.org/portal/) | HTTP 200 (JavaScript app) | Primary drug-sensitivity screen across cell lines; verify file-level terms before reuse | R1: sensitivity features |
| S4 | [DrugRepurposingHub](https://repo-hub.broadinstitute.org/repurposing) | HTTP 200 (SSL error to scripted clients; fine in a browser) | Broad-curated repurposing compound annotations | R1: candidate annotations |
| S5 | repoDB | DNS unreachable both probes | Treat as unavailable; use the paper instead (Brown & Patel, Sci Data 2017) | R1, R4: replaced by S11 and catalog KGs |
| S6 | [PROSPERO](https://www.crd.york.ac.uk/prospero/) | HTTP 200 | Systematic-review registrations; check reuse terms | R2: planned-review evidence for the ladder |
| S7 | [Epistemonikos](https://www.epistemonikos.org/en) | HTTP 403 to scripts, fine in a browser | Evidence-synthesis database; browser-only this round | R2: systematic-review layer |
| S8 | [MSigDB](https://www.gsea-msigdb.org/gsea/msigdb/) | HTTP 200 | Free with registration; redistribution terms to check | R3: Hallmark and aging gene sets for signatures |
| S9 | [SigCom LINCS](https://maayanlab.cloud/sigcom-lincs/) | HTTP 200 | LINCS signature search API beyond L1000CDS2 (94) | R3: signature query layer |
| S10 | [Harmonizome](https://maayanlab.cloud/Harmonizome/) | HTTP 200 | Gene-set aggregator | R3: candidate signature assembly |
| S11 | [DRKG](https://github.com/gnn4dr/DRKG) | HTTP 200 (repo moved from gnshealth; 705 stars) | Drug Repurposing Knowledge Graph with published embedding benchmarks; check repo licence | R4: the standard repurposing KG benchmark |
| S12 | [OpenBioLink](https://github.com/OpenBioLink/OpenBioLink) | HTTP 200 | Open KG benchmark for drug-discovery tasks; check repo licence | R4: evaluation benchmark |
| S13 | [BioSNAP ChCh-Miner](https://snap.stanford.edu/biodata/datasets/10001/10001-ChCh-Miner.html) | HTTP 200 via index | Drug-drug network from published studies; check per-dataset terms | R4: drug-drug edges |
| S14 | [Therapeutic Target Database](https://db.idrblab.net/ttd/) | HTTP 200 | Target reference; check academic terms | R4, R6: target lookup |
| S15 | [EMA medicine data](https://www.ema.europa.eu/en/medicines/download-medicine-data) | HTTP 200 | European public assessment reports; open with attribution | R5: European regulatory side of the triage |
| S16 | [GSRS API](https://gsrs.ncats.nih.gov/api/v1/substances?size=1) | HTTP 200, live API response | Global substance identity resolution | R5: identity layer alongside RxNorm (135) |
| S17 | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/) | HTTP 200 | Structured FDA drug labels | R5: label and indication checks |
| S18 | SenMayo gene set | Original GitHub repo returns 404; use the paper | [PMID 35974106](https://pubmed.ncbi.nlm.nih.gov/35974106/) (Nat Commun 2022) plus the 2026 evaluation toolkit [PMID 42266575](https://pubmed.ncbi.nlm.nih.gov/42266575/) | R6: curated senescence gene panel |
| S19 | [UKRI Gateway to Research](https://gtr.ukri.org/) | HTTP 200 | UK research funding with an API; Open Government Licence | R7: UK funding slice alongside CORDIS (141) |
| S20 | DrugComb | Timed out twice from this network | Combination-screen database; retry from the venue network or skip | R1, R4: combination angle, optional |

## What changes per direction with the new data

R1 gains a second label source (S1 worm ITP, next to mouse ITP 87), strain-level lifespan background (S2), sensitivity features (S3), and curated annotations (S4). What still does not exist: human outcome labels. S5 (repoDB) and S20 (DrugComb) are unavailable this round and must not be written into plans.

R2 gains the systematic-review layer: PROSPERO (S6) catches registered-but-unfinished reviews, Epistemonikos (S7) aggregates synthesis evidence. Neither replaces reading the primary papers; they are ladder rungs between registry and RCT.

R3 gains signature assembly (S8, S10) and a second LINCS query layer (S9). The direction of a reversal still needs the ITP (87) concordance check; none of the new sources provides organism-level outcomes.

R4 gains the canonical benchmark (S11 DRKG with published TransE/RotatE/CompGNN splits), a second benchmark (S12), drug-drug edges (S13), and target lookup (S14). Benchmarks make R4 easier to demo but they are co-occurrence; the held-out ITP evaluation from [drug-repurposing.md](drug-repurposing.md) remains the falsification layer.

R5 gains the European regulatory side (S15 EMA), substance identity (S16 GSRS), and structured labels (S17 DailyMed), so the triage card now has both FDA and EMA layers. Resolution failures must still be displayed, not dropped.

R6 gains a curated senescence gene panel (S18 SenMayo) with a 2026 toolkit for evaluating gene sets. The original GitHub repo is missing, so the gene list comes from the paper's supplementary; record that provenance when using it.

R7 gains a UK funding slice (S19). Amounts are only aggregated after the field semantics are verified, and UK data answers the UK question, not a Nordic one.

## Data filtering and field verification

Probe record, 2026-09-10: 15 of 20 candidates returned HTTP 200. CITP (S1) and SenMayo (S18) were verified through publications because their sites are unconfirmed or missing. repoDB (S5) failed DNS twice and is marked unavailable. DrugComb (S20) timed out twice from this network and is marked unverified, not dead. Epistemonikos (S7) blocks scripted clients but loads in a browser. DRKG moved from gnshealth to gnn4dr; old links now 404.

For every source actually used, record URL, version or release date, access date, licence, fields, and redistribution limits, per the checklist in [AGENTS.md](../../AGENTS.md). None of the S resources has been downloaded yet; none of the statements above is a trained model or a measured result.

## Demo Day evidence package to deliver

One main direction, plus its deliverables: data ledger, field and label definitions, retrieval and processing scripts, recalculable metrics or baselines, frozen held-out or reserved sets, failure cases, and a screen recording. R1, R3, R4, R6 report held-out results; R2, R7 report manual reserves; R5 reports manual source checks. A negative result with rules and error analysis is a valid Track 1 deliverable. This advances the Demo Day sections "Issues and Target Users", "Data Sources, Licences and Evidence", "Results and Success Metrics", and "Limitations and Safety", per [playbook notes](../playbook.md).

## Scope of evidence and still missing data

Still missing: human lifespan endpoints, Nordic-specific repurposing evidence, pharmacokinetic data beyond cell-line screens, and working access to repoDB and DrugComb. No statement in the demo exceeds "candidate ranked against held-out labels" or "claim unsupported by the dated evidence ladder". No clinical recommendations, no human efficacy claims.

The selection order R2 > R1 > R5 > R4 > R7 > R3 > R6 is a team-fit judgment for a zero-biology background, not a ranking of scientific value; R1 and R6 are the most scientifically interesting, and R2 the most demoable.
