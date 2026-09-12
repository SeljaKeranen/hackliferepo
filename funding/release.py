"""Build an immutable, approved-only public funding release and source ledger."""
import argparse,json,html,os
from urllib.parse import urlsplit
from .common import *
from .aggregate import public_grant
from .review import context,metrics,packet
from .classify import RULES_VERSION,TAXONOMY_VERSION,normalize
METHOD_VERSION='funding-method-v1'

def build(ctx=None,output=None):
 ctx=ctx or context();output=output or ROOT/'public';status=metrics(ctx)
 coverage=load(DATA/'coverage.json',{})
 for r in ctx['rows']:
  if r['source_hash']!=source_version(r):raise ValueError('Source content changed without a new version')
  if r['version_hash']!=digest({'source_hash':r['source_hash'],'normalizer':'funding-normalize-v1'}):raise ValueError('Invalid normalised source version')
  p=ctx['labels'][r['id']]
  if p['source_version']!=r['version_hash'] or p['taxonomy_version']!=TAXONOMY_VERSION:raise ValueError('Stale source or taxonomy in label')
  prediction={k:p[k] for k in ['category','method','taxonomy_version','rationale','supporting_passage','prior_candidate_reused','human_verified']}
  if p['version_hash']!=digest({'source':r['version_hash'],'prediction':prediction,'rules':RULES_VERSION}):raise ValueError('Classification content changed without a new version')
  if p['supporting_passage'] and normalize(p['supporting_passage']) not in normalize(r['abstract']):raise ValueError('Supporting passage is not in source')
  if not r['government_funder'] or r['year']!=YEAR or r['currency']!=PORTFOLIOS[r['country']]['currency']:raise ValueError('Funding scope or currency mismatch')
 for c in PORTFOLIOS:
  if coverage.get(c,{}).get('retained_records')!=sum(r['country']==c for r in ctx['rows']):raise ValueError('Coverage count does not match records')
 reports={};ledger=[]
 for country,report in ctx['reports'].items():
  ready=status['countries'][country]['publication_ready'] and coverage.get(country,{}).get('complete') is True
  s=report['summary']
  reports[country]={k:v for k,v in report.items() if k not in {'summary','top_award_ids'}}
  reports[country].update({'publication_ready':ready,'status':'reviewed_estimate' if ready else 'human_review_pending','summary':s if ready else None,'record_count':s['records'],'missing_amount_records':s['missing_amount_records'],'zero_amount_records':s['zero_amount_records'],'coverage':coverage.get(country,{}),'review':status['countries'][country]})
 for r in ctx['rows']:
  p=ctx['labels'][r['id']] if reports[r['country']]['publication_ready'] else None
  item=public_grant(r,p)
  # Portal links work without credentials. The Swecris API needs its documented
  # public token and is a collection endpoint, not a second public source page.
  item.pop('api_url',None)
  ledger.append(item)
 public_base=os.environ.get('PUBLIC_SITE_URL','').rstrip('/')
 if any(x['publication_ready'] for x in reports.values()):
  parsed=urlsplit(public_base)
  if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.query or parsed.fragment or parsed.path not in {'','/'}:raise ValueError('Set PUBLIC_SITE_URL to the public HTTPS deployment origin before publishing approved derived findings')
 ledger_hash=digest(ledger)
 release={'format':'longview-funding-release-v1','method_version':METHOD_VERSION,'year':YEAR,'categories':CATEGORIES,'review':status,'reports':reports,'ledger_hash':ledger_hash,'source_count':len(ledger),'scope_note':'Two government funding portfolios. These are not complete national totals and do not support a country ranking.','financial_note':'Recorded 2024 awards and commitments, in original currencies. Swedish multi-year commitments and US fiscal-year awards have different time bases. No annualisation or currency conversion.','calculation':'(Ageing biology + interventions targeting ageing) / classified ageing-related research funding','research_crosschecks':load(ROOT/'docs/funding/source-crosschecks.json',{}),'source_checked_at':max(r['retrieved_at'] for r in ctx['rows'])}
 rid=digest(release)[:16];release['release_id']=rid
 path=output/'funding/releases'/f'{rid}.json'
 if path.exists() and load(path)!=release:raise ValueError('Immutable release collision')
 write_json(path,release);write_json(output/'funding/current.json',release)
 ledger_path=output/'funding/ledgers'/f'{ledger_hash[:16]}.json'
 write_json(ledger_path,{'release_ledger_hash':ledger_hash,'records':ledger})
 findings=[]
 for country,r in reports.items():
  if r['publication_ready'] and r['summary']['ratio'] is not None:
   findings.append({'id':country.lower()+'-900','type':'finding','country':country,'classification':'funding','claim':f"Within {r['label']} ({r['period']}), the estimated award-weighted share for ageing biology and interventions targeting ageing is {100*r['summary']['ratio']:.1f}%. This is a named-portfolio estimate, not a national spending share.",'source_url':f'{public_base}/reports/{rid}/{country.lower()}/','source_date':load(ROOT/'eval/funding/report-approvals.json')[country]['reviewed_at'][:10],'confidence':'medium','source_note':f"Derived finding approved on the source_date; reproducible release {rid}. All underlying source URLs, amounts, dates and hashes are in its versioned ledger. Bounds exclude missing amounts. Human report approval and the 60-record benchmark passed.",'retrieved_at':release['source_checked_at']})
 write_json(output/'funding/findings.json',findings)
 if output==ROOT/'public':
  write_json(DATA/'review-packet.json',packet(ctx));write_json(DATA/'report-preview.json',ctx['reports'])
 for country,r in reports.items():
  p=output/'reports'/rid/country.lower()/'index.html';p.parent.mkdir(parents=True,exist_ok=True)
  ratio=f"{r['summary']['ratio']*100:.1f}%" if r['publication_ready'] and r['summary']['ratio'] is not None else 'Estimate pending human review'
  link=f"/country/{'sweden' if country=='SE' else 'united-states'}?release={rid}"
  page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(r['name'])} · Longview funding report</title><meta name="description" content="{html.escape(r['label'])}. {ratio}. Recorded 2024 awards; named portfolio, not a national total."><meta property="og:title" content="{html.escape(r['name'])} · Where does ageing research money go?"><meta property="og:description" content="{ratio}. {html.escape(r['label'])}. {r['period']}; not a national total."><meta property="og:image" content="/funding/social-preview.png"><style>body{{background:#f6f5ef;color:#163c33;font:18px system-ui;max-width:850px;padding:8vw;margin:auto}}small{{letter-spacing:.12em}}h1{{font-size:clamp(38px,7vw,78px);line-height:1.04}}a{{color:inherit}}.card{{padding:40px;background:white;border:1px solid #ddd;border-radius:20px}}p{{line-height:1.7}}</style></head><body><small>LONGVIEW / FROZEN REPORT · {rid}</small><h1>{html.escape(r['name'])}</h1><div class="card"><h2>{ratio}</h2><p>{html.escape(r['label'])} · {r['period']}<br>{r['record_count']:,} source records</p><p>{html.escape(r['basis'])}</p><p>Two named portfolios are shown separately. They are not national totals or a country ranking. The headline uses money amounts, with biology and interventions shown separately.</p><a href="{link}">Explore this exact report and its sources →</a></div><p>Human benchmark: {status['overall']['reviewed']}/60 reviewed. Publication requires ≥90% overall and in each country, ten large-award checks per country and report approval. Estimates are not clinical evidence.</p><p><a href="/funding/releases/{rid}.json">Release JSON</a> · <a href="/method">Read the method</a></p></body></html>'''
  if p.exists() and p.read_text()!=page:raise ValueError('Refusing to overwrite frozen report page')
  p.write_text(page)
 print(json.dumps({'release_id':rid,'source_records':len(ledger),'public_estimates':sum(r['publication_ready'] for r in reports.values()),'human_reviews':status['overall']['reviewed']}))
 return release
if __name__=='__main__':build()
