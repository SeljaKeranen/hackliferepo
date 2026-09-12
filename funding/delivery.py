"""Publish release-matched funding slides, recording and an offline fallback."""
import argparse,hashlib,json,shutil,subprocess,re
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from .common import ROOT,load

def main(offline=False):
 r=load(ROOT/'public/funding/current.json');deck=load(ROOT/'outputs/deck-manifest.json');video=load(ROOT/'outputs/recording-verification.json')
 assert deck['funding_release']==video['funding_release']==r['release_id'],'Regenerate the slides and recording for this funding release'
 assert deck['slides']==3 and video['captions'] and not video['synthetic_reviews'] and video.get('complete') is True and video['cues']>=12
 ffmpeg=shutil.which('ffmpeg') or next(iter((Path.home()/'.cache/ms-playwright').glob('ffmpeg-*/ffmpeg-linux')),None)
 if not ffmpeg:raise RuntimeError('Install ffmpeg or the Playwright ffmpeg binary to verify the recording')
 probe=subprocess.run([str(ffmpeg),'-y','-ss','40','-i',str(ROOT/'outputs/longview-demo.webm'),'-frames:v','1',str(ROOT/'outputs/funding-video-frame.png')],capture_output=True,text=True,check=True)
 match=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',probe.stderr)
 assert match,'Video duration unavailable'
 h,m,s=map(float,match.groups());video['duration_seconds']=h*3600+m*60+s
 video['decoded_frame_seconds']=40;video['frame_decode_passed']=True
 assert 80<=video['duration_seconds']<=120,'Unexpected fallback duration'
 (ROOT/'outputs/recording-verification.json').write_text(json.dumps(video,indent=2)+'\n')
 target=ROOT/'public/downloads';target.mkdir(parents=True,exist_ok=True)
 files=['longview-three-slides.pptx','longview-three-slides.pdf','longview-demo.webm']
 for name in files:
  source=ROOT/'outputs'/name;assert source.stat().st_size>1000;shutil.copy2(source,target/name)
 if offline:
  build=ROOT/'dist';assert (build/'index.html').exists()
  assert load(build/'funding/current.json')['release_id']==r['release_id']
  name='longview-offline.zip';files.append(name)
  with ZipFile(target/name,'w',ZIP_DEFLATED) as archive:
   for source in build.rglob('*'):
    rel=source.relative_to(build)
    # The old forecast payload is retained in the repository, but not bundled
    # with the new public funding fallback. Private packets stay out too.
    if source.is_file() and rel.parts[0] not in {'downloads','review','release'}:archive.write(source,rel)
   archive.write(ROOT/'scripts/run-offline.py','run-offline.py')
   archive.writestr('README.txt',f'Longview funding report — release {r["release_id"]}\n\nUnzip, then with Python 3 run:\n  python3 run-offline.py\nOpen the address printed by the server on that computer. The public funding report and source ledger need no internet. Original-source links require internet.\n\nHuman verification: {r["review"]["overall"]["reviewed"]}/60 reviewed. The numerical estimates remain pending until all human review requirements pass. No private reviewer packet is included. This is a research-funding communication prototype, not a national ranking or clinical tool.\n')
 manifest={'funding_release':r['release_id'],'slides':3,'human_reviewed':r['review']['overall']['reviewed'],'recording':video,'files':{n:{'bytes':(target/n).stat().st_size,'sha256':hashlib.sha256((target/n).read_bytes()).hexdigest()} for n in files}}
 (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 if offline:shutil.copytree(target,ROOT/'dist/downloads',dirs_exist_ok=True)
 print(json.dumps({'funding_release':r['release_id'],'slides':3,'files':{n:v['bytes'] for n,v in manifest['files'].items()}},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');main(p.parse_args().offline)
