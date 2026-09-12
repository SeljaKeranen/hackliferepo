# Method discussion with Andrew

Prepared for the team's 13:00 call on 12 September 2026. This brief supports the Demo Day evidence and novelty criteria. The call has not happened in this record; no agreement or expert validation is implied.

We have collected complete 2024 API portfolios for NIA-administered awards in the US and Swedish Research Council plus Forte in Sweden. The source facts are available, but the biological boundary is still a classification problem. We need a method that remains defensible when a project never uses “ageing” in its title.

The headline would be ageing biology plus interventions targeting ageing, divided by all classified ageing-related research funding in the selected portfolio. Biology-only funding stays visible separately. It is an award-weighted estimate, with known unresolved amounts shown as sensitivity scenarios. Care delivery and pensions are excluded.

The decision for this call: what evidence in an abstract is enough to classify a mechanism project as ageing biology, and when should it stay disease research or unresolved?

| Development case | What the original abstract says, in our words | Decision to resolve |
| --- | --- | --- |
| [Ovarian ageing, infertility and cancer, VR 2023-01872](https://www.vr.se/english/swecris.html#/project/2023-01872_VR) | The work investigates molecular mechanisms behind differences in ovarian ageing, using clinical cohorts and biomarkers. Retrieved 12 Sep 2026; funding year 2024. | Does organ-specific reproductive ageing qualify as fundamental ageing for this ratio? The current rule leaves it unresolved. |
| [Fluid biomarkers for neurodegenerative dementias, VR 2023-00356](https://www.vr.se/english/swecris.html#/project/2023-00356_VR) | Biomarker development is directed at dementia pathology and clinical diagnosis. Retrieved 12 Sep 2026; funding year 2024. | Which additional objective would be needed to call this ageing biology rather than disease research? |
| [MIMS metabolic surgery trial, VR 2023-00453](https://www.vr.se/english/swecris.html#/project/2023-00453_VR) | The trial studies cardiovascular outcomes after metabolic surgery among people with severe obesity and prior myocardial infarction. Retrieved 12 Sep 2026; funding year 2024. | A metabolism label alone cannot establish an ageing intervention. Is disease research the correct category? |
| [Gut microbiome, ageing and cardiometabolic diseases, NIH 10646431](https://reporter.nih.gov/project-details/10646431) | The aims include microbiome features associated with biological ageing and mechanistic links among gut dysbiosis, ageing and cardiometabolic disease. Retrieved 12 Sep 2026; FY2024. | How should a genuinely mixed ageing-mechanism and disease objective be counted without inventing budget fractions? |
| [DNA methylation and cellular senescence, NIH 10746453](https://reporter.nih.gov/project-details/10746453) | The project uses epigenetic editing to investigate causal links with cellular senescence. Retrieved 12 Sep 2026; FY2024. | Is explicit cellular senescence sufficient, or must an organism-level ageing objective also be present? |
| [Post-retirement work, Forte 2024-00018](https://www.vr.se/english/swecris.html#/project/2024-00018_Forte) | The research concerns work after retirement, labour-market participation and social narratives. Retrieved 12 Sep 2026; funding year 2024. | This belongs in nonbiological ageing research if the agreed denominator includes social ageing. Confirm that scope. |

These are development examples, selected by the assistant for discussion. They are excluded from the frozen 60-record benchmark and are not expert-labelled ground truth. Their machine candidates can be wrong. Full IDs, source dates and candidate status are in [development-cases.json](development-cases.json); the complete original abstracts remain at the source and in the ignored local research store.

Also settle whether training grants, research centres and publication support should be inside a research portfolio ratio, and how to handle mixed centres whose parent award covers several objectives. If that changes the taxonomy, preserve the existing evaluation and freeze a new version before measuring accuracy.

The current benchmark has no imported human verdicts. The public site shows that state. We should leave the call with a written boundary rule and a reviewer for the blinded sample, not an endorsement of a preselected funding-gap claim.
