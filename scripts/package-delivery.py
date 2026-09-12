"""Publish the generated deck/recording; --offline additionally packages the built app."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
def main(offline=False):
 target=ROOT/'public/downloads';target.mkdir(parents=True,exist_ok=True)
 evidence=json.loads((ROOT/'public/release/evidence.json').read_text())
 quantitative=json.loads((ROOT/'public/release/quantitative.json').read_text())
 deck=json.loads((ROOT/'outputs/deck-manifest.json').read_text())
 assert deck['evidence_release']==evidence['release_id'], 'Regenerate the slides for this evidence release'
 assert deck['quantitative_release']==quantitative['release_id'], 'Regenerate the slides for this model release'
 files=['longview-three-slides.pptx','longview-three-slides.pdf','longview-demo.webm']
 for name in files:
  source=ROOT/'outputs'/name;assert source.stat().st_size>1000
  shutil.copy2(source,target/name)
 if offline:
  build=ROOT/'dist';assert (build/'index.html').exists(), 'Run npm run build first'
  name='longview-offline.zip';files.append(name)
  with ZipFile(target/name,'w',ZIP_DEFLATED) as archive:
   for source in build.rglob('*'):
    rel=source.relative_to(build)
    if source.is_file() and rel.parts[0] not in {'downloads','review'}:
     archive.write(source,rel)
   archive.write(ROOT/'scripts/run-offline.py','run-offline.py')
   archive.writestr('README.txt','Longview offline demo\n\nUnzip this folder. With Python 3 installed, run:\n  python3 run-offline.py\nThen open the local URL printed by the script on that computer (usually http://127.0.0.1:8000). A free port is selected if 8000 is occupied. No internet is required for the model or bundled data. Original-source links require internet.\n\nThis is a research prototype, not a clinical or causal model. Human policy review is pending in this release. The 90% evidence-verification target is not yet measured. See Data & method in the app for country failures and data limitations.\n\nSlides and the video are separate downloads on the hosted app. The private reviewer packet is excluded from this offline copy.\n')
 manifest={'evidence_release':evidence['release_id'],'quantitative_release':quantitative['release_id'],'slides':3,'recording':'captioned real browser interaction; no audio','recording_verification':json.loads((ROOT/'outputs/recording-verification.json').read_text()),'files':{name:{'bytes':(target/name).stat().st_size,'sha256':hashlib.sha256((target/name).read_bytes()).hexdigest()} for name in files}}
 (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 if offline:shutil.copytree(target,ROOT/'dist/downloads',dirs_exist_ok=True)
 print(json.dumps(manifest,indent=2))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');main(parser.parse_args().offline)
