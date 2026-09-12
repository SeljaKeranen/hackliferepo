"""Freeze a new, blinded 60-record benchmark; retain the existing benchmarks."""
import json,random
from .common import *
from .aggregate import public_grant
from .classify import TAXONOMY_VERSION,AGE

BENCH=ROOT/'eval/funding/benchmark.json'

def select_sample(rows,labels):
 rng=random.Random(42);selected=[]
 development={x['id'] for x in load(ROOT/'docs/funding/development-cases.json',[])}
 rows=[r for r in rows if r['id'] not in development]
 for country in PORTFOLIOS:
  pools={category:[r for r in rows if r['country']==country and labels[r['id']]['category']==category] for category in CATEGORIES}
  for pool in pools.values():pool.sort(key=lambda r:r['id']);rng.shuffle(pool)
  chosen=[]
  while len(chosen)<30:
   progressed=False
   for cat in CATEGORIES:
    if pools[cat] and len(chosen)<30:chosen.append(pools[cat].pop());progressed=True
   if not progressed:raise ValueError('Fewer than 30 records for a country benchmark')
  selected+=chosen
 return selected

def main():
 rows=load(DATA/'records.json');labels={l['grant_id']:l for l in load(DATA/'labels.json')}
 population=digest({'records':[r['version_hash'] for r in rows],'labels':[labels[r['id']]['version_hash'] for r in rows]})
 if BENCH.exists():
  existing=load(BENCH)
  if existing['population_version']!=population:raise ValueError('Frozen benchmark differs: preserve it and explicitly version a new benchmark; never overwrite it')
  print('Existing funding benchmark retained');return
 chosen=select_sample(rows,labels)
 meta={'created_at':now(),'taxonomy_version':TAXONOMY_VERSION,'population_version':population,'sample_size':60,'per_country':30,'target':.9,'seed':42,'excluded_development_ids':[x['id'] for x in load(ROOT/'docs/funding/development-cases.json',[])],'sampling':'Round-robin across predicted categories within country; shuffled with seed 42. First completed human verdict is retained. Stratified benchmark accuracy is not population accuracy.','records':[{'id':r['id'],'country':r['country'],'source_version':r['version_hash'],'prediction_version':labels[r['id']]['version_hash'],'title_has_ageing_keyword':bool(AGE.search(r['title']))} for r in chosen]}
 write_json(BENCH,meta)
 # Full text and predicted answer key stay local. The hosted packet is blinded.
 write_json(DATA/'benchmark-key.json',{r['id']:labels[r['id']]['category'] for r in chosen})
 write_json(DATA/'benchmark-records.json',[{**public_grant(r),'abstract':r['abstract'],'review_version':labels[r['id']]['version_hash']} for r in chosen])
 write_json(ROOT/'eval/funding/verdicts.json',{})
 write_json(ROOT/'eval/funding/report-approvals.json',{})
 print(json.dumps({'frozen':60,'without_ageing_title':sum(not x['title_has_ageing_keyword'] for x in meta['records'])}))
if __name__=='__main__':main()
