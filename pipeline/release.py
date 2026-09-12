"""Export a frozen read-only release. Unreviewed policy claims never enter public/."""
import argparse
import json
from pathlib import Path
from .store import ROOT,COUNTRIES,CHECKS,connect,write_json,now,digest,approved,finding_version,current_source_matches
from .research import PLANNING_REQUESTS,CAP

def load(path,default):return json.loads(path.read_text()) if path.exists() else default

def main(strict=False):
    approved_findings=[];counts={};reviewed=0;correct=0;pending=0
    benchmark=load(ROOT/'eval/benchmark.json',{'versions':{}})
    first={}
    for c,(slug,_,name) in COUNTRIES.items():
        fs=load(ROOT/f'eval/findings/{slug}.json',[]);ps=load(ROOT/f'eval/provenance/{slug}.json',{});vs=load(ROOT/f'eval/verdicts/{slug}.verdicts.json',{})
        history=ROOT/f'eval/verdicts/{slug}.history.jsonl'
        if history.exists():
            for line in history.read_text().splitlines():
                v=json.loads(line);fid=v['finding_id']
                if v.get('version_hash')==benchmark['versions'].get(fid) and v.get('reviewed') and v.get('reviewer','').strip():
                    from datetime import datetime
                    if fid not in first or datetime.fromisoformat(v['reviewed_at'].replace('Z','+00:00'))<datetime.fromisoformat(first[fid]['reviewed_at'].replace('Z','+00:00')):first[fid]=v
        n=0
        for f in fs:
            prov=ps.get(f['id'],{});v=vs.get(f['id'])
            with connect() as source_db:
                source_matches=current_source_matches(prov,source_db)
            if approved(f,prov,v) and source_matches:
                # Reviewer identity stays local; public users see timestamp and evidence version.
                approved_findings.append(dict(f,provenance=prov,review={'status':'human_approved','reviewed_at':v['reviewed_at'],'version_hash':v['version_hash']}));n+=1
        counts[c]={'name':name,'candidates':len(fs),'approved':n,'withheld':len(fs)-n}
        pending+=len(fs)-n
    reviewed=len(first);correct=sum(v.get('correct') is True and all(v['checks'].get(k) is True for k in CHECKS) for v in first.values())
    total=len(benchmark['versions']);benchmark_complete=reviewed==total and total>0
    accuracy=correct/reviewed if reviewed else None
    if strict and (pending or not benchmark_complete or accuracy<.9):raise RuntimeError('Release gate failed: complete human review and >=90% initial benchmark accuracy required')
    with connect() as db:
        used=db.execute('SELECT COUNT(*) FROM research_runs').fetchone()[0]+PLANNING_REQUESTS
        coverage=[dict(r) for r in db.execute('SELECT * FROM coverage ORDER BY country,classification')]
        source_count=db.execute('SELECT COUNT(*) FROM sources').fetchone()[0]
        failed=db.execute("SELECT COUNT(*) FROM research_runs WHERE status='failed'").fetchone()[0]
        funding_rows=[dict(r) for r in db.execute('SELECT * FROM funding_observations')] if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='funding_observations'").fetchone() else []
    packet={'created_at':now(),'status':'reviewed_release' if pending==0 and benchmark_complete and accuracy>=.9 else 'human_review_pending','findings':approved_findings,'countries':counts,'coverage':coverage,'benchmark':{'reviewed':reviewed,'correct':correct,'sample_size':total,'accuracy':accuracy,'complete':benchmark_complete,'target':.9,'method':benchmark.get('sampling','')},'research':{'requests_used':used,'request_cap':CAP,'planning_requests':PLANNING_REQUESTS,'primary_documents':source_count,'failed_provider_attempts':failed},'coverage_note':'A bounded national-policy search across five categories. Unsearched countries and failed retrievals never mean no policy exists. High source confidence does not mean high policy effectiveness.'}
    public_ids={f['id'] for f in approved_findings}
    packet['funding']={'status':'comparability_not_established','national_fundamental_totals':{c:None for c in COUNTRIES},'approved_programme_records':[r for r in funding_rows if r['finding_id'] in public_ids],'candidate_programme_counts':{c:sum(r['country']==c for r in funding_rows) for c in COUNTRIES},'note':'Programme budgets, annual outturns and multi-year commitments require matching scope and periods before comparison.'}
    packet['release_id']=digest({k:v for k,v in packet.items() if k!='created_at'})[:12]
    write_json(ROOT/'public/release/evidence.json',packet)
    manifest={'created_at':now(),'evidence_release':packet['release_id'],'quantitative_release':load(ROOT/'public/release/quantitative.json',{}).get('release_id'),'files':{p.name:digest(load(p,{})) for p in (ROOT/'public/release').glob('*.json') if p.name!='manifest.json'}}
    write_json(ROOT/'public/release/manifest.json',manifest)
    print(json.dumps({'status':packet['status'],'approved':len(approved_findings),'withheld':pending,'initial_accuracy':accuracy,'requests':used}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--strict',action='store_true');a=p.parse_args();main(a.strict)
