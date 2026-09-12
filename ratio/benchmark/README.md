# Human labeling and agreement

The current working taxonomy has four categories and an independent low-confidence flag. Open `/ratio/#label`; the older `sheet.html` URL redirects there.

Build the sample with `python3 ratio/benchmark.py sheet`. Each reviewer uses their own code, judges the complete collected text without seeing predictions, and exports JSON. Research admin at `/ratio/#admin` imports several reviewers, shows labels per item, pairwise agreement and pipeline agreement for each reviewer, then exports CSV and an archive. Progress and imports remain browser-local.

For a reproducible command-line comparison:

```sh
python3 ratio/benchmark.py score --labels /path/to/reviewer-a.json /path/to/reviewer-b.json
```

The new importer rejects the old taxonomy and model-generated labels. It preserves conflicting reviewers and refuses to overwrite a reviewer's first verdict. It does not choose an alphabetical “primary” reviewer as truth or declare the development sample a passed final benchmark.

See [the instrument method](../INSTRUMENT.md) for sampling, source versions, attestation limits and verification. Human validation and the 90% final-evaluation target remain incomplete.
