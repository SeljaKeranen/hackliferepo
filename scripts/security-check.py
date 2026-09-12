"""Scan the static build and nested downloadable archives without printing secrets."""
import io,json,os
from pathlib import Path
from zipfile import ZipFile,is_zipfile
from pipeline.research import credentials
from pipeline.store import ROOT

def main():
 build=ROOT/'dist';assert build.is_dir()
 forbidden={'keys','.env','longview.sqlite','reviewer.key','funding-reviewer.key','sweden.verdicts.json','review-packet.json','benchmark-key.json','records.json'}
 values=[v.encode() for v in credentials().values() if v]
 for key in ['reviewer.key','funding-reviewer.key']:
  p=ROOT/'outputs'/key
  if p.exists():values.append(p.read_text().strip().encode())
 values += [v.encode() for k,v in os.environ.items() if len(v)>16 and any(t in k.upper() for t in ['API_KEY','ACCESS_TOKEN','AUTH_TOKEN'])]
 inspected=0
 def inspect(name,payload,depth=0):
  nonlocal inspected
  inspected+=1
  assert Path(name).name not in forbidden,f'Forbidden file in build: {name}'
  assert not any(v in payload for v in values),f'Secret detected in build artifact: {name}'
  if depth<3 and is_zipfile(io.BytesIO(payload)):
   with ZipFile(io.BytesIO(payload)) as z:
    for entry in z.infolist():
     if not entry.is_dir():inspect(name+'!'+entry.filename,z.read(entry),depth+1)
 for path in build.rglob('*'):
  if path.is_file():inspect(str(path.relative_to(build)),path.read_bytes())
 for packet_path in ['review/packet.json','review/funding/packet.json']:
  p=build/packet_path
  if p.exists():assert set(json.loads(p.read_text()))=={'id','iv','ciphertext'}
 for path in (build/'assets').glob('*.js'):
  s=path.read_text();assert 'api.tavily.com' not in s and 'ydc-index.io' not in s
 # Every current and archived funding release must enforce the same masking rule.
 for path in (build/'funding/releases').glob('*.json'):
  release=json.loads(path.read_text());ledger=json.loads((build/'funding/ledgers'/(release['ledger_hash'][:16]+'.json')).read_text())
  for c,r in release['reports'].items():
   if not r['publication_ready']:
    assert r['summary'] is None
    assert all(g['classification'] is None for g in ledger['records'] if g['country']==c)
  assert all('abstract' not in g and 'public_health_relevance' not in g for g in ledger['records'])
 legacy=build/'release/evidence.json'
 if legacy.exists():assert all(f.get('review',{}).get('status')=='human_approved' for f in json.loads(legacy.read_text())['findings'])
 archive=build/'downloads/longview-offline.zip'
 if archive.exists():
  with ZipFile(archive) as z:assert not any(n.startswith('review/') for n in z.namelist())
 print(f'Build security check passed: {inspected} files/archive members inspected; no provider or reviewer keys, no raw database/abstracts, encrypted reviewer packets, pending funding estimates masked.')
if __name__=='__main__':main()
