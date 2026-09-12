"""Download documented public WDI data, preserving nulls and provenance."""
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from .store import DATA, ROOT, connect, now, write_json

INDICATORS = {
 'SP.DYN.LE00.IN': ('life_expectancy','years'),
 'SH.XPD.CHEX.GD.ZS': ('health_spending','% of GDP'),
 'NY.GDP.PCAP.PP.KD': ('gdp_ppp','constant 2021 international dollars'),
 'EN.ATM.PM25.MC.M3': ('pm25','micrograms per cubic metre'),
 'SH.PRV.SMOK': ('tobacco','% ages 15+, current tobacco use'),
}
AGE_GROUPS = [f'{a:02d}{a+4:02d}' for a in range(0,80,5)] + ['80UP']

def api(url):
    path=DATA/'wdi'/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    meta=path.with_suffix('.meta.json')
    if path.exists(): return json.loads(path.read_text()),json.loads(meta.read_text())
    last=None
    for attempt in range(3):
        try:
            r=requests.get(url,timeout=90);r.raise_for_status();payload=r.json()
            if not isinstance(payload,list) or len(payload)!=2 or not isinstance(payload[0],dict) or 'pages' not in payload[0]: raise ValueError('Unexpected WDI response')
            if int(payload[0]['pages'])>1: raise ValueError('Pagination would truncate observations')
            record={'url':url,'retrieved_at':now(),'hash':hashlib.sha256(r.content).hexdigest(),'revision_date':payload[0].get('lastupdated','metadata')}
            write_json(path,payload);write_json(meta,record);return payload,record
        except (requests.RequestException,ValueError) as exc:
            last=exc
            if attempt<2: time.sleep(attempt+1)
    raise RuntimeError(f'WDI download failed: {url} ({type(last).__name__})')

def download_indicator(code, countries='all', start=1990, end=2025):
    meta,_=api(f'https://api.worldbank.org/v2/indicator/{code}?format=json')
    info=meta[1][0]
    url=f'https://api.worldbank.org/v2/country/{countries}/indicator/{code}?format=json&date={start}:{end}&per_page=20000'
    payload,provenance=api(url)
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO datasets VALUES(?,?,?,?,?,?,?,?,?)',(code,info['name'],url,'CC BY 4.0',INDICATORS.get(code,('', '% of sex-specific population'))[1],info['sourceNote']+' Provider: '+info['sourceOrganization'],provenance['retrieved_at'],provenance['revision_date'],provenance['hash']))
        for row in payload[1] or []:
            country=row['countryiso3code']
            if len(country)!=3: continue
            value=row['value']
            if value is not None and not isinstance(value,(float,int)): raise ValueError('Non-numeric observation')
            db.execute('INSERT OR REPLACE INTO observations VALUES(?,?,?,?)',(code,country,int(row['date']),value))
    return {'indicator':code,'rows':len(payload[1] or []),'title':info['name'],'revision':provenance['revision_date']}

def main():
    countries,provenance=api('https://api.worldbank.org/v2/country?format=json&per_page=400')
    eligible={r['id']:{'name':r['name'],'income':r['incomeLevel']['value'],'region':r['region']['value']} for r in countries[1] if r['region']['id'] not in ('NA','') and r['region']['value']!='Aggregates'}
    write_json(DATA/'countries.json',eligible)
    jobs=[(code,'all',1990,2025) for code in INDICATORS]
    jobs += [(f'SP.POP.{age}.{sex}.5Y','SWE;USA;SGP',2023,2024) for age in AGE_GROUPS for sex in ('MA','FE')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(download_indicator,*job) for job in jobs]): print(json.dumps(future.result()),flush=True)
    with connect() as db:
        summary=[dict(r) for r in db.execute('SELECT dataset_id,MIN(year) first_year,MAX(year) last_year,COUNT(value) observed,COUNT(*) total FROM observations GROUP BY dataset_id')]
    write_json(ROOT/'docs/data-coverage.json',{'retrieved_at':now(),'eligible_countries':len(eligible),'series':summary})

if __name__=='__main__': main()
