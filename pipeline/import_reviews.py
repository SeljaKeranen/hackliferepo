"""Import a teammate's browser-exported human verdicts; fail on stale versions."""
import argparse,json
from datetime import datetime,timezone
from .store import ROOT,COUNTRIES,CHECKS,finding_version,write_json,connect

def validated(v,versions):
    fid=v.get('finding_id')
    if fid not in versions:raise ValueError('Unknown finding id')
    if v.get('version_hash')!=versions[fid]:raise ValueError('Stale evidence version: '+fid)
    if not isinstance(v.get('reviewer'),str) or not v['reviewer'].strip():raise ValueError('Human reviewer is required')
    checks=v.get('checks',{})
    if set(checks)!=set(CHECKS) or any(x is not True and x is not False and x is not None for x in checks.values()):raise ValueError('Invalid checks')
    reviewed=all(checks[k] is not None for k in CHECKS);correct=reviewed and all(checks[k] is True for k in CHECKS)
    if v.get('reviewed') is not reviewed or v.get('correct') is not correct:raise ValueError('Inconsistent verdict flags')
    stamp=datetime.fromisoformat(v['reviewed_at'].replace('Z','+00:00'))
    if stamp.tzinfo is None or stamp>datetime.now(timezone.utc):raise ValueError('Invalid review timestamp')
    return v

def main(path):
    payload=json.loads(path.read_text())
    if payload.get('format')!='longview-human-review-v1':raise ValueError('Unsupported review format')
    versions={};slugs={}
    for c,(slug,_,_) in COUNTRIES.items():
        fs=json.loads((ROOT/f'eval/findings/{slug}.json').read_text());ps=json.loads((ROOT/f'eval/provenance/{slug}.json').read_text())
        for f in fs:versions[f['id']]=finding_version(f,ps[f['id']]);slugs[f['id']]=slug
    current=[validated(v,versions) for fid,v in payload['verdicts'].items() if fid==v.get('finding_id')]
    if len(current)!=len(payload['verdicts']):raise ValueError('Mismatched verdict key')
    history=[validated(v,versions) for v in payload.get('history',[]) if v.get('reviewed')]
    for v in current:
        if v['reviewed'] and not any(h==v for h in history):
            raise ValueError('Completed verdict is missing its audit-history event')
    # Complete all validation before mutating local review evidence.
    for c,(slug,_,_) in COUNTRIES.items():
        vp=ROOT/f'eval/verdicts/{slug}.verdicts.json';old=json.loads(vp.read_text()) if vp.exists() else {}
        for v in current:
            if slugs[v['finding_id']]==slug:
                previous=old.get(v['finding_id'])
                if not previous or datetime.fromisoformat(v['reviewed_at'].replace('Z','+00:00'))>=datetime.fromisoformat(previous['reviewed_at'].replace('Z','+00:00')):old[v['finding_id']]=v
        write_json(vp,old)
        hp=ROOT/f'eval/verdicts/{slug}.history.jsonl'
        existing=hp.read_text().splitlines() if hp.exists() else []
        additions=[json.dumps(v,ensure_ascii=False,sort_keys=True) for v in history if slugs[v['finding_id']]==slug]
        prior={json.dumps(json.loads(s),sort_keys=True,ensure_ascii=False) for s in existing}
        with hp.open('a') as out:
            for line in additions:
                if line not in prior:out.write(line+'\n');prior.add(line)
    with connect() as db:
        for v in history:
            if not db.execute('SELECT 1 FROM reviews WHERE finding_id=? AND version_hash=? AND reviewer=? AND reviewed_at=?',(v['finding_id'],v['version_hash'],v['reviewer'],v['reviewed_at'])).fetchone():
                db.execute('INSERT INTO reviews(finding_id,version_hash,reviewer,reviewed_at,checks,correct,note) VALUES(?,?,?,?,?,?,?)',(v['finding_id'],v['version_hash'],v['reviewer'],v['reviewed_at'],json.dumps(v['checks']),int(v['correct']),v.get('note','')))
    print(f'Imported {len(current)} human verdicts; {len(history)} completed history events. Rebuild the frozen release next.')

if __name__=='__main__':
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('file',type=Path);a=p.parse_args();main(a.file)
