# The ageing research funding report

This implements Track 3's public research funding challenge and advances the Demo Day evidence, technical execution and communication criteria. The current public release contains source records and a working review gate. Its numerical estimates are unverified and remain private.

The intended reader is a member of the public. Advocates can share a country report with its scope, period and sources attached. The question is how much of a selected government research portfolio targets ageing biology and interventions, relative to its classified ageing research funding. Whether the result supports an argument about a large funding gap is an empirical question.

## Scope and money

The snapshot was collected on 12 September 2026. Country means the government funding the award, not the recipient's address.

| Portfolio | Selection | Recorded amount |
| --- | --- | --- |
| United States | All NIA-administered FY2024 records returned by NIH RePORTER; 6,556 rows, excluding 1,214 constituent subprojects, leaving 5,342 parent award records | `award_amount`, direct plus indirect costs recorded for the fiscal year. FY2024 runs October 2023–September 2024. Multi-year funded awards can be exceptions to a one-year funding basis. |
| Sweden | All Swecris rows for Swedish Research Council `202100-5208` and Forte `202100-5240`, then filter `fundingYear == 2024`; 1,281 retained records | `fundingsSek` attributed to the selected government funder. Funding periods can span several years. |

The NIH parent/subproject exclusion follows its [FAQ, “Grant and Contract Costs” and italicised subproject costs](https://report.nih.gov/faqs), checked 12 September 2026. Its [API field definitions](https://api.reporter.nih.gov/documents/Data%20Elements%20for%20RePORTER%20Project%20API_V2.pdf) describe the source fields. [Swecris API documentation](https://www.vr.se/english/swecris/swecris-api.html) supplies the access route; the source portal displays the funding period and total funding for each award. For example, [project 2023-00231_VR](https://www.vr.se/english/swecris.html#/project/2023-00231_VR), opened on 12 September, displays a 2024–2031 funding period. That observation is an assistant source check, not a human review verdict.

These are complete API snapshots of narrower portfolios, subject to the source databases' own omissions and revisions. They are not national research totals. All years were paged for the two Swedish funders before filtering locally, so a search engine's interpretation of “2024” does not determine the sample. The query metadata and response hashes are retained locally. A reported count mismatch or incomplete pagination fails collection.

Money is kept in integer minor units, with original currency and period. Genuine zero amounts are preserved; missing amounts remain null. Do not annualise, combine SEK with USD, infer actual expenditure or rank countries using these portfolios. Care delivery, pensions and total health expenditure do not enter the denominator. The US portfolio includes NIA-administered awards, which may have contributions from other federal institutes; it is not an estimate of NIA's own appropriation.

## Objective taxonomy and classifier

Each award has one candidate objective. Mixed programmes are classified by the stated main objective only when support is clear; no amount is fractionally allocated across inferred subprojects.

| Category | Inclusion rule |
| --- | --- |
| `fundamental_aging` | Ageing mechanisms and biology, including a defined ageing mechanism studied across disease settings |
| `intervention` | An intervention whose stated objective targets ageing biology, senescence, lifespan or healthspan |
| `age_related_disease` | An age-related disease objective without an established ageing-biology objective |
| `care_research` | Research into care and support for older people or carers; not care delivery |
| `other_aging_research` | Social, behavioural, demographic and other nonbiological ageing research |
| `outside_scope` | No qualifying ageing objective, including unrelated physical/materials research and childhood-specific objectives |
| `unresolved` | Unclear relevance, missing evidence or a mixed objective that needs review |

The versioned local rule classifier reads the complete available abstract, with title precedence for certain clear objectives. It has not yet been validated by human reviewers. Word matches can mistake background for objectives or miss biology described indirectly. Swedish-language abstracts are unresolved under this English rule set. Short or missing abstracts also remain unresolved.

The teammate's CSVs and [methodology](../../data/Track3_C2/METHODOLOGY.md) remain unchanged. Earlier model classifications can be reused as candidates only after an exact title, year and amount match, a verbatim source passage match and agreement with the current rule. They are not human ground truth. The earlier published ratios counted grants; this implementation weights amounts. No additional paid model calls were made.

## Numerator, denominator and uncertainty

Let **N** be known funding for ageing biology plus ageing interventions; **D** be known funding in the five classified ageing categories; **U** be known funding labelled unresolved.

- Central estimate: **N / D**.
- Biology-only context: **fundamental ageing / D**; intervention funding is also shown separately.
- Lower sensitivity bound: **N / (D + U)**, assigning unresolved money to other ageing research.
- Upper sensitivity bound: **(N + U) / (D + U)**, assigning unresolved money to biology or interventions.

These scenarios bound category uncertainty among known amounts. They are not confidence intervals and do not cover errors in already resolved categories. Missing amounts are counted outside the bounds; no finite total uncertainty claim is made about them. If D is zero, the ratio and both bounds are unavailable.

## Human gate and falsification

The separate funding benchmark contains 60 records, 30 per country. A seed-42 shuffle and category round-robin cover rare categories. Twelve development cases are excluded. Forty benchmark titles lack an ageing keyword. This is a stratified diagnostic sample, not an unbiased estimate of whole-portfolio accuracy.

The reviewer sees source facts and the original-source link, without the prediction or classifier-selected passage. They select the main objective and mark source resolution, financial details and government scope. A record passes only if the category agrees with the frozen prediction and every check passes. The first completed verdict is retained in an append-only event history.

Publication requires all 60 reviews, at least 54 correct overall and 27 in each country. In addition, the ten largest monetary awards per country must pass source and category checks, including large outside-scope exclusions. Each report needs human approval of source scope, funding basis, arithmetic and visible uncertainty. Source, label or taxonomy changes invalidate affected approvals. A changed population cannot silently overwrite the frozen benchmark; preserve it and create an explicitly versioned new evaluation before releasing updated estimates.

Failing any gate blocks numerical publication. A small candidate share is insufficient evidence for the headline. Until approval, public classification fields and aggregate monetary ratios are null; the encrypted private workspace contains estimates for review. The earlier 34-record policy benchmark and 30-record grant benchmark stay separate.

See [the funding review guide](../../eval/funding/README.md) for the remote workflow, import command and tests. No human verdict has yet been imported for this release.

## Evidence and intended use

[Dataset and reuse register](dataset-register.md) documents access and limits. [Dated You.com and Tavily cross-checks](source-crosschecks.json) record discovery queries and links. Both providers were used, with 73 combined attempted requests out of the authorised 500 across the project. Search summaries never establish award facts or human correctness.

The release's source ledger contains factual metadata, original URLs, source dates, retrieval timestamps, amount basis and hashes. Full abstracts, raw API responses, researcher fields and credentials remain outside public releases and Git. Approved aggregate findings follow `schema/finding.schema.json`; pending releases contain no such findings.

The adoption test is still proposed: ask five readers, without coaching, to identify the portfolio, funding period, numerator and uncertainty, then find a source. Record whether they can interpret the main visual within three seconds and find the underlying source within 30 seconds. No adoption or comprehension result has been measured. The tool makes no clinical claims and does not predict the lifespan effect of funding.
