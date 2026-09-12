"""Funding arithmetic and publication controls. All human verdicts here are fixtures."""
import copy,json
import pytest
from funding.common import CATEGORIES,DATA,ROOT,load,cents,SOURCE_CHECKS,REPORT_CHECKS,source_version
from funding.aggregate import aggregate
from funding.review import context,metrics,import_export
from funding.classify import candidate,normalize

def fixtures():
 rows=[];labels={};bench={'population_version':'fixture-population','records':[]}
 for country in ['SE','US']:
  for n in range(30):
   rid=f'{country}-{n}';r={'id':rid,'country':country,'currency':'SEK' if country=='SE' else 'USD','year':2024,'amount_minor':(n+1)*100,'version_hash':'source-'+rid,'title':'Fixture '+rid}
   rows.append(r);labels[rid]={'category':'fundamental_aging' if n%2 else 'age_related_disease','version_hash':'prediction-'+rid}
   bench['records'].append({'id':rid,'country':country,'source_version':r['version_hash'],'prediction_version':labels[rid]['version_hash']})
 return context(rows,labels,bench)

def verdict(ctx,rid,category=None):
 return {'reviewer':'TEST FIXTURE','human_attested':True,'reviewed_at':'2026-09-12T08:00:00+00:00','source_version':ctx['by_id'][rid]['version_hash'],'review_version':ctx['labels'][rid]['version_hash'],'category':category or ctx['labels'][rid]['category'],'checks':dict.fromkeys(SOURCE_CHECKS,True),'note':'Synthetic unit-test fixture only.'}

def approved_fixture(ctx):
 verdicts={r['id']:{'first':verdict(ctx,r['id']),'current':verdict(ctx,r['id'])} for r in ctx['rows']}
 reports={c:{'reviewer':'TEST FIXTURE','human_attested':True,'reviewed_at':'2026-09-12T08:00:00+00:00','version_hash':r['version_hash'],'checks':dict.fromkeys(REPORT_CHECKS,True)} for c,r in ctx['reports'].items()}
 return verdicts,reports

def test_currency_minor_units_preserve_missing_and_zero():
 assert cents(None) is None and cents('') is None
 assert cents(0)==0 and cents('123.45')==12345
 for bad in ['NaN','Infinity','-1']:
  with pytest.raises(ValueError):cents(bad)

def test_shares_weight_money_and_bound_only_known_unresolved():
 rows=[{'id':str(i),'country':'SE','currency':'SEK','year':2024,'amount_minor':v} for i,v in enumerate([100,900,100,None,0])]
 labels={str(i):{'category':c} for i,c in enumerate(['fundamental_aging','age_related_disease','unresolved','unresolved','intervention'])}
 a=aggregate(rows,labels)
 assert a['ratio']==.1 # two target grants out of three classified grants is not the money share
 assert a['sensitivity_lower']==pytest.approx(100/1100)
 assert a['sensitivity_upper']==pytest.approx(200/1100)
 assert a['missing_amount_records']==1 and a['zero_amount_records']==1
 assert a['numerator_minor']==100 and a['denominator_minor']==1000

def test_empty_denominator_has_no_ratio_or_finite_bounds():
 a=aggregate([{'id':'x','country':'US','currency':'USD','year':2024,'amount_minor':100}],{'x':{'category':'unresolved'}})
 assert a['ratio'] is None and a['sensitivity_lower'] is None and a['sensitivity_upper'] is None

def test_cannot_sum_duplicate_awards_or_mixed_currency():
 rows=[{'id':'a','country':'SE','currency':'SEK','year':2024,'amount_minor':100}]
 with pytest.raises(ValueError):aggregate(rows*2,{'a':{'category':'fundamental_aging'}})
 with pytest.raises(ValueError):aggregate(rows+[dict(rows[0],id='b',currency='USD')],{'a':{'category':'fundamental_aging'},'b':{'category':'fundamental_aging'}})

def test_overall_ninety_does_not_hide_one_country_failure():
 ctx=fixtures();v,a=approved_fixture(ctx)
 for rid in ['SE-0','SE-1','US-0','US-1','US-2','US-3']:v[rid]['first']['category']='unresolved'
 m=metrics(ctx,v,a)
 assert m['overall']['accuracy']==.9 and not m['overall']['passed']
 assert not m['countries']['US']['publication_ready'] and not m['countries']['SE']['publication_ready']

def test_all_reviews_and_largest_awards_and_report_are_required():
 ctx=fixtures();v,a=approved_fixture(ctx)
 assert all(p['publication_ready'] for p in metrics(ctx,v,a)['countries'].values())
 del v['US-1'];assert not metrics(ctx,v,a)['overall']['passed']
 v,a=approved_fixture(ctx);a['SE']['checks']['arithmetic_correct']=False
 assert not metrics(ctx,v,a)['countries']['SE']['publication_ready']
 v,a=approved_fixture(ctx);top=ctx['reports']['SE']['top_award_ids'][0];v[top]['current']['category']='unresolved'
 assert not metrics(ctx,v,a)['countries']['SE']['publication_ready']

def test_source_and_label_changes_invalidate_reviews():
 ctx=fixtures();v,a=approved_fixture(ctx);ctx['by_id']['US-0']['version_hash']='changed'
 m=metrics(ctx,v,a);assert m['countries']['US']['stale']==1 and not m['overall']['passed']
 ctx=fixtures();v,a=approved_fixture(ctx);ctx['labels']['SE-0']['version_hash']='new-taxonomy'
 assert not metrics(ctx,v,a)['overall']['passed']

def test_import_preserves_first_error_and_rejects_stale_atomically(tmp_path):
 ctx=fixtures();rid='SE-0';wrong=verdict(ctx,rid,'unresolved');path=tmp_path/'export.json'
 body={'format':'longview-funding-review-v1','benchmark_version':'fixture-population','verdicts':{rid:wrong},'reports':{}}
 path.write_text(json.dumps(body));import_export(path,ctx,tmp_path/'eval',False)
 body['verdicts'][rid]=verdict(ctx,rid);path.write_text(json.dumps(body));import_export(path,ctx,tmp_path/'eval',False)
 v=load(tmp_path/'eval/verdicts.json');assert v[rid]['first']['category']=='unresolved' and v[rid]['current']['category']=='age_related_disease'
 assert metrics(ctx,v,{})['overall']['correct']==0
 history=(tmp_path/'eval/history.jsonl').read_text();body['verdicts'][rid]['source_version']='stale';path.write_text(json.dumps(body))
 with pytest.raises(ValueError):import_export(path,ctx,tmp_path/'eval',False)
 assert (tmp_path/'eval/history.jsonl').read_text()==history
 body['simulation']=True;path.write_text(json.dumps(body))
 with pytest.raises(ValueError):import_export(path,ctx,tmp_path/'eval',False)

def test_frozen_benchmark_is_balanced_and_separate():
 bench=load(ROOT/'eval/funding/benchmark.json');assert len(bench['records'])==60
 assert all(sum(x['country']==c for x in bench['records'])==30 for c in ['SE','US'])
 assert not set(bench['excluded_development_ids']) & {r['id'] for r in bench['records']}
 assert sum(not r['title_has_ageing_keyword'] for r in bench['records'])==40

def test_public_pending_release_contains_no_candidate_ratios_or_abstracts():
 r=load(ROOT/'public/funding/current.json');ledger=load(ROOT/'public/funding/ledgers'/(r['ledger_hash'][:16]+'.json'))
 for c,report in r['reports'].items():
  if not report['publication_ready']:
   assert report['summary'] is None
   assert all(x['classification'] is None for x in ledger['records'] if x['country']==c)
 assert all('abstract' not in x and 'public_health_relevance' not in x for x in ledger['records'])
 assert len({x['id'] for x in ledger['records']})==r['source_count']

def test_objective_precedence_and_uncertain_language():
 r={'title':'Developing elderly care for people with dementia','abstract':'This research studies nursing homes and the needs of older people with dementia. We will study how caregivers provide support and how services can be improved.'}
 assert candidate(r)['category']=='care_research'
 r={'title':'Cell generation','abstract':'We will investigate regeneration and cell renewal in the human heart and brain, including how to restore regenerative capacity after injury.'}
 assert candidate(r)['category']=='unresolved'
 r={'title':'Ageing in society','abstract_language':'sv','abstract':'Forskning om åldrande och äldre människor. '*10}
 assert candidate(r)['category']=='unresolved'

@pytest.mark.skipif(not (DATA/'records.json').exists(),reason='Official local snapshots are not committed')
def test_collected_snapshot_integrity_and_verbatim_support():
 rows=load(DATA/'records.json');labels={x['grant_id']:x for x in load(DATA/'labels.json')};cov=load(DATA/'coverage.json')
 assert len(rows)==len({r['id'] for r in rows})==6623
 assert cov['US']['api_rows']==cov['US']['retained_records']+cov['US']['excluded_subprojects']
 for r in rows:
  assert r['year']==2024 and r['government_funder'] and r['source_hash']==source_version(r)
  assert r['currency']==('SEK' if r['country']=='SE' else 'USD')
  p=labels[r['id']];assert p['source_version']==r['version_hash']
  assert not p['supporting_passage'] or normalize(p['supporting_passage']) in normalize(r['abstract'])

def test_review_event_log_recovers_first_verdict_after_interrupted_write(tmp_path):
 ctx=fixtures();rid='SE-0';body={'format':'longview-funding-review-v1','benchmark_version':'fixture-population','verdicts':{rid:verdict(ctx,rid,'unresolved')},'reports':{}};path=tmp_path/'export.json';path.write_text(json.dumps(body));folder=tmp_path/'eval'
 import_export(path,ctx,folder,False)
 (folder/'verdicts.json').write_text('{}') # emulate lost materialised view, not lost history
 body['verdicts'][rid]=verdict(ctx,rid);path.write_text(json.dumps(body));import_export(path,ctx,folder,False)
 assert load(folder/'verdicts.json')[rid]['first']['category']=='unresolved'

@pytest.mark.skipif(not (DATA/'records.json').exists(),reason='Official snapshots stay local')
def test_approved_release_and_source_integrity_in_isolated_output(tmp_path,monkeypatch):
 import funding.release as rel
 import jsonschema
 ctx=context();v,a=approved_fixture(ctx)
 status=metrics(ctx,v,a)
 monkeypatch.setattr(rel,'metrics',lambda _:status)
 original_load=rel.load
 monkeypatch.setattr(rel,'load',lambda path,default=None:a if path==ROOT/'eval/funding/report-approvals.json' else original_load(path,default))
 monkeypatch.delenv('PUBLIC_SITE_URL',raising=False)
 with pytest.raises(ValueError,match='PUBLIC_SITE_URL'):rel.build(ctx,tmp_path/'no-origin')
 assert not (tmp_path/'no-origin').exists()
 monkeypatch.setenv('PUBLIC_SITE_URL','https://fixture.invalid')
 release=rel.build(ctx,tmp_path/'approved-fixture')
 assert all(r['publication_ready'] and r['summary'] for r in release['reports'].values())
 findings=load(tmp_path/'approved-fixture/funding/findings.json');assert len(findings)==2
 schema=load(ROOT/'schema/finding.schema.json')
 for finding in findings:jsonschema.validate(finding,schema);assert finding['source_url'].startswith('https://fixture.invalid/reports/')
 ctx['rows'][0]['title']+=' CHANGED FIXTURE'
 with pytest.raises(ValueError,match='Source content changed'):rel.build(ctx,tmp_path/'changed-source')
 assert not (tmp_path/'changed-source').exists()
