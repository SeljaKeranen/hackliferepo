# Review the funding report

This is the new 60-record funding evaluation. The earlier policy review at `/review/` and the teammate's grant benchmark are preserved separately.

Open `/review/funding/` with the private fragment key from `outputs/funding-reviewer.key`. It is a browser decryption key, not a research API credential. The packet contains 60 blinded benchmark records plus 20 large-award records and two private report previews. The current union contains 80 distinct awards.

Enter reviewer initials and confirm that you will check the original sources. Open each award's source, read the full abstract, select the main research objective and mark the three checks. Classifier predictions are hidden. The browser locks the first completed award verdict and saves progress locally. The report tab shows the candidate monetary totals and separate report checks. Do not approve a report until its method and calculation have been inspected.

Export the completed JSON and give the file to the team. The page does not upload or publish reviews. Import a real human export with:

```bash
.venv/bin/python -m funding.review --import-file /path/to/human-export.json
.venv/bin/python -m funding.release
node scripts/package-funding-review.mjs
npm run build
```

Before releasing approved findings, set `PUBLIC_SITE_URL` to the public HTTPS deployment origin. Use the delivery commands in the root README to regenerate slides, recording and the hosted release. Never import `outputs/funding-browser-fixture-DO-NOT-IMPORT.json` or any test fixture. The importer rejects exports explicitly marked as simulations, unknown IDs, incomplete checks and stale source/review versions. A JSON attestation is not identity authentication; the team must establish that a real person made the review before importing it.

The benchmark passes at ≥54/60 overall and ≥27/30 in each country, after all 60 records are reviewed. Ten large-award checks per country and a report approval are additional publication requirements. First verdicts remain in `verdicts.json`; subsequent imports update `current`, and every distinct completed event appends to `history.jsonl`. Do not delete earlier errors to improve the reported score.

Changed source or label versions invalidate the relevant reviews and report approval. `funding.benchmark` refuses to overwrite a different frozen population. A new taxonomy or model requires an explicitly versioned evaluation; the old benchmark remains evidence of its original performance.

```bash
.venv/bin/python -m pytest -q tests/test_funding.py
node scripts/check-funding-browser.mjs
```

The tests use isolated synthetic verdicts. Passing software checks does not satisfy the human accuracy requirement.
