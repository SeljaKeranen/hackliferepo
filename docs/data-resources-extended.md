# Data resources: review and extensions

Review of the 81-entry library in [data-resources.md](data-resources.md), plus additional
sources found while preparing for the hackathon. Links and access notes checked
8 September 2026. Where a licence is not stated below, verify terms at the source before
use, per the checklist in [AGENTS.md](../AGENTS.md).

## Review of the existing library

Coverage is strong on perturbation screens (LINCS, sci-Plex, Tahoe-100M, Perturb-seq,
JUMP, RxRx), single-cell atlases (CELLxGENE Census, Tabula Sapiens and Muris Senis,
Human Cell Atlas), and ageing cohorts (HRS, ELSA, LASI, MHAS, SWAN, SAGE). The weakest
spots, given our tracks:

- Ageing-gene gold standards are missing. The library has CellAge, DrugAge, AnAge and
  LongevityMap from HAGR but not GenAge, the benchmark set of ageing-related genes that
  most papers validate against.
- Gold-standard intervention outcomes are missing. DrugAge and Geroprotectors.org
  aggregate heterogeneous literature experiments; the NIA Interventions Testing Program
  (multi-site, genetically heterogeneous mice, pre-registered protocols, negative results
  published) is the cleaner label set for any repurposing or prediction task.
- Chemistry plumbing is missing. No ChEMBL, PubChem, ZINC, DrugCentral or BindingDB, so
  name-to-structure resolution, bioactivity lookup and purchasability checks have no
  canonical source in the list.
- Clinical-chemistry biological age is not directly computable from the list. The
  accelerometer-only NHANES entry (67) does not include the lab panels needed for
  PhenoAge/KDM-style clocks; full NHANES does.
- Senescence has SenOmic and CellAge but not SenNet, the NIH consortium portal built
  specifically to map senescent cells in human tissue.
- Track 3's own briefs name PubMed, ClinicalTrials.gov, Swecris and CORDIS, none of which
  appear in the library table. Their heavier-duty siblings (AACT, Europe PMC, OpenAlex)
  are worth knowing about.
- Microbiome ageing is absent entirely.

Access watch-outs found by direct probing on 7 September 2026:

- Geroprotectors.org (32) and EUbOPEN Gateway (79) are JavaScript apps; no bulk download
  or public API was found. Plan to scrape or query interactively, not pipeline.
- SenOmic (44) bulk files are hosted on Google Drive links (65 to 311 MB zip per senescence
  type) and need a confirm-token download flow.
- iLINCS REST API serves signature metadata only; gene-level L1000 vectors are available
  through L1000CDS2 at maayanlab.cloud (entry below).
- Tahoe-100M (17) ships as 3,388 single-cell parquet shards; budget time for subsetting.
- Restricted or on-request entries that will not arrive over a weekend: BLSA (1), GNPC (2),
  Parse PBMC atlas (23), organ-ageing plasma proteome (36), Mammalian Methylation
  Consortium browser (41), AI-READI (49), Natural Cycles (57). AlphaFold 3 server (4) and
  State (51) are rate-limited or gated. Cell2Sentence-Scale (60) is listed as unavailable.
- KEGG (7) API terms restrict bulk redistribution; fine for lookups, do not republish.

## Additions, continuing the library numbering

### Ageing-biology reference sets

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 82 | [GenAge](https://genomics.senescence.info/genes/) | Data | Omics, biomarkers | Human, model organisms | Open | Benchmark ageing-gene set (307 human, 2,000+ model-organism genes), zipped TSV downloads. The validation yardstick most ageing-gene papers use. |
| 83 | [Open Genes](https://open-genes.com/) | Data | Omics, perturbations, lifespan | Human, model organisms | Open | 1,700+ curated experiments with structured setups; REST API (open-genes.org/api/docs), TSV dumps, and an MCP server (opengenes-mcp). |
| 84 | [SynergyAge](https://synergyage.info/) | Data | Omics, perturbations | Model organisms | Open | Synergistic and antagonistic genetic interactions affecting lifespan; fills the combination gap left by single-gene sets. |
| 85 | [Digital Ageing Atlas](https://ageing-map.org/) | Data | Biomarkers, clinical, omics | Human, mouse | Open | 3,000+ curated age-related changes across molecular to physiological levels; full database download. |
| 86 | [MitoAge](https://www.mitoage.org/) | Data | Omics, comparative | 922 animal species | Unreachable on 8 Sep 2026 | mtDNA composition features linked to lifespan records (922 species). Host did not respond during the link audit; if it stays down, use the paper ([PMID 26590258](https://pubmed.ncbi.nlm.nih.gov/26590258/)) and its supplementary data instead. |
| 87 | [NIA Interventions Testing Program via Mouse Phenome Database](https://phenome.jax.org/projects/ITP1) | Data | Lifespan, drugs, phenotypes | Mouse (UM-HET3) | Open | 54 compounds, 164 trials, three sites, SOPs, negative results included. Highest-quality mammalian intervention labels available. |
| 88 | [SenNet Data Portal](https://data.sennetconsortium.org/) | Data | Single-cell, spatial, imaging, omics | Human, mouse | Open | NIH Cellular Senescence Network; harmonized senescence datasets with REST search API (search.api.sennetconsortium.org); downloads via free Globus login. |

### Chemistry and drug data

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 89 | [ChEMBL](https://www.ebi.ac.uk/chembl/) | Data | Drugs, bioactivity | Multiple | Open (CC BY-SA 3.0) | 2M+ compounds with measured activities against targets; the standard bioactivity source the library lacks. SQLite dump or web API. |
| 90 | [PubChem](https://pubchem.ncbi.nlm.nih.gov/) | Data, tool | Drugs, structure | Multiple | Open (public domain) | PUG-REST API resolves name to structure to CID to bioassay in one call; the practical backbone for compound identity mapping. |
| 91 | [ZINC15](https://zinc15.docking.org/) | Data | Drugs, structure | n/a | Open | 230M+ purchasable compounds with vendor links; answers "can we actually buy the hit" for validation experiments. |
| 92 | [DrugCentral](https://drugcentral.org/) | Data | Drugs, clinical | Human | Check licence (non-commercial terms) | Approved drugs with targets, indications, off-label use and adverse events; purpose-built for repurposing questions. |
| 93 | [BindingDB](https://www.bindingdb.org/) | Data | Drugs, bioactivity | Multiple | Open | Measured binding affinities (Ki, IC50, Kd) for 3M+ interactions; complements ChEMBL for potency ranking. |
| 94 | [L1000CDS2](https://maayanlab.cloud/L1000CDS2/) | Data, tool | Drugs, omics, perturbations | Human cell lines | Open | Precomputed LINCS L1000 characteristic-direction signatures with a JSON query API (gene-set in, ranked concordant or reversing signatures out). Working route to gene-level LINCS data since the iLINCS REST API is metadata-only. |

### Cohorts, mortality and clinical

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 95 | [NHANES full surveys](https://wwwn.cdc.gov/nchs/nhanes/Default.aspx) | Data | Biomarkers, clinical | Human | Open | The lab panels (chemistry, CBC, glycohemoglobin) behind PhenoAge and KDM clocks; entry 67 is only the accelerometer subset. |
| 96 | [Human Mortality Database](https://www.mortality.org/) | Data | Mortality | Human, 40+ countries | Free registration, CC BY 4.0 | Gold-standard period and cohort life tables; the reference for any mortality-rate claim. |
| 97 | [Gateway to Global Aging Data](https://g2aging.org/) | Data, tool | Biomarkers, clinical | Human, 40+ countries | Free registration | Harmonized HRS-family files (HRS, ELSA, SHARE, CHARLS, LASI and more) with comparable variables; one download instead of per-study wrangling. |
| 98 | [FinnGen](https://www.finngen.fi/en) | Data | Omics, clinical (GWAS) | Human | Open summary statistics | Population-scale GWAS summary stats including age-related endpoints; no application needed for released summary data. |
| 99 | [BioAge R package](https://github.com/dayoonkwon/BioAge) | Tool | Clinical biomarkers | Human | Open (GPL-3.0) | Computes KDM, PhenoAge and homeostatic-dysregulation biological age from blood panels; ships NHANES III/IV training data, so a clock demo works on day one. |

### Omics and pathway infrastructure

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | [Reactome](https://reactome.org/) | Data | Pathways | Human + models | Open (CC BY 4.0) | Curated pathway database with stable IDs and an analysis API; cleaner for programmatic use than KEGG (7), whose terms restrict bulk use. |
| 101 | [STRING](https://string-db.org/) | Data | Pathways, interactions | Multiple | Open (CC BY 4.0) | Protein-protein interaction network with confidence scores and bulk downloads; standard for turning gene hits into mechanism hypotheses. |
| 102 | [PRIDE / ProteomeXchange](https://www.ebi.ac.uk/pride/) | Data | Proteomics | Multiple | Open | Raw and processed proteomics; fills the proteome gap left by the restricted GNPC (2) and Oh 2023 (36) entries. |
| 103 | [Metabolomics Workbench](https://www.metabolomicsworkbench.org/) | Data | Metabolomics | Multiple | Open | NIH metabolomics repository with REST API; ageing metabolome studies included. |
| 104 | [HMDB](https://hmdb.ca/) | Data | Metabolomics | Human | Free for academic use | Reference metabolite database with concentrations and disease links; pairs with 103. |
| 105 | [ImmPort](https://www.immport.org/) and [10,000 Immunomes](http://www.10kimmunomes.org/) | Data | Immune phenotyping, omics | Human | Open (registration for ImmPort downloads) | Harmonized healthy-subject immune data (10KIP: 42,117 samples, 10,344 subjects) with age, sex and race annotated; immune-ageing analyses without a cohort application. |

### Imaging

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 106 | [Image Data Resource (IDR)](https://idr.openmicroscopy.org/) | Data | Imaging | Multiple | Open (CC0/CC BY) | Published reference microscopy with image-level metadata and an API; complements BBBC (11) and JUMP (80). |
| 107 | [BioStudies](https://www.ebi.ac.uk/biostudies/) | Data | Mixed, imaging | Multiple | Open | EMBL-EBI supplementary-data archive; often the actual home of figures and tables behind ageing papers. |

### Models and analysis tools

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 108 | [Geneformer](https://huggingface.co/ctheodoris/Geneformer) | Model | Omics, perturbations | Human | Open (Apache 2.0) | Single-cell transformer with an in-silico perturbation module; pretrained weights on Hugging Face. |
| 109 | [scGPT](https://github.com/bowang-lab/scGPT) | Model | Omics, perturbations | Human | Open (MIT) | Single-cell foundation model; whole-human pretrained checkpoint; perturbation-prediction tutorials included. |
| 110 | [GEARS](https://github.com/snap-stanford/GEARS) | Model | Omics, perturbations | Human | Open | Graph model for single and combinatorial genetic-perturbation response; trained on Perturb-seq (18). |
| 111 | [Perturbation-model benchmark caution](https://www.biorxiv.org/content/10.1101/2024.09.16.613342) | Paper | Omics, perturbations | n/a | Open | Evidence that deep perturbation models do not yet beat simple linear baselines; cite this when stating model uncertainty, judges will know it. |

### Literature, trials and funding (Track 3 plumbing)

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 112 | [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api) | Data | Clinical trials | Human | Open | REST API, JSON or CSV, refreshed on weekdays; the Track 3 claim-audit brief names it. |
| 113 | [AACT](https://aact.ctti-clinicaltrials.org/) | Data | Clinical trials | Human | Open (free account) | All of ClinicalTrials.gov as a queryable PostgreSQL database, updated daily; use for aggregate trial analyses the web API makes painful. |
| 114 | [Europe PMC](https://europepmc.org/) | Data | Literature | n/a | Open | Full-text open-access articles plus a bulk API; more permissive for text mining than PubMed's E-utilities. |
| 115 | [OpenAlex](https://openalex.org/) | Data | Literature, citations, funding | n/a | Open (CC0) | Scholarly graph of works, authors, funders and citations; free API and full snapshot; suits the political-mapping and follow-the-money briefs. |

### Microbiome

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 116 | [curatedMetagenomicData](https://waldronlab.io/curatedMetagenomicData/) | Data, tool | Microbiome | Human | Open (Bioconductor) | 22,710 uniformly processed metagenomes from 94 datasets with age for 21,213 samples; a published age meta-analysis vignette ships with it. |
| 117 | [GMrepo](https://gmrepo.humangut.info/) | Data | Microbiome | Human | Open | Curated gut metagenomes with phenotype annotation and a browser query builder filtering by age and BMI. |

## Second extension round, every entry verified live 8 September 2026

Each URL below was fetched successfully during the audit unless marked otherwise.

### Genetics of ageing and disease

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 118 | [GWAS Catalog](https://www.ebi.ac.uk/gwas/) | Data | Omics, clinical | Human | Open | All published GWAS with full summary statistics, including longevity, healthspan and parental-lifespan studies. REST API plus bulk downloads. |
| 119 | [OpenGWAS (MRC IEU)](https://gwas.mrcieu.ac.uk/) | Data, tool | Omics, clinical | Human | Open (free API token) | 50,000+ curated GWAS summary datasets in one format; the library's entry 73 is one dataset from here. |
| 120 | [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) | Data | Omics, clinical | Human | Open | Variant-phenotype assertions, including progeroid-syndrome genes; FTP bulk files. |
| 121 | [gnomAD](https://gnomad.broadinstitute.org/) | Data | Omics | Human | Open | Population allele frequencies and gene-constraint scores; the standard "is this target safe to perturb" filter. |
| 122 | [Gene Ontology](https://geneontology.org/) + [QuickGO](https://www.ebi.ac.uk/QuickGO/) | Data | Pathways, function | Multiple | Open (CC BY 4.0) | The functional-annotation layer the library does not include; QuickGO for programmatic queries. |

### Structural biology

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 123 | [AlphaFold DB](https://alphafold.ebi.ac.uk/) | Data | Structural | Multiple | Open (CC BY 4.0) | 200M+ precomputed predicted structures with bulk download; the open counterpart to the restricted AlphaFold 3 server (4). |

### Knowledge graphs

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 124 | [SPOKE](https://spoke.rbvi.ucsf.edu/) | Knowledge graph | Drugs, omics, clinical, pathways | Human | Open API, no bulk download | 27M nodes, 53M edges across 40+ sources; REST API and Neighborhood Explorer. Bulk is withheld on purpose (upstream licences), so query, do not scrape. |
| 125 | [Hetionet](https://github.com/hetio/hetionet) | Knowledge graph | Drugs, omics, pathways | Human | Open (CC0 data) | The integrative network behind Project Rephetio drug-repurposing; fully downloadable, static since 2016 but canonical. |

### Single-cell ageing

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 126 | [AgeAnno](https://relab.xidian.edu.cn/AgeAnno/) | Data | Omics, single-cell, tissue | Human | Open | 1.68M cells across 28 healthy tissues, ages 0-110, annotating 5,580 ageing genes (DEGs, cell communication, TF networks, scATAC). Downloads via its GitHub repo. |
| 127 | [Aging Fly Cell Atlas](https://hongjielilab.org/afca) | Data | Omics, single-cell | Drosophila | Open | 566k nuclei, four ages, sex-stratified, with trained aging clocks; also on CELLxGENE and GEO (GSE218661). |
| 128 | [Broad Single Cell Portal](https://singlecell.broadinstitute.org/single_cell) | Data, tool | Omics, single-cell | Multiple | Open | Hosts ageing-brain studies (for example Ximerakis et al. 2019) with downloadable matrices when a study is public. |

### Ageing clocks and computation

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 129 | [PyAging](https://github.com/lucascamillomd/pyaging) | Tool | Omics, clocks | Human, mouse, C. elegans, mammals | Open source | GPU-backed compendium of DNAm, transcriptomic, histone and ATAC clocks; one call scores many clocks on an AnnData object. |
| 130 | [RNAAgeCalc](https://bioconductor.org/packages/RNAAgeCalc) | Tool | Omics, clocks | Human | Open (GPL-2) | GTEx-trained transcriptomic age, tissue-specific and cross-tissue; Bioconductor package. |
| 131 | [Horvath DNAmAge calculator](https://dnamage.clockfoundation.org/) | Tool | Omics, clocks | Human | Free registration | The original epigenetic clock web calculator; useful as the reference implementation when comparing clocks. |
| 132 | [EWAS Open Platform](https://ngdc.cncb.ac.cn/ewas/) | Data, tool | Omics (methylation) | Human | Open | EWAS Atlas (1.09M curated associations, 17k causal links), EWAS Data Hub (180k normalized DNAm samples), plus an analysis toolkit. |

### Safety, regulatory and drug identity

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 133 | [openFDA](https://open.fda.gov/) | Data, tool | Drugs, clinical | Human | Open (public domain) | Harmonized FDA drug labels and FAERS adverse-event reports over a JSON API; the quick route to safety and indication checks. |
| 134 | [EPA CompTox Dashboard](https://comptox.epa.gov/dashboard/) | Data, tool | Drugs, toxicology | Multiple | Open | ToxCast/Tox21 in-vitro bioactivity for thousands of chemicals; batch search and downloads for safety triage. |
| 135 | [RxNav / RxNorm API](https://lhncbc.nlm.nih.gov/RxNav/) | Tool | Drugs | n/a | Open | NLM drug-name normalization (brand, generic, ingredient, RxCUI). Solves the name-matching problem when joining DrugAge-style labels to chemistry databases. |

### Model-organism reference

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 136 | [WormBase](https://wormbase.org/) | Data | Omics, phenotypes | C. elegans | Open (anti-bot blocked scripts at audit; fine in a browser) | Curated lifespan and ageing phenotypes per gene/variant for the workhorse longevity organism. |
| 137 | [FlyBase](https://flybase.org/) | Data | Omics, phenotypes | Drosophila | Open | Gene and allele phenotypes including lifespan; pairs with the Aging Fly Cell Atlas (127). |

### Literature, trials and funding (Track 3 plumbing)

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 138 | [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/) | Tool | Literature | n/a | Open | The Track 3 claim-audit brief names PubMed; E-utilities is its programmatic interface. |
| 139 | [Semantic Scholar API](https://api.semanticscholar.org/) | Data, tool | Literature, citations | n/a | Open | Citation graphs, influence scores and TLDR abstracts; complements Europe PMC (114). |
| 140 | [NIH RePORTER API](https://api.reporter.nih.gov/) | Data | Funding | n/a | Open | US grant titles, abstracts, amounts, investigators; the follow-the-money brief's US arm. |
| 141 | [CORDIS](https://cordis.europa.eu/) | Data | Funding | n/a | Open | EU framework projects as CSV/JSON/XML; the follow-the-money brief's EU arm. |
| 142 | [Swecris](https://www.swecris.se/) | Data | Funding | n/a | Open API | Swedish research grants; named in the playbook with a public test token. Local angle for a Stockholm submission. |

### Flagship cohort (planning note)

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 143 | [UK Biobank](https://www.ukbiobank.ac.uk/) | Data | Biomarkers, clinical, imaging, omics | Human | Restricted (application and fee; anti-bot blocked scripts at audit) | The reference prospective cohort behind most ageing-biomarker papers. Listed so Friday planning does not assume weekend access; use NHANES (95) and g2aging (97) instead. |

## Link audit, 8 September 2026

All 146 unique URLs across both data docs were fetched programmatically (parallel GET,
browser user agent, 25 s timeout), with failures retried by curl. A first pass covered the
117 library plus first-extension entries; a consolidated second pass the same day covered
the full 146 including the second extension round, with identical results.

Result: 127 return HTTP 200, 6 return 202 (Figshare, Dataverse and Shinyapps answer
asynchronously; fine in a browser), 1 returns 203 (PubMed to scripted clients; fine in a
browser), 6 return 403 to scripts but open in a browser (HMDB 104, OpenAlex 115,
UK Biobank 143, WormBase 136, HRS 70, Zenodo entry 20), and the rest are below.

Result: 101 return HTTP 200, 6 return HTTP 202 (Figshare, Dataverse and Shinyapps answer
asynchronously; fine in a browser), 4 return 403 to scripts but open in a browser
(HMD's neighbour HMDB 104, OpenAlex 115, HRS 70, Zenodo entry 20), and the rest are below.

Problems worth acting on:

| Entry | Resource | Status 8 Sep 2026 | Action |
| --- | --- | --- | --- |
| 86 | MitoAge | host unreachable (http and https) | Treat as unavailable; paper and supplements remain |
| 46 | ClockBase | host unreachable (port 3838 Shiny server) | Treat as unavailable; Biolearn (38) covers the same clocks |
| 59 | TxGNN | HTTP 503 | Site down; model and data live at [github.com/mims-harvard/TxGNN](https://github.com/mims-harvard/TxGNN) |
| 13 | ENCODE | HTTP 502 at both audits today | Degraded all day on 8 Sep; retry on the day, and mirror via its AWS Open Data bucket if it stays down |
| 16 | LINCS | lincsproject.org root 404s for some clients | Works in a browser; gene-level data via iLINCS metadata API plus L1000CDS2 (94) |
| 32, 79 | Geroprotectors.org, EUbOPEN | reachable but JavaScript-only | No bulk download or public API found; scrape or query interactively |
| 44 | SenOmic | reachable | Bulk files are Google Drive links needing a confirm-token download flow |
| 17 | Tahoe-100M | reachable | 3,388 parquet shards; subset before committing |
| 60 | Cell2Sentence-Scale | no link in library, marked unavailable | Skip |
| 1, 2, 23, 36, 41, 49, 57 | BLSA, GNPC, Parse PBMC, Oh 2023, Mammalian Methylation, AI-READI, Natural Cycles | restricted or on request | Will not arrive over a weekend; exclude from Friday plans |

Overlap check, library vs additions: no unintended duplicates. Deliberate complements are
cross-referenced in their Notes columns: L1000CDS2 (94) is the working data route for
LINCS (16); OpenGWAS (119) is the platform behind entry 73; AlphaFold DB (123) is the open
counterpart of the restricted AlphaFold 3 server (4); full NHANES (95) supersedes the
accelerometer-only entry 67 for clock work; Reactome (100) substitutes for the
bulk-restricted KEGG (7); Biolearn (38) covers the down ClockBase (46).

## Which additions matter per track

- Track 1 (longevity biology): 82, 87 and 88 give benchmark genes, gold-standard
  intervention labels and senescence maps; 89 to 94 fix compound identity, potency and
  purchasability; 118 and 119 add the human-genetics evidence layer, 121 the
  target-safety filter, 133 and 134 the safety screens, and 135 the name normalization
  that joins labels to chemistry. 108 to 110 are the ready-made perturbation models,
  with 111 as the honesty citation.
- Track 3 (communication, trust, policy): 112 to 115 and 138 to 142 are the working
  stack for claim audits, funding analysis and political mapping, and they are all free
  to query this week.
- Track 4 (clinical translation): 95 plus 99 make a blood-panel biological-age demo
  computable offline; 96 and 97 supply the outcome references to validate it against,
  and 133 adds label and adverse-event checks. 143 is the flagship everyone cites but
  nobody can touch in a weekend.

## Suggested next step

Add the sources the team actually picks to the table in
[data-resources.md](data-resources.md) with licences confirmed at the source, and record
restricted or JS-only items as out of scope for the weekend rather than discovering that
on Saturday.
