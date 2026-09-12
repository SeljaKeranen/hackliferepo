# Research review instrument

The current demo is the four-label research instrument at `/ratio/`. It advances Demo Day technical execution, evidence and responsible use, and researcher adoption. It does not publish a funding number.

```sh
python3 -m ratio.instrument.build
python3 -m http.server 8010 --bind 127.0.0.1
```

See [INSTRUMENT.md](INSTRUMENT.md) for the method, source and licence register, human workflow, admin comparisons, limitations and verification commands. The classifier and review UI use [the working taxonomy](instrument/taxonomy.json). Andrew's confirmation and proper human validation are pending.

The earlier `build.py`, `build_adjudicated.py`, `output/` artifacts and seven-category lexicon are retained for development history. The default page does not load their funding ratios. The new model runner writes four-category candidates to a separate ignored directory. Its output must not be passed into the legacy seven-category aggregator.

Historical “expert” label layers are not documented human ground truth. Earlier agreement figures and mechanically checked quotations do not establish classifier accuracy. No external check exists; UKHRA/HRCS and cancer calibration remain outside the weekend scope.
