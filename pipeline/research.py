"""Budgeted, cached discovery and primary-source retrieval.

Search example: python -m pipeline.research search you.com 'query'
Fetch example: python -m pipeline.research fetch https://official.example/page
Every attempted provider request is reserved transactionally before the network call.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import requests
from bs4 import BeautifulSoup
from .store import DATA, ROOT, connect, now, write_json

CAP = 500
PLANNING_REQUESTS = 7

def credentials():
    result = {'you.com': os.environ.get('YOU_API_KEY'), 'tavily': os.environ.get('TAVILY_API_KEY')}
    path = ROOT / 'keys'
    if path.exists():
        lines = [s.strip() for s in path.read_text().splitlines() if s.strip()]
        for i, line in enumerate(lines[:-1]):
            label = line.lower().rstrip(':')
            if label in result and not result[label]: result[label] = lines[i+1]
    return result

def search(provider, query, count=5):
    cache = DATA / 'search' / (hashlib.sha256(f'{provider}:{query}:{count}'.encode()).hexdigest()+'.json')
    if cache.exists(): return json.loads(cache.read_text())
    key = credentials().get(provider)
    if not key: raise RuntimeError(f'No credential for {provider}; no request made')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        used = db.execute('SELECT COUNT(*) FROM research_runs').fetchone()[0] + PLANNING_REQUESTS
        if used >= CAP: raise RuntimeError('Research request cap reached')
        run_id = db.execute('INSERT INTO research_runs(provider,operation,query,requested_at,status) VALUES(?,?,?,?,?)', (provider,'search',query,now(),'reserved')).lastrowid
    try:
        if provider == 'you.com':
            r = requests.post('https://ydc-index.io/v1/search', headers={'X-API-Key':key}, json={'query':query,'count':count},timeout=60)
        elif provider == 'tavily':
            r = requests.post('https://api.tavily.com/search', headers={'Authorization':f'Bearer {key}'}, json={'query':query,'max_results':count,'search_depth':'basic','include_answer':False,'include_usage':True},timeout=60)
        else: raise ValueError('Unknown provider')
        r.raise_for_status()
        payload = r.json()
        write_json(cache,payload)
        with connect() as db:
            db.execute('UPDATE research_runs SET status=?,response_hash=? WHERE id=?',('complete',hashlib.sha256(r.content).hexdigest(),run_id))
        return payload
    except Exception as exc:
        # Never include request headers, keys or response body in logs.
        with connect() as db: db.execute('UPDATE research_runs SET status=?,error=? WHERE id=?',('failed',type(exc).__name__,run_id))
        raise RuntimeError(f'{provider} request failed: {type(exc).__name__}') from None

def results(payload):
    found = payload.get('results', [])
    if isinstance(found,dict): found = found.get('web',[])
    return [{'title':r.get('title',''),'url':r.get('url',''),'summary':r.get('content') or r.get('description') or ' '.join(r.get('snippets',[]))} for r in found]

def canonical(url):
    p=urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username: raise ValueError('A public HTTPS source URL is required')
    return urlunsplit((p.scheme,p.netloc.lower(),p.path,p.query,''))

def fetch(url, force=False):
    url = canonical(url)
    source_id = hashlib.sha256(url.encode()).hexdigest()[:20]
    meta_path = DATA / 'sources' / (source_id+'.json')
    if meta_path.exists() and not force: return json.loads(meta_path.read_text())
    r = requests.get(url, timeout=60, headers={'User-Agent':'LongviewHackathon/0.1 (public-policy source verification)'})
    retrieved=now()
    r.raise_for_status()
    if 'pdf' in r.headers.get('content-type',''):
        raise ValueError('PDF needs explicit page-aware extraction; do not treat binary as evidence')
    soup = BeautifulSoup(r.content,'html.parser')
    title = soup.title.get_text(' ',strip=True) if soup.title else urlsplit(url).hostname
    for tag in soup(['script','style','nav','footer','header']): tag.decompose()
    text = soup.get_text('\n',strip=True)
    text = re.sub(r'\n{3,}','\n\n',text)
    snapshot_hash = hashlib.sha256(r.content).hexdigest()
    snapshot_dir = DATA / 'source-versions'; snapshot_dir.mkdir(parents=True,exist_ok=True)
    (snapshot_dir / (snapshot_hash+'.html')).write_bytes(r.content)
    text_path = DATA / 'sources' / (source_id+'-'+snapshot_hash[:12]+'.txt');text_path.parent.mkdir(parents=True,exist_ok=True);text_path.write_text(text)
    date_match = re.search(r'\b(?:20\d{2}-\d{2}-\d{2})\b',text)
    source={'id':source_id,'canonical_url':url,'resolved_url':r.url,'publisher':urlsplit(url).hostname,'title':title,'retrieved_at':retrieved,'content_hash':hashlib.sha256(r.content).hexdigest(),'http_status':r.status_code,'text_path':str(text_path.relative_to(ROOT)),'publication_date':None,'detected_date_candidate':date_match.group() if date_match else None}
    with connect() as db:
        db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,retrieved_at=excluded.retrieved_at,content_hash=excluded.content_hash,http_status=excluded.http_status,text_path=excluded.text_path', tuple(source[k] for k in ['id','canonical_url','publisher','title','retrieved_at','content_hash','http_status','text_path','publication_date']))
    write_json(meta_path,source)
    return source

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    s=sub.add_parser('search');s.add_argument('provider',choices=['you.com','tavily']);s.add_argument('query')
    f=sub.add_parser('fetch');f.add_argument('url')
    a=parser.parse_args()
    print(json.dumps(results(search(a.provider,a.query)) if a.command=='search' else fetch(a.url),indent=2,ensure_ascii=False))

def extract(url):
    """Provider extraction fallback; fingerprint extracted text, not an unseen HTTP body."""
    cache=DATA/'extract'/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    if cache.exists():return json.loads(cache.read_text())
    key=credentials().get('tavily')
    if not key:raise RuntimeError('No Tavily credential')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT COUNT(*) FROM research_runs').fetchone()[0]+PLANNING_REQUESTS>=CAP:raise RuntimeError('Research cap reached')
        rid=db.execute('INSERT INTO research_runs(provider,operation,query,requested_at,status) VALUES(?,?,?,?,?)',('tavily','extract',url,now(),'reserved')).lastrowid
    try:
        r=requests.post('https://api.tavily.com/extract',headers={'Authorization':f'Bearer {key}'},json={'urls':[url],'extract_depth':'basic','format':'text','include_usage':True},timeout=90)
        r.raise_for_status();payload=r.json()
        if not payload.get('results'):raise ValueError('No extracted source text')
        text=payload['results'][0]['raw_content']
        source_id=hashlib.sha256(canonical(url).encode()).hexdigest()[:20]
        text_path=DATA/'sources'/(source_id+'.txt');text_path.parent.mkdir(exist_ok=True,parents=True);text_path.write_text(text)
        source={'id':source_id,'canonical_url':canonical(url),'resolved_url':url,'publisher':urlsplit(url).hostname,'title':payload['results'][0].get('title') or text.splitlines()[0][:200],'retrieved_at':now(),'content_hash':hashlib.sha256(text.encode()).hexdigest(),'http_status':0,'text_path':str(text_path.relative_to(ROOT)),'publication_date':None,'retrieval_method':'tavily_extract','hash_basis':'provider-extracted text; origin HTTP status not independently established'}
        with connect() as db:
            db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?,?,?,?)',tuple(source[k] for k in ['id','canonical_url','publisher','title','retrieved_at','content_hash','http_status','text_path','publication_date']))
            db.execute('UPDATE research_runs SET status=?,response_hash=? WHERE id=?',('complete',hashlib.sha256(r.content).hexdigest(),rid))
        write_json(cache,source);return source
    except Exception as e:
        with connect() as db:db.execute('UPDATE research_runs SET status=?,error=? WHERE id=?',('failed',type(e).__name__,rid))
        raise RuntimeError('Source extraction failed: '+type(e).__name__) from None
