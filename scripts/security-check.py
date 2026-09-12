"""Inspect only build artifacts; never print a credential or matching content."""
import json
from pathlib import Path
from pipeline.research import credentials
from pipeline.store import ROOT

def main():
 build=ROOT/'dist';assert build.is_dir()
 forbidden={'keys','.env','longview.sqlite','reviewer.key','sweden.verdicts.json'}
 values=[v.encode() for v in credentials().values() if v]
 key=ROOT/'outputs/reviewer.key'
 if key.exists():values.append(key.read_text().strip().encode())
 for path in build.rglob('*'):
  if not path.is_file():continue
  assert path.name not in forbidden,f'Forbidden file in build: {path.name}'
  payload=path.read_bytes()
  assert not any(v in payload for v in values),f'Secret detected in build file: {path.name}'
 evidence=json.loads((build/'release/evidence.json').read_text())
 assert all(f.get('review',{}).get('status')=='human_approved' for f in evidence['findings'])
 encrypted=json.loads((build/'review/packet.json').read_text());assert set(encrypted)=={'id','iv','ciphertext'}
 for path in (build/'assets').glob('*.js'):
  s=path.read_text();assert 'api.tavily.com' not in s and 'ydc-index.io' not in s
 print('Build security check passed: no provider/reviewer keys, no raw database or verdicts, encrypted review packet, approved-only public findings.')
if __name__=='__main__':main()
