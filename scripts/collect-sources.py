import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pipeline.research import fetch
from pipeline.store import ROOT, write_json
rows=json.loads((ROOT/'data/discovery.json').read_text())
selection={0:[1,2,3],1:[0],2:[0,3],3:[0],5:[1],6:[0,1],7:[0],8:[1],9:[0],10:[0,3],12:[2],13:[0],15:[0,1,2],16:[0,1],17:[1],18:[0],20:[1],21:[1],22:[0,1,3],23:[1]}
items=[]
for n,indices in selection.items():
 for i in indices:
  row=rows[n]['results'][i]
  items.append({'country':rows[n]['country'],'url':row['url']})
items += [{'country':'SE','url':f['source_url']} for f in json.loads((ROOT/'eval/findings/sweden.json').read_text()) if f['id'] in ['se-003','se-008','se-009','se-014']]
# Canonical decision page rather than proposal-only HTML.
for item in items:
 if 'ny-lag-om-tobak-och-liknande-produkter_H601' in item['url']: item['url']='https://www.riksdagen.se/sv/dokument-och-lagar/dokument/betankande/ny-lag-om-tobak-och-liknande-produkter_h601sou3/'
 if 'en-fast-omsorgskontakt-i-hemtjansten_h901sou24/html' in item['url']: item['url']='https://www.riksdagen.se/sv/dokument-och-lagar/dokument/betankande/en-fast-omsorgskontakt-i-hemtjansten_h901sou24/'

def run(item):
 try: return dict(item,source=fetch(item['url']),status='retrieved')
 except Exception as e: return dict(item,status='retrieval_failed',error=type(e).__name__)
with ThreadPoolExecutor(max_workers=4) as pool:
 out=[]
 for future in as_completed([pool.submit(run,item) for item in items]):
  row=future.result();out.append(row);print(json.dumps(row),flush=True)
write_json(ROOT/'data/source-index.json',out)
