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

## Third extension round, verified live 9 September 2026

### Ageing biology and brain

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 144 | [GenDR](https://genomics.senescence.info/diet/) | Data | Omics, perturbations | Model organisms, human homologs | Open | HAGR's dietary-restriction gene database: DR-essential genes plus a conserved mammalian DR expression signature; TSV and Excel downloads. Completes the HAGR set (with 31, 37, 39, 40, 82). |
| 145 | [SASP Atlas](https://saspatlas.herokuapp.com/) | Data | Proteomics, biomarkers | Human | Open (CC0 on MassIVE MSV000083468) | Proteomic secretomes of senescent cells by inducer and cell type, soluble and exosomal; the reference for SASP composition and senescence biomarker candidates. |
| 146 | [HuBMAP portal](https://portal.hubmapconsortium.org/) | Data | Single-cell, spatial, tissue | Human | Open | NIH Human BioMolecular Atlas Program; spatial reference maps and an open API. SenNet's (88) sibling program, same portal technology. |
| 147 | [Allen Aging, Dementia and TBI study](https://aging.brain-map.org/) | Data | Omics, clinical, pathology | Human | Open (raw reads controlled via NIAGADS) | RNA-seq plus neuropathology from 107 aged brains (ACT cohort, median age at death 90); processed data download directly, no approval needed. |
| 148 | [AD Knowledge Portal](https://adknowledgeportal.synapse.org/) | Data | Omics, clinical | Human | Open with free Synapse registration | ROSMAP and related aging-brain multi-omics (WGS, RNA-seq, proteomics, methylation); the main open route to that cohort. |
| 149 | [Dog Aging Project](https://data.dogagingproject.org/) | Data | Clinical, biomarkers | Dog | Application plus data-use agreement, via Terra | Tens of thousands of companion dogs with annual curated releases; the leading comparative-geroscience cohort. Codebooks open on GitHub without an application. |

### Microbiome and meta-search

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 150 | [MGnify](https://www.ebi.ac.uk/metagenomics) | Data, tool | Microbiome | Multiple | Open | EBI's microbiome analysis platform; larger raw-coverage complement to the curated sets (116, 117). |
| 151 | [OmicsDI](https://www.omicsdi.org/) | Tool | Omics (all) | Multiple | Open | Cross-repository omics dataset search index with an API; the fastest way to find a dataset that no named library lists. |

### Models

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 152 | [scFoundation](https://github.com/biomap-research/scFoundation) | Model | Omics, single-cell | Human | Open weights; check repo licence | 50M-cell foundation model; complements scGPT (109) and Geneformer (108). |
| 153 | [Evo 2](https://github.com/ArcInstitute/evo2) | Model | Omics (DNA) | Multiple | Open (Apache 2.0) | Genome-scale DNA foundation model; the engine inside BioReason (52), usable standalone. |
| 154 | [Boltz](https://github.com/jwohlwend/boltz) | Model | Structural, drugs | Multiple | Open (MIT) | Open structure and binding-affinity prediction; the practical substitute when the AlphaFold 3 server (4) is rate-limited. |
| 155 | [AlphaMissense](https://console.cloud.google.com/storage/browser/dm_alphamissense) | Data | Omics, variants | Human | Open for non-commercial use (CC BY-NC-SA 4.0) | Precomputed pathogenicity scores for all ~71M possible missense variants; pairs with ClinVar (120) and gnomAD (121). Mind the non-commercial licence. |

### Reference and pharmacogenomics

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 156 | [Cellosaurus](https://www.cellosaurus.org/) | Data | Cell lines | Multiple | Open (CC BY 4.0) | The reference for cell-line identity, provenance and contamination flags; use before proposing any validation experiment. |
| 157 | [Orphanet](https://www.orpha.net/) | Data | Clinical, omics | Human | Free academic registration | Rare-disease reference including progeroid syndromes; gene-disease mappings with ORPHA codes. |
| 158 | [PharmacoDB](https://pharmaco.ca/) | Data, tool | Drugs, omics | Human cell lines | Open | Unified access to GDSC, CCLE, gCSI and PRISM drug-sensitivity datasets with one API; less wrangling than pulling each separately. |

### Literature and citations (Track 3)

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 159 | [Wikidata](https://www.wikidata.org/) | Knowledge base | Mixed | n/a | Open (CC0) | General structured backbone (genes, drugs, politicians, institutions) with SPARQL; useful glue for the political-mapping brief. |
| 160 | [OpenCitations](https://opencitations.net/) | Data | Citations | n/a | Open (CC0) | Open citation graph with API and dumps; pairs with OpenAlex (115). |
| 161 | [iCite](https://icite.od.nih.gov/) | Tool | Citations | n/a | Open | NIH citation-metrics API (Relative Citation Ratio); quick influence scores for the claim-audit evidence ladder. |

### Cancer and sleep (age-adjacent)

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 162 | [HTAN](https://humantumoratlas.org/) | Data | Omics, single-cell, imaging | Human | Open via Synapse | Human Tumor Atlas Network; spatial and single-cell tumor atlases for the age-related-cancer angle. |
| 163 | [NSRR (sleepdata.org)](https://sleepdata.org/) | Data | Clinical, signals | Human | Free with data-use agreement | Sleep polysomnography cohorts across ages; sleep is an underused healthspan readout. |
| 164 | [clue.io](https://clue.io/) | Tool | Drugs, omics, perturbations | Human cell lines | Free academic registration | The Broad's own Connectivity Map platform; the interactive counterpart to programmatic L1000CDS2 (94). |

Checked and excluded this round: SIDER (host offline; openFDA 133 covers adverse events),
Cochrane Library (bot-blocked and mostly paywalled; Europe PMC 114 covers systematic
reviews), LINCS Data Portal at lincsportal.ccs.miami.edu (unreachable; see entry 16 note).

## Fourth extension round, verified live 10 September 2026

Checked for overlap against the library (1-81), rounds 1-3 here (82-164), the eldercare
supplement's 13 entries, and the team-fit guide's S1-S19 before inclusion.

### Exercise and reprocessed expression at scale

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 165 | [MoTrPAC Data Hub](https://motrpac-data.org/) | Data | Omics, perturbations | Rat, human | Public data without an account; restricted files need registration | NIH molecular maps of exercise across tissues and timepoints; the omics of the best-established healthspan intervention. |
| 166 | [ARCHS4](https://maayanlab.cloud/archs4/) | Data | Omics | Human, mouse | Open | Uniformly reprocessed RNA-seq from most of GEO; the practical route to "all public expression data" without reprocessing. |
| 167 | [recount3](https://rna.recount.bio/) | Data | Omics | Multiple | Open | Uniformly reprocessed RNA-seq across GEO, SRA, GTEx and TCGA; overlaps 166 with different pipelines, useful for robustness checks. |
| 168 | [Expression Atlas](https://www.ebi.ac.uk/gxa/) | Data | Omics | Multiple | Open | EBI's curated expression experiments, including ageing studies; complements raw GEO (5) with consistent analysis. |

### Metabolomics, proteomics and glycobiology

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 169 | [MetaboLights](https://www.ebi.ac.uk/metabolights/) | Data | Metabolomics | Multiple | Open | EBI's metabolomics repository; the European counterpart to Metabolomics Workbench (103). |
| 170 | [MassIVE](https://massive.ucsd.edu/) | Data | Proteomics, metabolomics | Multiple | Open (CC0 common) | The UCSD mass-spec repository where, for example, the SASP Atlas (145) raw data lives; pairs with PRIDE (102). |
| 171 | [GNPS](https://gnps.ucsd.edu/) | Data, tool | Metabolomics | Multiple | Open | Molecular networking and spectral libraries for metabolomics analysis. |
| 172 | [GlyGen](https://www.glygen.org/) | Data | Glycobiology, omics | Human, model organisms | Open | NIH glycoscience portal; covers the glycan species behind IgG glycosylation ageing markers that the library otherwise lacks. |
| 173 | [LipidMaps](https://www.lipidmaps.org/) | Data | Lipidomics | Multiple | Open | Reference lipid structures, classes and measurements; lipid metabolism is central to ageing and absent from the library. |

### Interactions, abundance and regulation

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 174 | [IntAct](https://www.ebi.ac.uk/intact/) | Data | Pathways, interactions | Multiple | Open (CC BY 4.0) | EBI's curated molecular-interaction database; complements STRING (101) with experiment-level evidence. |
| 175 | [PaxDb](https://pax-db.org/) | Data | Proteomics | Multiple | Open | Integrated protein-abundance estimates across organisms and tissues; a quick reality check on whether a target is expressed at meaningful levels. |
| 176 | [ChIP-Atlas](https://chip-atlas.org/) | Data | Omics, regulation | Human, mouse | Open | Uniformly reprocessed public ChIP-seq and ATAC-seq; TF-target evidence for mechanism hypotheses. |

### Patents

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 177 | [SureChEMBL 2.0](https://www.surechembl.org/) | Data | Drugs, patents | n/a | Open | Compound-patent mappings from EMBL-EBI; the 2.0 relaunch ships biweekly Parquet bulk files (legacy MAP files deprecated). Freedom-to-operate signals for repurposing candidates. |

### Nordic statistics and dementia (supports the eldercare project docs)

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 178 | [SCB Statistikdatabasen](https://www.statistikdatabasen.scb.se/) | Data | Demographics, care, mortality | Human (Sweden) | Open (PxWeb API, attribution) | Statistics Sweden's official database; the population and mortality denominators behind any Swedish care indicator. |
| 179 | [NHWStat (NOMESCO/NOSOSCO)](https://nhwstat.org/) | Data | Health, welfare, expenditure | Human (Nordics) | Open (PxWeb API) | Nordic-comparable health and social statistics from the Nordic Council of Ministers' committees; the cross-country layer above the national portals. |
| 180 | [WHO Global Dementia Observatory](https://www.who.int/data/gho/data/themes/global-dementia-observatory-gdo/) | Data | Clinical, policy | Human (62+ countries) | Open (GHO OData API and bulk zips) | 35 standardised dementia indicators per country: diagnosis, care facilities, carer support, policy. Directly serves the ageing-and-dementia project docs. |
| 181 | [OpenNeuro](https://openneuro.org/) | Data | Imaging, EEG | Human | Open (mostly CC0 datasets) | The platform behind the eldercare supplement's ds004504; hundreds more MRI/EEG/iEEG datasets for dementia-adjacent work. |

### Policy, trials and communication

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 182 | [Our World in Data](https://ourworldindata.org/) | Data, tool | Demographics, health | n/a | Open (CC BY 4.0) | Life expectancy and ageing charts with an open data API; the fastest credible visual for Track 3 communication. |
| 183 | [UN World Population Prospects](https://population.un.org/wpp/) | Data | Demographics | n/a | Open (attribution) | Official UN population projections to 2100; the denominator for every "ageing society" claim. |
| 184 | [WHO ICTRP](https://trialsearch.who.int/) | Data | Clinical trials | Human | Open | Meta-search across 20+ national trial registries; catches trials that ClinicalTrials.gov (112) and AACT (113) miss. |
| 185 | [EU Clinical Trials Register](https://www.clinicaltrialsregister.eu/) | Data | Clinical trials | Human | Open | EU trial registrations and results; the European complement for claim audits. |

### Flagship cohort (planning note)

| # | Resource | Type | Data types | Species | Access | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 186 | [All of Us](https://allofus.nih.gov/) | Data | Biomarkers, clinical, omics, wearables | Human (US) | Restricted (registration, training, workspace compute fees; anti-bot blocked scripts at audit) | The US counterpart to UK Biobank (143) with strong wearable and diversity coverage. Listed for planning only; not weekend-usable. |

Checked and excluded this round: DeepBlue (deepblue.mpi-inf.mpg.de unreachable on
10 Sep 2026; ChIP-Atlas 176 and ENCODE 13 cover the regulatory-epigenomics use case).

## Link audit, 8 September 2026 (corpus-wide recheck 10 September 2026)

Corpus-wide pass on 10 September 2026: all 261 unique URLs across the four data documents
(library, this file, the eldercare supplement, and the team-fit guide's S1-S19) were
fetched programmatically (parallel GET, browser user agent, 25 s timeout), failures
retried with curl. Result: 227 return 200; 6 return 202 (Figshare/Dataverse/Shinyapps
async); 4 return 203 (NCBI/PubMed to scripted clients); 15 return 403 to scripts but open
in a browser (cdc.gov, oecd.org, doi.org/MDPI, hmdb.ca, openalex.org, ukbiobank.ac.uk,
allofus.nih.gov, wormbase.org, hrs.isr.umich.edu, zenodo.org). The team-fit guide's 20
URLs all pass. Remaining failures below.

Earlier passes on 8 September covered the 117 library plus first-extension entries and a
consolidated recheck of all 146 URLs then present; on 9 September the 24 third-round
candidates were checked before inclusion (20 OK, AlphaMissense URL fixed, SIDER/Cochrane/
LINCS Data Portal excluded); on 10 September the 23 fourth-round candidates were checked
(21 OK, All of Us anti-bot blocked, DeepBlue unreachable and excluded).

All 146 unique URLs across both data docs were fetched programmatically (parallel GET,
browser user agent, 25 s timeout), with failures retried by curl. A first pass covered the
117 library plus first-extension entries; a consolidated second pass the same day covered
the full 146 including the second extension round, with identical results. On 9 September
the 24 third-round candidate URLs were checked the same way before inclusion: 20 returned
200, AlphaMissense's landing page had moved (fixed to the live data bucket), and three
candidates were excluded as a result (SIDER offline, Cochrane bot-blocked, LINCS Data
Portal unreachable). On 10 September the 23 fourth-round candidates were checked: 21
returned 200, All of Us (186) is anti-bot blocked to scripts (restricted by design
anyway), and DeepBlue was unreachable and excluded.

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
| 16 | LINCS | lincsproject.org root 404s for some clients; lincsportal.ccs.miami.edu unreachable on 9 Sep | Works in a browser; gene-level data via iLINCS metadata API, L1000CDS2 (94) and clue.io (164) |
| 32, 79 | Geroprotectors.org, EUbOPEN | reachable but JavaScript-only | No bulk download or public API found; scrape or query interactively |
| 44 | SenOmic | reachable | Bulk files are Google Drive links needing a confirm-token download flow |
| 17 | Tahoe-100M | reachable | 3,388 parquet shards; subset before committing |
| 60 | Cell2Sentence-Scale | no link in library, marked unavailable | Skip |
| 1, 2, 23, 36, 41, 49, 57 | BLSA, GNPC, Parse PBMC, Oh 2023, Mammalian Methylation, AI-READI, Natural Cycles | restricted or on request | Will not arrive over a weekend; exclude from Friday plans |

Found in the eldercare supplement during the corpus-wide pass (for its author to fix):

| Document | Link | Status 10 Sep 2026 | Note |
| --- | --- | --- | --- |
| data-resources-extended-eldercare.md | dst.dk quality-statement PDF (GetArchiveFile.aspx?ext=kvaldel...) | HTTP 404, confirmed with curl | Dead link; use the StatBank documentation page instead |
| data-resources-extended-eldercare.md | nhats.org NHATSCogstateUserGuideR11-13_Oct2024.pdf | HTTP 404, confirmed with curl | Moved; current guide via nhats.org researcher documentation |
| data-resources-extended-eldercare.md | cdc.gov BRFSS pages (6 links) | 403 to scripts | Bot protection; fine in a browser |

Overlap check, library vs additions: no unintended duplicates. Deliberate complements are
cross-referenced in their Notes columns: L1000CDS2 (94) is the working data route for
LINCS (16); OpenGWAS (119) is the platform behind entry 73; AlphaFold DB (123) is the open
counterpart of the restricted AlphaFold 3 server (4); full NHANES (95) supersedes the
accelerometer-only entry 67 for clock work; Reactome (100) substitutes for the
bulk-restricted KEGG (7); Biolearn (38) covers the down ClockBase (46).

## Which additions matter per track

- Track 1 (longevity biology): 82, 87 and 88 give benchmark genes, gold-standard
  intervention labels and senescence maps; 144 and 145 complete the HAGR set and the
  SASP reference; 89 to 94 fix compound identity, potency and purchasability; 118 and
  119 add the human-genetics evidence layer, 121 and 155 the variant-safety filters,
  133 and 134 the safety screens, and 135 the name normalization that joins labels to
  chemistry. 108 to 110 and 152 to 154 are the ready-made models, with 111 as the
  honesty citation; 156 keeps the validation experiment's cell lines honest.
- Track 3 (communication, trust, policy): 112 to 115 and 138 to 142 are the working
  stack for claim audits, funding analysis and political mapping; 159 to 161 add a
  structured-knowledge backbone and two open citation graphs. All free to query this week.
- Track 4 (clinical translation): 95 plus 99 make a blood-panel biological-age demo
  computable offline; 96 and 97 supply the outcome references to validate it against,
  133 adds label and adverse-event checks, and 147, 148 and 163 open up brain-aging,
  dementia and sleep readouts. 143 and 186 are the flagships everyone cites but nobody
  can touch in a weekend.
- Eldercare and dementia direction (the team's supplement): 178 and 179 add the missing
  Swedish and Nordic-comparable statistical layers, 180 the WHO dementia indicators, and
  181 the broader EEG/MRI platform behind the supplement's single dataset.

## Suggested next step

Add the sources the team actually picks to the table in
[data-resources.md](data-resources.md) with licences confirmed at the source, and record
restricted or JS-only items as out of scope for the weekend rather than discovering that
on Saturday.
