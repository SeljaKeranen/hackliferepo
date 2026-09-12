# Funding sources and permitted use

Access decision: 12 September 2026. This register advances evidence quality for the public funding report. Collection covers government funders and award records, without researcher names or contact details in Longview's exports.

| Source | Financial definition and scope | Reuse and retrieval |
| --- | --- | --- |
| [NIH RePORTER API](https://api.reporter.nih.gov/) | NIA-administered records for FY2024. Parent award amounts; constituent subprojects are excluded from sums. Country refers to the funding government. | Public federal award facts. Attribute NIH RePORTER. Full abstracts remain local; public releases use factual metadata and short supporting excerpts. API field definitions and [NIH's FAQ](https://report.nih.gov/faqs) document fiscal-year costs and parent/subproject treatment. |
| [Swecris API](https://www.vr.se/english/swecris/swecris-api.html) | Swedish Research Council (202100-5208) and Forte (202100-5240); FundingYear 2024. Government funder contributions, sometimes covering multi-year periods. | The [Swecris reuse terms](https://www.vr.se/english/swecris.html), checked 12 September 2026 under “Use of data from Swecris”, explicitly permit internal and public use and ask for source attribution. No named CC licence is stated there. Retain raw text locally; redistribute factual grant metadata and short excerpts only. Fetch the documented public API token at runtime; never put it in a public build. |
| Existing Aging Funding Atlas CSVs | Candidate labels and record identifiers, from the team's earlier keyword sample. | Preserve the original attribution and [licence notes](../../data/Track3_C2/output/DATA_LICENCES.md). These CSVs cannot establish complete portfolio coverage, current sources or human verification. |
| You.com and Tavily | Discovery and corroboration of source definitions and funder identity. | Continue the existing 500 combined attempted-request ledger. Search summaries do not establish funding facts. No additional paid classification service is used. |

Native currency is retained. Ratios compare allocation shares; absolute amounts in SEK and USD are not combined or currency-converted. Funding commitments and NIH fiscal-year awards are not actual annual spending. Care services, pensions and general health expenditure are outside the denominator.

The previous atlas's ratios count records. Its Swecris source label also incorrectly says CORDIS/EU. Longview rebuilds the funding totals from source records and uses funder-based country attribution.
