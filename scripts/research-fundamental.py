from concurrent.futures import ThreadPoolExecutor,as_completed
from pipeline.research import search,results,fetch,extract
from pipeline.store import ROOT,write_json
queries=[
('US','site:nia.nih.gov Division of Aging Biology fiscal year 2024 budget research funding'),
('US','site:nia.nih.gov congressional justification 2025 aging biology budget basic research'),
('SE','site:vr.se åldrandets biologi grundforskning finansiering 2024'),
('SE','site:forte.se forskning åldrande grundforskning biologi finansiering'),
('SG','Singapore fundamental ageing biology research government funding healthy longevity programme budget NRF'),
('SG','site:nmrc.gov.sg healthy longevity research 2024 budget basic ageing')]
def run(item):
 c,q=item
 return {'country':c,'query':q,'results':results(search('you.com',q,5))}
with ThreadPoolExecutor(max_workers=3) as pool:
 out=[f.result() for f in as_completed([pool.submit(run,item) for item in queries])]
write_json(ROOT/'data/fundamental-discovery.json',out)
for row in out:
 print(row['country'],row['query'])
 for i,r in enumerate(row['results']):print(i,r['title'][:110],r['url'],r['summary'][:350])
