### 1 · Longevity Biology × AI

Build tools around ageing clocks, biomarker inference, target triage, AI-supported drug repurposing, in-silico trials or other defensible applications of AI to the biology of ageing.

**Best suited to:** ML engineers, bioinformaticians, computational biologists, translational researchers and biomedical builders. # Challenges - Track 1

<aside>
🧬

**Track 1 · Longevity Biology × AI — scientific challenges**

A flagship agentic challenge — **Build a Longevity AI Scientist** — plus five focused scientific challenges, each with a defined question, a required output and a suggested data stack. Choose one, or use them as a template for a question of your own.

</aside>

## 1 · Build a Longevity AI Scientist ⭐

*Question → evidence → experiment, end to end — the flagship challenge*

**The question.** Ageing research is bottlenecked by human bandwidth, not ideas. Can your team build an **AI scientist** — an agent, or a small team of agents — that takes a real longevity question and moves it forward without a human steering each step?

**Build:** an agent that forms a hypothesis, gathers and weighs the evidence, calls biological tools, runs an in-silico experiment and returns a cited, defensible answer. Example shapes:

- **Target triage agent** — mine literature and Open Targets, rank candidate targets by genetic evidence, sketch a binder with an open structure-prediction tool (e.g. Boltz) and write a cited target-validation memo.
- **Autonomous ageing-clock builder** — pull methylation or multi-omic data, train a clock, benchmark it against DunedinPACE and report honestly on where it fails.
- **Literature-to-hypothesis agent** — read a corpus of ageing papers and propose novel, testable hypotheses, each traceable to its sources.
- **In-silico intervention tester** — simulate a candidate intervention on a pathway and summarise the predicted mechanism and confidence.
- **Grounded science communicator** — turn a dense longevity finding into a legible, fully-cited brief — and a voice briefing a clinician or policymaker could actually listen to.

**Required output:**

1. A working agent that plans, retrieves, calls tools and revises without hand-holding
2. At least one real biological or data tool call inside the loop — not just text summarisation
3. A cited final report: what the evidence supports, what it doesn't, and the next experiment to run
4. Stated uncertainty and failure modes
5. A demo a judge could re-run, plus a recorded fallback

**The partner stack — provided to every team:**

- **Anthropic** — the agent brain: Claude models, Claude Agent SDK and MCP for reasoning, planning, tool-calling and grounded writing.
- **Nebius** — GPU compute and model hosting; Token Factory credits via QR at the venue.
- **Tavily** — live web retrieval over papers, trials and news; 8,000 credits per participant.
- **Amass** — scientific memory across literature, trials, patents and biological data, via app, API and MCP; $500 credits per team.
- **ElevenLabs** — turn findings into listenable, cited voice briefings; 1 month Creator per participant.
- **Lovable** — a demo-ready front-end, fast; Pro Plan 1 with 100 credits.
- **Open data** — Open Targets and the playbook dataset library for target–disease evidence, ageing clocks and public omics.

A **starter scaffold** (Claude + Nebius + Tavily + one memory layer + one bio tool) is provided on day one, so the 36 hours go into the science, not the plumbing.

**Evaluation:** scored on the hackathon's six weighted dimensions. For this challenge the bar is a real question moved forward with genuine autonomy — every claim traceable to a source, limits stated honestly, and an output a clinician or investor can understand in one pass. A rigorous answer to a narrow question beats a vague tour of a big one.

**What proves it works:** at least 95% of factual claims in the final report carry a working citation; the full run re-executes from a clean checkout in under 30 minutes; and judges can switch one tool off and watch the answer change — proof the tools are inside the loop, not decoration.

## 2 · Find the control point

*Ageing → mechanism*

**The question.** Given an ageing-associated molecular state, identify the process most plausibly limiting restoration of a younger, homeostatic state.

**Required output:**

1. Ranked mechanistic hypotheses
2. Evidence across tissues and cell types
3. Stated uncertainty
4. One experiment that could falsify the top hypothesis

**What proves it works:** the top-ranked hypothesis is supported by evidence in a held-out tissue or cell type the team never used, and a mentor scientist judges the falsification experiment genuinely executable.

**Suggested open-data stack:**

- **Tabula Muris Senis** (or other open ageing atlases) — age-associated molecular states
- **Human Protein Atlas (HPA)** — tissue, cell-type and subcellular localisation as a reality filter

## 3 · From phenotype to perturbation

*Mechanism → intervention*

**The question.** Starting from an ageing-associated phenotype or mechanism, identify an actionable target and a credible chemical perturbation predicted to move the system towards a healthier state.

**Required output:**

1. Target and perturbation, with predicted direction of effect
2. Independent evidence layers
3. Negative and control strategy
4. A testable validation experiment

**What proves it works:** the pipeline recovers at least two known target–compound pairs from a held-out set, with the predicted direction of effect matching the published literature.

**Suggested open-data stack:**

- **Human Protein Atlas (HPA)** — target expression and localisation
- **Broad Cell Painting / JUMP** — chemical and genetic phenotypic profiles
- **EUbOPEN** — high-quality chemical probes and matched inactive controls
- **IUPHAR/BPS Guide to Pharmacology** — curated target–ligand pharmacology

## 4 · What should we do next?

*Evidence → experiment*

**The question.** Given incomplete and potentially conflicting evidence around an ageing mechanism or intervention, choose the single next experiment with the highest expected information gain.

**Required output:**

1. Competing hypotheses
2. The proposed experiment
3. Predicted outcomes under each hypothesis
4. A decision rule — how each result would change target or intervention prioritisation

**Suggested open-data stack:**

- A curated multi-source package assembled from the resources above
- One evidence layer is deliberately withheld — part of the task is identifying what is missing, not pretending the available data are sufficient

**What proves it works:** the decision rule is written down before the withheld layer is revealed — and when it is revealed, the team shows whether the chosen experiment changes, and defends the outcome against a mentor panel.

## 5 · Curate the world's ageing data

*Messy studies → harmonised, provenance-tagged metadata*

**The question.** Single-cell ageing studies are scattered across public repositories with inconsistent sample metadata — replication and meta-analysis stall because nobody can tell which samples are comparable. Can your agents turn a messy study into clean, harmonised, fully-provenanced metadata?

**Build:** a supervisor-orchestrated multi-agent pipeline that, given a paper or a GEO accession, locates the linked files, extracts per-sample metadata (donor, age, sex, tissue, assay, treatment), harmonises values to standard ontologies, maps samples to donors, and issues a human-readable QA report.

**Required output:**

1. A harmonised sample–donor table for at least one well-structured and one deliberately messy ageing study
2. Per-field confidence scores and provenance pointers (source document and location)
3. A QA report that flags ambiguities for human review rather than guessing silently
4. Accuracy measured against a curator-reviewed reference set

**Possible sources:**

- **GEO**, **CZ CELLxGENE Census**, **Human Cell Atlas** and **Tabula Sapiens v2** — all in the playbook dataset library, with plenty of ageing scRNA-seq studies to practise on
- Open ontologies (MONDO, EFO, Cell Ontology, UBERON) via the free OLS API
- **Claude (Anthropic) Agent SDK** for orchestration · **Amass** for study context

**Evaluation:** extraction precision and recall against the reference set, ontology-mapping accuracy and provenance completeness — with human QA time saved as the headline metric. A strong bar from previous editions: ≥90% precision on a clean study, ≥80% on a messy one, and ≥98% of fields carrying a source pointer.

## 6 · Synthetic data for ageing clocks

*Scarce methylation data → validated synthetic cohorts*

**The question.** Ageing-clock research is throttled by data access: real methylation cohorts can take months of applications. Can you generate synthetic or augmented methylation data realistic enough that a clock trained on it holds up against one trained on real data alone?

**Build:** a pipeline that synthesises or augments DNA-methylation cohorts, ships a validation card (distributions, correlations, known age associations), and reports honestly where synthetic data helps and where it breaks.

**Required output:**

1. A synthetic or augmented methylation cohort with a validation card
2. The key experiment: a clock trained on augmented data vs the same clock trained on the original data, both scored on held-out real samples
3. Failure modes and privacy caveats, stated plainly

**Possible sources:**

- **DNA methylation datasets via Biolearn** — 40+ harmonised GEO datasets and 20+ reference clocks, including DunedinPACE and AltumAge — and **ClockBase**, both in the playbook dataset library
- **Nebius** GPU credits for the training runs

**Evaluation:** the augmented-data clock matches or beats the baseline on held-out real data — and the team can explain why, or why not.

## Why these resources are practical

| Resource | What it gives you | Access and licence |
| --- | --- | --- |
| Human Protein Atlas | Downloadable tissue, single-cell, cell-line and subcellular data | CC BY 4.0; check embedded third-party data |
| Cell Painting / JUMP | Images, features and metadata downloadable separately; public AWS, no account required | CC0 |
| EUbOPEN | Peer-reviewed chemical probes — potency, selectivity, cellular target engagement and, where feasible, matched inactive controls; chemogenomic set downloadable as CSV | Open download |
| Guide to Pharmacology | Downloadable target, ligand and interaction tables, plus REST access | ODbL; contents CC BY-SA 4.0 |

## How these challenges are run

- **Pre-curated data.** IDs, mappings and processed feature matrices are provided; raw-data links are optional extensions.
- **Held-out evaluation.** A tissue, perturbation, compound class or evidence layer is held back for final evaluation — build for generalisation, not just the visible data.
- **Uncertainty required.** Submissions must state uncertainty and a falsification criterion.
- **Validity over polish.** Biological validity and generalisation score higher than UI polish.
- **The flagship runs on the partner stack.** Challenge 1 teams build with Anthropic, Nebius, Tavily, Amass, ElevenLabs and Lovable — access and credit details are in the Tooling Partners section and the Friday technical briefing.

<aside>
🎯

**Choosing between them?**

Pick the question your team can answer with evidence over the weekend. A focused, falsifiable result beats a broad survey — mentors can help you scope during Friday's track Q&A and Saturday's rotations.

</aside> ### 2 · AI Infrastructure — Nebius

Build a performant, scalable longevity-compute solution using the Nebius infrastructure stack. The challenge statement, access route and technical documentation will be shared with participants before the event.

**Best suited to:** ML infrastructure, systems and platform engineers, AI researchers and developer-tool builders. # Track 2: AI Infrastructure

## Challenge: "From Signal to Intervention" — Serverless Longevity Compute Pipelines

<aside>
🎯

**One-line pitch:** Build a working tool that turns a biological or behavioral signal into an actionable longevity insight, running entirely on Nebius Serverless AI (optionally paired with Token Factory for the reasoning/explanation layer) — judged on the use case as much as the infrastructure.

</aside>

### What teams actually build

Not a single API wrapping one model. A pipeline with at least two real stages, e.g.:

1. **Compute stage (Serverless Jobs):** something GPU-heavy and batchable — virtual screening/docking against an aging-relevant target, an omics analysis pipeline (single-cell, methylation, proteomics), a biological-age model run across a cohort, or a simulation sweep.
2. **Serving/decision stage (Serverless Endpoints):** the output turned into something a user or clinician can query live — a ranked shortlist, a risk score with rationale, a match/no-match decision.
3. **Optional reasoning layer (Token Factory):** an LLM that interprets stage 2's output into plain-language explanation, hypothesis generation, or next-step recommendations.

<aside>
💡

**Why "GPU-relevant" is called out explicitly:** Track 2 is scored on "best use of the Nebius GPU stack." A pipeline whose entire compute stage is a linear formula (no GPU needed at any point) still runs on Serverless, but it doesn't showcase the thing this track — and the case-study slot — actually exists to demonstrate. Teams should be nudged toward a use case where GPU compute is doing real work, not toward proving GPU where a spreadsheet would do.

</aside>

---

## "Biological Age & Explanation"

Ingest a batch of omics records, compute biological-age estimates at scale via Serverless Jobs, then expose a Serverless Endpoint that takes a new individual's data and returns their biological age plus which biomarkers are driving deviation from chronological age. An optional Token Factory-backed reasoning layer turns the flagged biomarkers into a personalized, plain-language explanatory narrative instead of a raw number.

Model choice matters here, not just the architecture. The obvious shortcut — a published linear formula like PhenoAge (nine blood values times nine fixed weights) — needs zero GPU and can run anywhere, which undercuts a track whose whole scoring rubric is "best use of the Nebius GPU stack." The recommended default is a deep-learning epigenetic clock, specifically AltumAge (a neural network trained on ~20K DNA methylation sites, published in npj Aging) served through pyaging, an open-source, PyTorch-backed, GPU-optimized library that already implements AltumAge alongside dozens of other clocks (including PhenoAge) behind one consistent API. That gives teams a real GPU inference workload — batch-scoring a cohort through a neural net on a Job, then serving single-sample predictions on a GPU Endpoint — rather than a formula that happens to be deployed on a GPU box.

Since pyaging also ships PhenoAge in the same library, a nice (optional) demo beat is to compute both on the same request and show the contrast live: the free/instant CPU formula next to the GPU-backed deep clock, with their respective latency and cost. That turns the GPU-vs-CPU tradeoff into part of the story instead of hiding it.

<aside>
⚠️

**Naming/framing note:** avoid "triage" or "risk" language in the public brief — keep the deliverable framed as nonclinical biological-age estimation and explanation (research/wellness context), not diagnosis or clinical decision support. This matches both our own no-medical-advice stance and the safety scope Nebius already publishes on the closest existing reference architecture (see below).

</aside>

**Use case:** closer to a real digital-health explainability tool than a benchmark demo — the batch stage does the heavy lifting, the endpoint makes it usable by an end user in real time, and the reasoning layer is what makes the number legible rather than clinically actionable.

### Starter kit: reuse bionemo-agent

Recently shipped life-science/bionemo-agent in the serverless cookbook already demonstrates the exact infra combo the track requires (Serverless Endpoints + Jobs, with Token Factory as an add-on).

**What it already gives teams, reusable as-is:**

- A ReAct agent (NVIDIA NeMo Agent Toolkit) that routes a request to the right backend skill (explanation layer of the challenge), and it's already wired to Token Factory (GLM-5 by default).
- The 3 deployment paths (full stack, agent-only endpoint, Serverless Job smoke check) and all the nebius ai endpoint / nebius ai job scripting.
- 2 of its existing skills carry over directly: chat and literature_retrieval.

**What we need to add:**

- None of its current skills compute a biological age or aging-clock estimate — we need omics-to-age tools. We need to add a new skill, biological_age, following the same self-hosted-bionemo/ service pattern: a GPU-backed deep-learning clock (AltumAge via the pyaging library) exposed at a new route like /v1/aging/biological-age, registered in the agent's skill-routing config.
- The Job path needs repurposing: instead of a one-shot smoke check, it should batch-score a public methylation cohort dataset through the GPU clock to build the reference distribution the live endpoint compares new individuals against.
- structure_prediction and molecular_dynamics are irrelevant to this use case and should be left out of what teams are pointed to, to avoid scope confusion.

<aside>
✅

**TODO:** fork bionemo-agent, strip the protein/structure skills from the participant-facing starter, and add a stub biological_age skill with a placeholder model and a sample public dataset wired into the Job path.

</aside>

---

## "Longevity × Sleep"

Turn a sleep signal into an actionable longevity insight, running entirely on Nebius Serverless AI – with Token Factory powering the layer that talks to the user.

### About Lezonder

This challenge was shaped together with Evgeniy Antoshkin, creator of Lezonder, an iOS app that turns consumer sleep-tracker data from Oura, Apple Health, WHOOP and other supported devices into a gamified experience designed to motivate better sleep. Lezonder contributed its hands-on experience working with real-world wearable sleep data, as well as the synthetic longitudinal dataset included in this challenge. The dataset reproduces aggregate statistical patterns seen in real tracker data without containing any Lezonder user records, giving teams a way to experiment with personal baselines, regularity, recovery and longer-term sleep patterns that are difficult to study with the short Sleep-EDF histories alone.

https://www.lezonder.com/ · App Store

### Why sleep

A couple of things from research and hands-on experience building in this space:

- Sleep architecture changes measurably with age. Slow-wave (deep) sleep tends to decline across adulthood, while sleep becomes more fragmented and less efficient. This makes sleep an interesting signal to explore in the context of aging and health span.
- Longitudinal patterns may matter as much as individual nights. In a prospective study of more than 60,000 people, sleep regularity was a stronger predictor of all-cause mortality risk than sleep duration. That raises an interesting question: what can weeks or months of sleep data tell us that one night cannot?

### Angles worth exploring

- **Sleep age:** Can you estimate a person's chronological age from sleep architecture? Which sleep features carry the strongest age-related signal, and what can the gap between predicted and actual age tell us?
- **Sleep resilience:** Can longitudinal sleep data distinguish a random bad night from a meaningful change in someone's baseline? How quickly does a person's sleep return to baseline after disruption?
- **Sleep regularity:** What patterns of bedtime, wake time, duration and sleep architecture characterize stable vs. irregular sleep over weeks or months?
- **Personalized sleep insights:** Instead of comparing everyone to the population average, can you learn an individual's baseline and identify which changes are meaningful specifically for them?
- Or bring your own – anything that connects sleep data to healthspan, aging or long-term health.

### Where Token Factory fits

The compute stages produce numbers; an LLM layer makes them friendly. For example:

- Turn weeks of sleep metrics into actionable suggestions grounded strictly in the available data.
- "Explain my night": let the user ask what changed relative to their own baseline and get a plain-language answer.
- Monthly summaries that translate raw stats into readable trends: what changed, what stayed stable, and what may be worth paying attention to.
- Explain model outputs such as predicted sleep age, unusual deviations or changes in sleep regularity without turning them into medical diagnoses.

### Data

- **Open dataset to start with:** Sleep-EDF Expanded (PhysioNet) – polysomnography recordings with sleep stage annotations.
- **Lezonder-prepared challenge dataset:** a compact tabular dataset derived primarily from the Sleep Cassette subset of Sleep-EDF, which contains recordings from healthy adults aged 25-101. Teams can start from per-recording features such as total sleep time, slow-wave/deep sleep, REM sleep, an optional sleep-efficiency proxy, age and sex, without processing raw PSG files. Further details can be found in the README_Lezonder.md.
- **Synthetic longitudinal extension:** a fully synthetic dataset with multiple weeks or months of sleep history per virtual participant, designed for experimenting with trends, regularity, personal baselines and recovery patterns. No real Lezonder user records will be used. It is intended for prototyping models and product experiences, not for validating biological or clinical claims. Further details can be found in the README_Lezonder.md.
- **Consumer wearables** (Oura Ring, Apple Watch, Whoop, etc.) don't capture the same raw signals, but they provide related sleep metrics and derived sleep-stage estimates – teams can find public sample exports online or simulate their own.

### Pretrained models you can start from

If you want to work with raw PSG rather than the prepared tabular dataset, these open tools and pretrained models can give you a head start:

- **YASA** – easiest baseline: EDF files in, hypnograms out, one pip install.
- **PhysioEx** – Apache-2.0 weights for classic architectures, some trained directly on Sleep-EDF.
- **SleepFM** – PSG foundation model with disease-risk prediction, a natural fit for longevity (weights are non-commercial, CC BY-NC 4.0).

### What a good submission looks like

- A working pipeline with at least two real stages (see the Track 2 pipeline structure above) that takes sleep data in and produces an insight a person could actually understand or act on.
- Strong submissions should go beyond describing a single night: look for patterns across people, across time, or relative to an individual's own baseline.
- The goal is not to make medical claims, but to discover and communicate potentially useful signals connecting sleep with aging and health span.
- Judging criteria are the same as for the "Biological Age & Explanation" Challenge. ### 3 · Communication, Trust & Policy

Build products, tools or campaigns that make longevity science understandable, credible and actionable while addressing misinformation, institutional trust and responsible adoption.

**Best suited to:** science communicators, UX designers, policy specialists, behavioural scientists and product builders. # Challenges - Track 3

<aside>
🏛️

**Track 3 · Communication, Trust & Policy — proposed challenges**

Five challenges spanning political intelligence, public funding, evidence verification, national research strategy and the shape of the longevity R&D landscape itself. Choose one, or use them as a template for a question of your own.

</aside>

## 1 · Map the politics of longevity

*Political activity → global map*

**The question.** Where are governments and politicians seriously engaging with longevity, healthy ageing or the biology of ageing?

**Build:** An AI research agent that searches public sources and produces a cited, time-stamped global map of political activity.

**Required output:**

1. Interactive map with country- or state-level findings
2. Classification of each finding: policy, legislation, funding, strategy or political statement
3. Source and date for every finding
4. Confidence and coverage score, including **“nothing reliable found”**

**Evaluation:** Accuracy on a small human-verified benchmark matters more than map coverage. The bar: ≥90% of sampled findings verified correct by a human reviewer, and every finding carrying a dated source — including the honest "nothing reliable found" results.

## 2 · Follow the money

*Public grants → ageing-biology funding*

**The question.** How much public research funding actually targets the biology of ageing rather than individual age-related diseases?

**Build:** An AI classifier that analyses grant databases in Sweden, Europe or beyond.

**Required output:**

1. Funding totals and the share classified as ageing biology
2. Categories such as fundamental biology, interventions, age-related disease and elderly care
3. Interactive breakdown by country, funder and field
4. Confidence, ambiguous cases and a reproducible classification methodology

**Possible data:**

- **Swecris — Swedish research funding database.** Grants from Swedish governmental and private research funders; the API is public and currently has a public test token. Swecris API + documentation · Swagger/API endpoint
- **CORDIS — EU-funded research projects.** Horizon Europe project data downloadable in CSV, JSON, XML and Excel, including projects, organisations, deliverables and publications. CORDIS project search · Horizon Europe open dataset/downloads
- **NIH RePORTER — US research grants.** Use for international comparison; the API exposes project titles, abstracts, award amounts, organisations, investigators, dates and funding mechanisms. NIH RePORTER API · NIH RePORTER website

**Evaluation:** Test the classifier against a small manually labelled grant set. The bar: ≥85% agreement with human labels on the labelled set, with ambiguous cases explicitly flagged rather than forced.

## 3 · Audit a longevity claim

*Scientific claim → evidence chain*

**The question.** How strong is the evidence behind a claim such as *“X slows ageing”*?

**Build:** An evidence agent that decomposes the claim, searches the scientific literature and reconstructs the evidence chain.

**Required output:**

1. Evidence ladder: cells → animals → observational humans → trials and meta-analyses
2. Endpoint distinction: biomarker, healthspan, disease outcome or lifespan
3. Supporting and contradicting studies with citations
4. Evidence grade, uncertainty and key missing evidence

**Possible sources:**

- **PubMed — biomedical literature.** Primary source for this challenge; available through search, bulk-download files and NCBI's E-utilities API. PubMed · Data downloads/API information · NCBI E-utilities API documentation
- **ClinicalTrials.gov — registered clinical trials.** Distinguishes promising preclinical evidence from actual human testing; modern REST API and CSV downloads, refreshed on weekdays. ClinicalTrials.gov · ClinicalTrials.gov API
- **Examine — curated intervention evidence.** Supplementary source; systematically collects and grades randomised-trial evidence, but the main efficacy database is **not an open dataset** — the commercial API/MCP currently focuses on supplement interactions, and efficacy data require separate access/licensing. Examine · Examine Connect API/MCP
- Primary literature

**Evaluation:** Traceability and correct interpretation matter more than producing a confident verdict. The bar: ≥95% of factual claims carry a working citation, and an independent reviewer can reconstruct the verdict from the cited sources alone.

## 4 · Design the ageing moonshot

*Public ambition → research portfolio*

**The question.** If a government committed €10 billion to dramatically accelerate progress against biological ageing, how should it actually spend it?

**Build:** A multi-agent system that designs, critiques and revises a 10-year research and translation portfolio.

**Required output:**

1. Budget allocation across science, biomarkers, interventions, trials, infrastructure and translation
2. Specific programmes, milestones and success metrics
3. Explicit assumptions and major bottlenecks
4. Red-team critique followed by a revised portfolio
5. A short, publishable **Ageing Moonshot** white paper generated from the final plan

**Stretch:** Let users change the budget or risk tolerance and watch the portfolio adapt.

**Evaluation:** the red-team critique surfaces at least three substantive weaknesses and the revised portfolio demonstrably addresses each one — and the final white paper is generated from the plan, not hand-written.

## 5 · Map the longevity R&D landscape

*Open problems → capabilities → infrastructure gaps*

**The question.** Reviews have catalogued 100+ open problems in ageing science, but nobody systematically tracks which capabilities, datasets and tools exist to attack them. Labs duplicate each other's work and keystone gaps go unfunded. Can you build the map?

**Build:** a multi-agent system that classifies open ageing problems, extracts the capabilities each one requires, maps the existing resources (datasets, models, cohorts, tools) and scores the gaps by cost, number of blocked problems and duplication.

**Required output:**

1. A structured problem → capability → resource map for a meaningful slice of the field
2. A ranked list of "keystone" gaps — the missing capabilities blocking the most research
3. Duplication clusters: where multiple groups are building the same thing
4. Every mapping traceable to a dated source

**Possible sources:**

- Start inside the playbook dataset library itself: the HAGR family (**DrugAge**, **AnAge**, **CellAge**, **Longevity Map**, **Geroprotectors.org**), **HALD** (a text-mined knowledge graph of 300k+ ageing papers) and **Open Targets**
- PubMed, ClinicalTrials.gov and grant databases (Swecris, CORDIS, NIH RePORTER) retrieved via **Tavily** or **Amass**
- **Claude (Anthropic)** for the multi-agent reasoning · **Lovable** for an explorable map

**Evaluation:** extraction accuracy on a human-checked slice beats map size; the keystone-gap list should be one a funder would recognise as real.

## How these challenges are run

- **Sources must be traceable.** Every material finding, classification and claim should link back to a dated primary or authoritative source.
- **Uncertainty is part of the output.** Teams should distinguish confirmed evidence, ambiguous cases, missing coverage and unsupported claims.
- **Benchmark before scaling.** Validate the system against a small human-reviewed sample before optimising for breadth.
- **Data availability.** Challenges 1 and 4 deliberately name no fixed dataset: Challenge 1 relies on web-accessible government and political sources, while Challenge 4 is primarily an AI research-and-reasoning task. The cleanest ready-to-use programmatic stack is **Swecris + CORDIS** for Challenge 2 and **PubMed + ClinicalTrials.gov** for Challenge 3 — both accessible without a paid service.
- **Accuracy over polish.** Correct interpretation, reproducibility and honest limits score higher than a comprehensive-looking interface.

<aside>
🎯

**Choosing between them?**

Pick the question your team can answer with credible evidence over the weekend. A narrow, well-audited result beats a broad but unreliable system — mentors can help you scope during Friday's track Q&A and Saturday's rotations.

</aside> ### 4 · Healthspan & Clinical Translation

Build clinician-facing tools, preventive-health workflows and credible pathways from data or research to real-world healthspan applications.

**Best suited to:** clinicians, healthtech builders, clinical-data specialists, researchers and product teams. # Challenges - Track 4

<aside>
🩺

**Track 4 · Healthspan & Clinical Translation — challenges**

Six challenges that turn data and research into tools a clinician, client or health-seeker could actually use. Each has a defined question, a required output and open data to start from. Choose one, or use them as a template for a workflow of your own.

</aside>

## 1 · The pre-consultation brief

*Scattered intake → clinician-ready brief*

**The question.** Longevity clinicians lose hours reconstructing a new client's story. Can you turn scattered inputs — intake forms, prior lab reports, wearable exports, stated goals — into a brief a clinician could act on in five minutes?

**Build:** an agent that ingests multi-format intake, structures the history, flags missing information, and drafts a cited, clinician-facing summary with priorities for the first consultation — plus a plain-language version (optionally voiced) for the client.

**Required output:**

1. Structured intake summary: history, medications, wearable patterns, goals
2. Missing-information and red-flag list — escalated to a clinician, never auto-answered
3. A one-page cited brief for the clinician
4. A clinician review step — accept, edit or reject each section before the brief is finalised, with corrections logged
5. A plain-language client summary, with an optional voice read-out

**Possible sources:**

- Synthetic or self-generated intake data only — never real patient records
- Published reference ranges and preventive-health guidelines from public sources
- **Amass** for evidence grounding · **Claude (Anthropic)** for the agent loop · **Lovable** for the intake front-end · **ElevenLabs** for the voice summary

**Evaluation:** clinician time saved and zero unsupported claims matter more than breadth of ingestion. The bar: the brief assembles in under 10 minutes from raw intake, and a clinician reviewer finds nothing they would need to delete.

## 2 · Explain my bloodwork

*Lab panel → understanding, not diagnosis*

**The question.** A client receives a 40-marker blood panel and understands none of it. Can you turn it into a cited, plain-language explanation — and a smart set of questions to bring to their clinician?

**Build:** an agent that parses a panel, maps markers to published reference ranges and ageing-relevant literature, grades what each result may plausibly suggest, and generates an explanation with an explicit uncertainty layer. Strictly non-diagnostic.

**Required output:**

1. Marker-by-marker interpretation with reference ranges and citations
2. Ageing-relevant patterns flagged with evidence grades and stated uncertainty
3. A "questions for your clinician" list
4. A one-screen summary a non-specialist can read in a minute

**Possible sources:**

- Synthetic panels (generate your own or use the provided fixtures)
- PubMed for marker literature · published reference-range sources
- **Tavily** for grounded retrieval · **Amass** for evidence traceability

**Evaluation:** calibrated language — saying "discuss this with your clinician" exactly when it should — beats confident overreach. The bar: ≥95% of marker-level statements verified as accurate on a clinician review pass, with every escalation judged appropriate.

## 3 · The trial navigator

*Volunteer profile → the right trial*

**The question.** People who could benefit from a clinical trial rarely find it. Can you match a volunteer profile to longevity-relevant trials they are plausibly eligible for — and show the reasoning behind every match?

**Build:** an agent over the ClinicalTrials.gov API that takes a structured profile, searches and filters recruiting studies, checks eligibility criteria line by line, and returns a ranked, cited shortlist with next steps.

**Required output:**

1. Ranked trial shortlist with per-criterion eligibility reasoning
2. Direct source links and last-checked dates for every match
3. Explicit "insufficient information" outcomes where the data is missing
4. A shareable one-page summary for the volunteer or their clinician

**Possible sources:**

- **ClinicalTrials.gov** — registered trials with a modern REST API and CSV downloads, refreshed on weekdays: ClinicalTrials.gov · API documentation
- **Claude (Anthropic)** for criterion-by-criterion reasoning · **Lovable** for the navigator interface

**Evaluation:** precision beats recall — three defensible matches beat thirty maybes. The bar: on a test set of profiles with known answers, every match in the top three survives a per-criterion check against the source.

## 4 · The polypharmacy check

*Medication list → a safer-ageing conversation*

**The question.** Older adults often take five or more medicines, and interaction risk compounds with age. Can you turn a medication list into a clinician-facing review brief that makes a deprescribing conversation easier?

**Build:** a tool that checks a medication list against open drug-label and interaction data, flags documented interactions and age-related cautions, and drafts discussion points a pharmacist or physician can verify — never automated advice.

**Required output:**

1. Interaction flags with severity and citations to label data
2. Age-related caution notes grounded in published criteria (e.g. STOPP/START literature)
3. Structured discussion points for a pharmacist or physician review
4. Honest "not found in sources" reporting instead of invented reassurance
5. A review interface where the pharmacist or physician accepts or rejects each flag, with decisions captured

**Possible sources:**

- **openFDA drug labels** — open API over structured US drug labelling: openFDA drug label API
- **DailyMed** — NLM's structured product labels: dailymed.nlm.nih.gov
- Synthetic medication lists only

**Evaluation:** every flag traceable to a source; false confidence is a fail, not a feature.

## 5 · Design a safe N=1 protocol

*Supplement stack → monitored, evidence-based self-experiment*

**The question.** People experiment with stacks of supplements and over-the-counter compounds, but interaction checkers are binary and nobody designs the experiment properly. Can you build an agent that turns a stack into a safe, monitored N=1 protocol a clinician could sign off on?

**Build:** an agent that reasons over interaction and pharmacology data, then designs the protocol: a baseline period, intervention sequencing, washouts, a monitoring schedule and explicit stop criteria — with citations and contraindication flags throughout.

**Required output:**

1. A structured protocol: baselines, sequencing, washout periods, monitoring schedule, stop criteria
2. Interaction and contraindication flags, each cited to a pharmacology source
3. Known high-risk combinations correctly flagged on a planted test set
4. A clinician sign-off step — edit or strike any protocol element before export, with changes logged
5. A clinician-reviewable one-page summary, with an optional voice read-out

**Possible sources:**

- **PrimeKG**, the **IUPHAR/BPS Guide to Pharmacology** and the **Probes & Drugs** portal — all in the playbook dataset library — plus openFDA label data
- **Geroprotectors.org** and **DrugAge** for model-organism lifespan evidence behind common compounds
- **Claude (Anthropic)** for the reasoning chain · **ElevenLabs** for the audio summary

**Evaluation:** it catches every planted high-risk interaction and refuses cleanly when the evidence is thin — false confidence is a fail, not a feature.

## 6 · Predict the menopause transition

*Longitudinal women's health data → earlier, personalised foresight*

**The question.** Menopause affects half the population yet remains one of the least personalised transitions in medicine — symptom onset, severity and timing vary widely and are managed largely by trial and error. Can you predict trajectories early enough to matter?

**Build:** a model (or agent) that uses longitudinal hormonal, demographic and lifestyle data to forecast symptom trajectories or timing, with an explanation layer a clinician or patient can actually read.

**Required output:**

1. A validated prediction — symptom burden or timing — with performance on a held-out split
2. Explainable drivers of each prediction, in plain language
3. An honest account of where it fails, and for whom
4. A one-screen summary, with an optional voice read-out

**Possible sources:**

- **SWAN (Study of Women's Health Across the Nation)** — 3,302 women followed for 30+ years — and the **UK Biobank age-at-menopause GWAS**, both in the playbook dataset library
- The ovarian-ageing single-cell atlases (mouse and human ovary) in the library for mechanistic priors

**Evaluation:** calibrated predictions that hold across subgroups beat leaderboard-chasing; state performance and limits explicitly. The bar: reported performance includes a held-out split and a subgroup breakdown, and a clinician reviewer rates the explanations accurate and non-alarmist.

## The partner stack — provided to every team

- **Anthropic** — the agent brain: Claude models, Claude Agent SDK and MCP for reasoning, tool-calling and grounded writing. Access details in the participant technical briefing.
- **Nebius** — GPU compute and model hosting; Token Factory credits via QR at the venue.
- **Tavily** — live web retrieval over guidelines, literature and trials; 8,000 credits per participant.
- **Amass** — evidence-grounded scientific memory via app, API and MCP; $500 credits per team.
- **ElevenLabs** — voice read-outs and audio summaries; 1 month Creator per participant.
- **Lovable** — a demo-ready front-end, fast; Pro Plan 1 with 100 credits (code in WhatsApp).

## How these challenges are run

- **Synthetic or self-generated data only.** Never upload identifiable health information into hackathon tools — use the provided fixtures or data you generate yourself.
- **Decision support, not diagnosis.** Frame every build as helping a clinician or informing a client. Outputs state their limits and route medical decisions to professionals.
- **Clinician in the loop.** If your output is clinician-facing, include a review step: a clinician can accept, edit or reject each item before anything is exported — and their corrections are logged as evaluation data.
- **Evidence-graded by default.** Every claim and flag carries a citation and a confidence. "Nothing reliable found" is a valid, scored outcome.
- **Tangible over theoretical.** A working flow a clinician can click through beats a polished slide about one.
- **Judged on the six weighted dimensions.** Impact, technical execution, novelty, evidence and responsible use, track fit, and demo quality — the strongest Track 4 projects score high on impact and evidence, not just interface polish.

<aside>
🎯

**Choosing between them?**

Pick the workflow your team can make real by Sunday. A narrow tool that works end to end beats a broad concept that cannot be demonstrated — mentors, including practising clinicians, can help you scope during Friday's track Q&A and Saturday's rotations.  ### 5 · Open / Wildcard

Propose your own challenge at the frontier of AI and longevity biotech.

**Best suited to:** interdisciplinary teams, researchers, founders, experimental builders and anyone pursuing a bold idea across AI, biotech and longevity.

</aside>
