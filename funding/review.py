"""Version-bound human review, immutable first verdicts and publication gates."""
import argparse,json
from datetime import datetime
from .common import *
from .aggregate import aggregate,public_grant
from .classify import TAXONOMY_VERSION
EVAL=ROOT/'eval/funding'

def context(rows=None,labels=None,bench=None):
 rows=rows if rows is not None else load(DATA/'records.json',[])
 labels=labels if labels is not None else {x['grant_id']:x for x in load(DATA/'labels.json',[])}
 bench=bench if bench is not None else load(EVAL/'benchmark.json',{})
 reports={}
 for country,scope in PORTFOLIOS.items():
  rr=[r for r in rows if r['country']==country]
  # The 10 largest recorded awards include excluded records: large exclusions
  # can distort a ratio just as much as large inclusions.
  top=sorted(rr,key=lambda x:(-(x['amount_minor'] or 0),x['id']))[:10]
  summary=aggregate(rr,labels)
  version=digest({'scope':scope,'records':[(r['id'],r['version_hash'],labels[r['id']]['version_hash']) for r in rr],'aggregation':'funding-shares-v1','summary':summary})
  reports[country]={'country':country,**scope,'summary':summary,'version_hash':version,'top_award_ids':[r['id'] for r in top]}
 return {'rows':rows,'by_id':{r['id']:r for r in rows},'labels':labels,'benchmark':bench,'reports':reports}

def complete(v):
 if not isinstance(v,dict) or v.get('human_attested') is not True or not str(v.get('reviewer','')).strip():return False
 try:dt=datetime.fromisoformat(v['reviewed_at'].replace('Z','+00:00'))
 except (KeyError,TypeError,ValueError):return False
 return dt.tzinfo is not None

def valid_grant(v,r,label):
 return bool(complete(v) and v.get('source_version')==r['version_hash'] and v.get('review_version')==label['version_hash'] and v.get('category') in CATEGORIES and set(v.get('checks',{}))==set(SOURCE_CHECKS) and all(type(v['checks'][k]) is bool for k in SOURCE_CHECKS))

def source_pass(v):return all(v.get('checks',{}).get(k) is True for k in SOURCE_CHECKS)

def metrics(ctx,verdicts=None,approvals=None):
 verdicts=verdicts if verdicts is not None else load(EVAL/'verdicts.json',{})
 approvals=approvals if approvals is not None else load(EVAL/'report-approvals.json',{})
 parts={c:{'sample_size':30,'reviewed':0,'correct':0,'stale':0} for c in PORTFOLIOS}
 for item in ctx['benchmark'].get('records',[]):
  c=item['country'];r=ctx['by_id'].get(item['id']);label=ctx['labels'].get(item['id']);entry=verdicts.get(item['id'],{})
  first=entry.get('first');current=entry.get('current')
  frozen=(r and label and r['version_hash']==item['source_version'] and label['version_hash']==item['prediction_version'])
  if not frozen:
   parts[c]['stale']+=1;continue
  if first and valid_grant(first,r,label):
   parts[c]['reviewed']+=1
   parts[c]['correct']+=int(first['category']==label['category'] and source_pass(first))
 for c,p in parts.items():
  p['accuracy']=p['correct']/p['reviewed'] if p['reviewed'] else None
  p['passed']=p['reviewed']==30 and p['correct']>=27 and p['stale']==0
 total_reviewed=sum(p['reviewed'] for p in parts.values());correct=sum(p['correct'] for p in parts.values())
 overall={'sample_size':60,'reviewed':total_reviewed,'correct':correct,'accuracy':correct/total_reviewed if total_reviewed else None,'passed':total_reviewed==60 and correct>=54 and all(p['passed'] for p in parts.values())}
 for c,report in ctx['reports'].items():
  top_pass=0
  for rid in report['top_award_ids']:
   v=verdicts.get(rid,{}).get('current');r=ctx['by_id'][rid];label=ctx['labels'][rid]
   top_pass+=int(valid_grant(v,r,label) and source_pass(v) and v['category']==label['category'])
  approval=approvals.get(c,{})
  approved=bool(complete(approval) and approval.get('version_hash')==report['version_hash'] and all(approval.get('checks',{}).get(k) is True for k in REPORT_CHECKS))
  parts[c].update({'top_awards_checked':top_pass,'top_awards_required':len(report['top_award_ids']),'report_approved':approved,'publication_ready':overall['passed'] and top_pass==10 and approved})
 return {'target':.9,'overall':overall,'countries':parts,'sampling_note':ctx['benchmark'].get('sampling'),'benchmark_created_at':ctx['benchmark'].get('created_at')}

def packet(ctx):
 benchmark_ids=[x['id'] for x in ctx['benchmark']['records']]
 top_ids=list(dict.fromkeys(rid for r in ctx['reports'].values() for rid in r['top_award_ids']))
 ids=list(dict.fromkeys(benchmark_ids+top_ids));records=[]
 for rid in ids:
  r=ctx['by_id'][rid];p=ctx['labels'][rid]
  records.append({**public_grant(r),'review_version':p['version_hash'],'in_benchmark':rid in benchmark_ids,'top_award':rid in top_ids})
 return {'format':'longview-funding-review-v1','taxonomy_version':TAXONOMY_VERSION,'benchmark_version':ctx['benchmark']['population_version'],'created_at':now(),'categories':CATEGORIES,'source_checks':SOURCE_CHECKS,'report_checks':REPORT_CHECKS,'records':records,'reports':ctx['reports'],'status':metrics(ctx),'existing_verdicts':load(EVAL/'verdicts.json',{}),'existing_approvals':load(EVAL/'report-approvals.json',{}),'instructions':'Read the original source before choosing the objective. Predictions and selected passages are hidden. Full abstracts remain at the original source. Report estimates are unverified and for private review only.'}

def _import_export(path,ctx=None,eval_dir=EVAL,persist_db=True):
 ctx=ctx or context();body=load(path)
 if body.get('format')!='longview-funding-review-v1' or body.get('benchmark_version')!=ctx['benchmark'].get('population_version'):raise ValueError('Wrong or stale funding review packet')
 if body.get('simulation') is True:raise ValueError('Synthetic reviews cannot be imported')
 verdicts=load(eval_dir/'verdicts.json',{});approvals=load(eval_dir/'report-approvals.json',{});events=[]
 # Recover the materialised views from the immutable event log after a crash.
 hp=eval_dir/'history.jsonl'
 if hp.exists():
  for line in hp.read_text().splitlines():
   event=json.loads(line);key=event['id'];v=event['verdict']
   if event['kind']=='grant':
    entry=verdicts.setdefault(key,{});entry.setdefault('first',v);entry['current']=v
   else:approvals[key]=v
 allowed={x['id'] for x in ctx['benchmark']['records']}|{i for r in ctx['reports'].values() for i in r['top_award_ids']}
 for rid,v in body.get('verdicts',{}).items():
  if rid not in allowed or not valid_grant(v,ctx['by_id'][rid],ctx['labels'][rid]):raise ValueError('Unknown, incomplete or stale grant verdict: '+rid)
  entry=verdicts.setdefault(rid,{})
  entry.setdefault('first',v);entry['current']=v
  event={'kind':'grant','id':rid,'verdict':v};event['event_hash']=digest(event);events.append(event)
 for country,v in body.get('reports',{}).items():
  if country not in PORTFOLIOS or not complete(v) or v.get('version_hash')!=ctx['reports'][country]['version_hash'] or set(v.get('checks',{}))!=set(REPORT_CHECKS) or not all(type(x) is bool for x in v['checks'].values()):raise ValueError('Incomplete or stale report approval')
  approvals[country]=v;event={'kind':'report','id':country,'verdict':v};event['event_hash']=digest(event);events.append(event)
 history_path=eval_dir/'history.jsonl';existing=history_path.read_text().splitlines() if history_path.exists() else [];seen={json.loads(s)['event_hash'] for s in existing}
 fresh=[e for e in events if e['event_hash'] not in seen]
 eval_dir.mkdir(parents=True,exist_ok=True)
 # All validation happens before any write. History is never rewritten or erased.
 with history_path.open('a') as f:
  for event in fresh:f.write(json.dumps(event,ensure_ascii=False)+'\n')
 write_json(eval_dir/'verdicts.json',verdicts);write_json(eval_dir/'report-approvals.json',approvals)
 if persist_db:
  with db() as c:
   for event in fresh:
    if event['kind']=='grant':
     v=event['verdict'];c.execute('INSERT OR IGNORE INTO funding_review_events VALUES(?,?,?,?,?)',(event['event_hash'],event['id'],v['review_version'],v['reviewed_at'],json.dumps(v)))
 return {'imported_events':len(fresh),'metrics':metrics(ctx,verdicts,approvals)}

def import_export(path,ctx=None,eval_dir=EVAL,persist_db=True):
 import fcntl
 eval_dir.mkdir(parents=True,exist_ok=True)
 with (eval_dir/'.review.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  return _import_export(path,ctx,eval_dir,persist_db)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--import-file');args=parser.parse_args();ctx=context()
 if args.import_file:print(json.dumps(import_export(args.import_file,ctx),indent=2))
 else:
  write_json(DATA/'review-packet.json',packet(ctx));write_json(DATA/'report-preview.json',ctx['reports']);print(json.dumps(metrics(ctx),indent=2))
if __name__=='__main__':main()
