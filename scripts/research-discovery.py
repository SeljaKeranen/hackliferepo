import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pipeline.research import search, results
from pipeline.store import ROOT, write_json, connect, now
queries={
'SE':[
('legislation','site:riksdagen.se ny lag tobak liknande produkter 2018/19 SoU3 beslut 12 december 2018'),
('strategy','site.regeringen.se nationell demensstrategi 2025 21 januari'),
('policy','site:regeringen.se förebyggande hälsa äldre 2024 2025 mat ensamhet'),
('funding','site:forte.se 2025 äldreomsorg nordiska forskningsprojekt finansiering'),
('political statement','site:regeringen.se äldreomsorg minister 2024 Japan Sydkorea'),
('strategy','site:regeringen.se 2018 god jämlik hälsa folkhälsopolitik proposition'),
('legislation','site:riksdagen.se fast omsorgskontakt hemtjänsten 2022 beslut'),
('funding','site:regeringen.se 2023 2024 ofrivillig ensamhet äldre statsbidrag')],
'US':[
('legislation','site:fda.gov Tobacco 21 December 20 2019 law'),
('legislation','site:fda.gov August 29 2024 final rule tobacco age September 30'),
('strategy','site:health.gov Healthy People 2030 launched August 18 2020'),
('policy','site:cms.gov Medicare diabetes prevention program April 1 2018'),
('funding','site:nih.gov 2024 Alzheimers research funding billion'),
('political statement','site:hhs.gov surgeon general advisory loneliness May 2023'),
('policy','site:epa.gov 2024 final PM2.5 standard 9 micrograms February 7'),
('strategy','site:hhs.gov 2022 national strategy support family caregivers September 21')],
'SG':[
('strategy','site:moh.gov.sg Healthier SG white paper 2022 October 4'),
('policy','site:moh.gov.sg Healthier SG launched July 5 2023'),
('funding','site:moh.gov.sg Age Well SG 3.5 billion 2024 decade'),
('strategy','site:moh.gov.sg 2023 action plan successful ageing launched January 30'),
('legislation','site:moh.gov.sg tobacco minimum legal age 21 January 1 2021'),
('political statement','site:moh.gov.sg war on diabetes 2016 April 13'),
('legislation','site:moh.gov.sg Nutri Grade December 30 2022 beverages'),
('policy','site:moh.gov.sg 2023 Nutri Grade freshly prepared beverages December 30')]
}

def run(item):
    country,category,q,i=item
    provider='you.com' if i%2==0 else 'tavily'
    try: found=results(search(provider,q,4));status='searched' if found else 'no_results'
    except RuntimeError as e: found=[];status='retrieval_failed'
    with connect() as db:
        db.execute('INSERT INTO coverage VALUES(?,?,?,?,?,?) ON CONFLICT(country,classification) DO UPDATE SET query_count=query_count+1,status=excluded.status,updated_at=excluded.updated_at',(country,category,status,1,'Bounded discovery. Search results alone do not establish a finding or absence.',now()))
    return {'country':country,'classification':category,'query':q,'provider':provider,'status':status,'results':found}

items=[(country,cat,q,i) for country,qs in queries.items() for i,(cat,q) in enumerate(qs)]
with ThreadPoolExecutor(max_workers=3) as pool:
    out=[]
    for f in as_completed([pool.submit(run,item) for item in items]):
        row=f.result();out.append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
write_json(ROOT/'data/discovery.json',out)
