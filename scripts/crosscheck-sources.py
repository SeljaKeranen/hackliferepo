import json
from concurrent.futures import ThreadPoolExecutor,as_completed
from pipeline.research import search,results
from pipeline.store import ROOT,write_json,now
queries=[
('SE','site:riksdagen.se "2018/19:SoU3" "2018-12-12"'),
('SE','site:riksdagen.se "2021/22:SoU24" "2022-05-04"'),
('SE','site:regeringen.se "demensstrategi" "23 januari 2025"'),
('SE','site:regeringen.se "143,5 miljoner" "2023"'),
('US','site:fda.gov "Tobacco 21" "Dec. 20, 2019"'),
('US','site:fda.gov "Sept. 30" "under the age of 30" 2024'),
('US','site:nia.nih.gov "Aging Biology" "350,997"'),
('US','site:cms.gov "November 2, 2021" "one year" "MDPP"'),
('SG','site:moh.gov.sg "5 July 2023" "2 July 2023"'),
('SG','site:moh.gov.sg "30 June 2023" "Nutri-Grade"'),
('SG','site:moh.gov.sg "350 million" "22 May 2026"'),
('SG','site:moh.gov.sg "3.5 billion" "6 March 2024"')]
def run(item):
 c,q,i=item;provider='tavily' if i%2==0 else 'you.com'
 try:out=results(search(provider,q,3));status='results_returned' if out else 'no_results_returned'
 except Exception:out=[];status='retrieval_failed'
 return {'country':c,'query':q,'provider':provider,'status':status,'results':out,'checked_at':now(),'interpretation':'Discovery cross-check only; not a factual or human-review verdict.'}
with ThreadPoolExecutor(max_workers=3) as pool:out=[f.result() for f in as_completed([pool.submit(run,(c,q,i)) for i,(c,q) in enumerate(queries)])]
write_json(ROOT/'data/source-crosschecks.json',out)
summary=[{k:v for k,v in r.items() if k!='results'}|{'source_links':[s['url'] for s in r['results']]} for r in out]
write_json(ROOT/'docs/source-crosschecks.json',summary)
for r in out:print(r['country'],r['provider'],r['status'],len(r['results']),r['query'])
