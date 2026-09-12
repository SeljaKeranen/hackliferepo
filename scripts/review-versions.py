import json
from pipeline.store import ROOT,COUNTRIES,finding_version
out={}
for c,(slug,_,_) in COUNTRIES.items():
    fs=json.loads((ROOT/f'eval/findings/{slug}.json').read_text())
    ps=json.loads((ROOT/f'eval/provenance/{slug}.json').read_text())
    out.update({f['id']:finding_version(f,ps[f['id']]) for f in fs})
print(json.dumps(out))
