"""Collect complete portfolios with cached, resumable official API requests."""
import argparse, csv, io, json, re, time, hashlib
from pathlib import Path
import requests
from .common import DATA, ROOT, YEAR, PORTFOLIOS, load, now, digest, write_json, cents, source_version, db

SESSION=requests.Session()
SESSION.headers['User-Agent']='LongviewFunding/1.0 (public research award analysis)'

def request_json(url, payload=None, params=None, headers=None):
 key=digest({'url':url,'payload':payload,'params':params});p=DATA/'api'/(key+'.json')
 if p.exists():return load(p)
 for attempt in range(3):
  try:
   r=SESSION.post(url,json=payload,timeout=90) if payload is not None else SESSION.get(url,params=params,headers=headers,timeout=90)
   r.raise_for_status();body=r.json()
   envelope={'retrieved_at':now(),'endpoint':url,'request':payload if payload is not None else params,'response_hash':hashlib.sha256(r.content).hexdigest(),'data':body}
   write_json(p,envelope);return envelope
  except (requests.RequestException,ValueError) as error:
   if attempt==2:raise RuntimeError(f'Official API retrieval failed: {type(error).__name__}; no complete coverage claim') from None
   time.sleep(2**attempt)

def nih():
 url='https://api.reporter.nih.gov/v2/projects/search'
 fields=['ApplId','SubprojectId','FiscalYear','ProjectNum','CoreProjectNum','ProjectTitle','AbstractText','PhrText','AwardAmount','ProjectDetailUrl','AwardNoticeDate','BudgetStart','BudgetEnd','ProjectStartDate','ProjectEndDate','AgencyIcAdmin','AgencyIcFundings','ActivityCode','FundingMechanism']
 rows=[];offset=0;total=None;pages=[]
 while total is None or offset<total:
  payload={'criteria':{'agencies':['NIA'],'is_agency_admin':True,'fiscal_years':[YEAR]},'offset':offset,'limit':500,'include_fields':fields,'sort_field':'appl_id','sort_order':'asc'}
  env=request_json(url,payload=payload);j=env['data'];n=j['meta']['total']
  if total is not None and n!=total:raise ValueError('NIH count changed during pagination; refresh the snapshot')
  total=n;batch=j.get('results',[])
  if not batch:raise ValueError('NIH pagination ended before reported total')
  for r in batch:r['_retrieved_at']=env['retrieved_at']
  rows.extend(batch);pages.append(env['response_hash']);offset+=len(batch)
  print(f'NIH FY2024: {offset}/{total} source records',flush=True)
  if offset>=15000 and offset<total:raise ValueError('NIH offset ceiling reached; incomplete portfolio')
 assert len(rows)==total and len({r['appl_id'] for r in rows})==total
 records=[];excluded=0
 for r in rows:
  assert r['fiscal_year']==YEAR and r['agency_ic_admin']['abbreviation']=='NIA'
  if r.get('subproject_id') is not None:excluded+=1;continue
  amount=r.get('award_amount');rid='nih:'+str(r['appl_id'])
  record={'id':rid,'country':'US','source':'nih','source_id':str(r['appl_id']),'project_number':r['project_num'],'core_project_number':r.get('core_project_num'),'title':r.get('project_title') or r['project_num'],'abstract':r.get('abstract_text') or '', 'public_health_relevance':r.get('phr_text') or '', 'funder':'National Institute on Aging (administering institute)','funder_id':'NIA','government_funder':True,'year':YEAR,'currency':'USD','amount_minor':cents(amount),'amount_basis':'NIH fiscal-year parent award','funding_start':r.get('budget_start'),'funding_end':r.get('budget_end'),'source_date':r.get('award_notice_date'),'source_date_note':'Award notice date when supplied; fiscal year remains the funding-period field.','source_url':r.get('project_detail_url') or f"https://reporter.nih.gov/project-details/{r['appl_id']}",'api_url':url,'retrieved_at':r['_retrieved_at'],'source_location':'award_amount; fiscal_year; agency_ic_admin; abstract_text','activity_code':r.get('activity_code'),'funding_mechanism':r.get('funding_mechanism'),'funding_contributions':r.get('agency_ic_fundings',[])}
  record['source_hash']=source_version(record);record['version_hash']=digest({'source_hash':record['source_hash'],'normalizer':'funding-normalize-v1'})
  records.append(record)
 return records,{'source':'NIH RePORTER','api_rows':total,'retained_records':len(records),'excluded_subprojects':excluded,'complete':True,'page_hashes':pages,'scope':'All NIA-administered FY2024 API records, then parent awards only'}

def swecris():
 r=SESSION.get('https://www.vr.se/english/swecris/swecris-api.html',timeout=45);r.raise_for_status();m=re.search(r'VRSwecrisAPI\d{4}-\d+',r.text)
 if not m:raise ValueError('Official Swecris public token could not be located')
 headers={'Authorization':'Bearer '+m.group()};records={};coverage=[]
 for funder in PORTFOLIOS['SE']['funders']:
  page=1;rows=[];total=None;hashes=[]
  while total is None or len(rows)<total:
   env=request_json('https://swecris-api.vr.se/v1/scp/search',params=[('fundingOrganisation[]',funder),('page',page),('size',500)],headers=headers);j=env['data'];n=j['total']
   if total is not None and n!=total:raise ValueError('Swecris count changed during pagination')
   total=n;batch=j['result']
   if not batch:raise ValueError('Swecris pagination ended before reported total')
   for row in batch:row['_retrieved_at']=env['retrieved_at']
   rows.extend(batch);hashes.append(env['response_hash']);page+=1
   print(f'Swecris {funder}: {len(rows)}/{total} source records (all funding years)',flush=True)
  selected=0
  for row in rows:
   r={k.lower():v for k,v in row.items()}
   if str(r.get('fundingyear'))!=str(YEAR):continue
   if r.get('fundingorganisationid')!=funder:continue
   if r.get('fundingorganisationtypeoforganisationen')!='Governmental':raise ValueError('Selected funder government status missing')
   pid=r['projectid'];rid='swecris:'+pid+':'+funder+':'+str(r.get('fundingstartdate'))[:10]
   record={'id':rid,'country':'SE','source':'swecris','source_id':pid,'project_number':pid,'title':r.get('projecttitleen') or r.get('projecttitlesv') or pid,'abstract':r.get('projectabstracten') or r.get('projectabstractsv') or '', 'abstract_language':'en' if r.get('projectabstracten') else 'sv','public_health_relevance':'','funder':r['fundingorganisationnameen'],'funder_id':funder,'government_funder':True,'year':YEAR,'currency':'SEK','amount_minor':cents(r.get('fundingssek')),'amount_basis':'Swecris government funder grant commitment','funding_start':r.get('fundingstartdate'),'funding_end':r.get('fundingenddate'),'source_date':r.get('updateddate'),'source_date_note':'Source update date; funding year and funding period are separate fields.','source_url':'https://www.vr.se/english/swecris.html#/project/'+pid,'api_url':'https://swecris-api.vr.se/v1/projects/'+pid,'retrieved_at':r['_retrieved_at'],'source_location':'fundingsSek; fundingYear; fundingOrganisationId; projectAbstractEn/Sv','subject_codes':r.get('scbs')}
   record['source_hash']=source_version(record);record['version_hash']=digest({'source_hash':record['source_hash'],'normalizer':'funding-normalize-v1'})
   if rid in records and records[rid]['source_hash']!=record['source_hash']:raise ValueError('Conflicting Swedish funding rows')
   records[rid]=record;selected+=1
  coverage.append({'funder_id':funder,'api_rows_all_years':total,'selected_funding_year_rows':selected,'complete':len(rows)==total,'page_hashes':hashes})
 return list(records.values()),{'source':'Swecris','retained_records':len(records),'complete':all(c['complete'] for c in coverage),'funders':coverage,'scope':'All Research Council and Forte records, filtered locally by fundingYear=2024'}

def main(source='all'):
 existing=load(DATA/'records.json',[]);kept=[r for r in existing if source!='all' and r['source']!=source]
 cov=load(DATA/'coverage.json',{})
 for name,fn in [('nih',nih),('swecris',swecris)]:
  if source not in ('all',name):continue
  records,coverage=fn();kept.extend(records);cov['US' if name=='nih' else 'SE']=coverage
  write_json(DATA/(name+'-records.json'),records);write_json(DATA/'coverage.json',cov)
 write_json(DATA/'records.json',sorted(kept,key=lambda r:r['id']))
 with db() as c:
  for r in kept:c.execute('INSERT INTO funding_grants VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_hash=excluded.source_hash,version_hash=excluded.version_hash,payload=excluded.payload',(r['id'],r['country'],r['source_hash'],r['version_hash'],json.dumps(r,ensure_ascii=False)))
 print(json.dumps({'records':len(kept),'countries':{c:sum(r['country']==c for r in kept) for c in PORTFOLIOS}}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',choices=['all','nih','swecris'],default='all');main(p.parse_args().source)
