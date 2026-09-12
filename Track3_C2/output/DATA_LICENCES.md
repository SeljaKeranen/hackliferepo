# Data licences and provenance

Generated: 2026-09-12

## NIH RePORTER (reporter)
- Source: https://reporter.nih.gov/ (API v2), retrieved 2026-09-12.
- Status: U.S. federal government data; generally public domain. Attribute NIH RePORTER.
- Derived fields: category labels (rules + DeepSeek deepseek-flash), amount_eur conversion.

## CORDIS (cordis)
- Source: https://cordis.europa.eu/ (search JSON + project JSON), retrieved 2026-09-12.
- Licence: CORDIS content is (c) European Union; reuse permitted under CC BY 4.0 unless
  stated otherwise. Check the CORDIS legal notice for third-party material.
- Derived fields: category labels, amount_eur conversion, first-country extraction.

## Swecris (swecris)
- Source: https://www.vr.se/english/swecris.html (API v1, `/v1/scp/export`), retrieved 2026-09-12.
- Auth: `Authorization: Bearer <public token>` (verified working 2026-09-12).
- Scope note: only records matched by precise ageing phrases are kept; records matched
  only by broad terms ("aging", "livslangd") were excluded (non-ageing noise).
- Funders mix governmental and private bodies; `extra.funder_type` is kept per record
  and a government-only split is published in aggregates.json.
- Licence: data openly accessible per VR; attribute Swecris.

## Exchange rates
- Source: ECB reference rates, 2026-09-11.
- Rates per EUR: {"USD": 1.1592, "DKK": 7.4748, "GBP": 0.85815, "SEK": 11.2373, "NOK": 10.7805}
- Usage: amount_eur = amount / rate_per_eur[currency].

## Classification labels
- rule_category: keyword baseline (rules v1).
- llm_category: DeepSeek model output (temperature 0), not human-verified.
- Human-verified benchmark: produced separately (30 records, see data/benchmark/).
