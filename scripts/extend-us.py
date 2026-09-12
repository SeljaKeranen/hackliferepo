import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pipeline.research import fetch,extract,search,results
from pipeline.store import ROOT,write_json
p=ROOT/'data/source-index.json';rows=json.loads(p.read_text())
urls=[
'https://acl.gov/news-and-events/announcements/hhs-delivers-first-national-strategy-support-family-caregivers-0',
'https://www.cms.gov/newsroom/fact-sheets/final-policies-medicare-diabetes-prevention-program-mdpp-expanded-model-calendar-year-2022-medicare',
'https://www.cms.gov/newsroom/fact-sheets/proposed-policies-medicare-diabetes-prevention-program-expanded-model-calendar-year-2018-physician',
'https://www.hhs.gov/press-room/hhs-backs-ai-innovation-for-americas-caregivers.html']
def run(url):
 try:s=fetch(url)
 except Exception:
  try:s=extract(url)
  except Exception as e:return {'country':'US','url':url,'status':'retrieval_failed','error':type(e).__name__}
 return {'country':'US','url':url,'status':'retrieved','source':s}
with ThreadPoolExecutor(max_workers=3) as pool:
 for f in as_completed([pool.submit(run,r['url']) for r in rows if r['status']=='retrieval_failed']+[pool.submit(run,u) for u in urls]):
  r=f.result()
  existing=next((i for i,v in enumerate(rows) if v['url']==r['url']),None)
  if existing is None:rows.append(r)
  else:rows[existing]=r
  print(json.dumps(r),flush=True)
write_json(p,rows)
