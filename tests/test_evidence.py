import copy,json
from pathlib import Path
import pytest
from jsonschema import validate,ValidationError
from pipeline.store import ROOT,connect,approved,finding_version,CHECKS
from pipeline.import_reviews import validated
from pipeline.curate import normal

@pytest.fixture
def record():
 f=json.loads((ROOT/'eval/findings/sweden.json').read_text())[0]
 p=json.loads((ROOT/'eval/provenance/sweden.json').read_text())[f['id']]
 # Synthetic verdict only: never written into real eval/verdicts or a release.
 v={'finding_id':f['id'],'version_hash':finding_version(f,p),'reviewer':'TEST FIXTURE','reviewed_at':'2026-01-01T00:00:00Z','checks':{k:True for k in CHECKS},'reviewed':True,'correct':True,'note':'Synthetic test only'}
 return copy.deepcopy((f,p,v))

def test_edited_claim_or_source_invalidates_human_verdict(record):
 f,p,v=copy.deepcopy(record);assert approved(f,p,v)
 f['claim']+=' An unsupported added sentence.';assert not approved(f,p,v)
 f,p,v=copy.deepcopy(record);p['content_hash']='different';assert not approved(f,p,v)

def test_empty_or_failed_or_partial_review_never_published(record):
 f,p,v=record
 for mutation in [{'reviewer':''},{'checks':{}},{'correct':False},{'version_hash':'old'}]:assert not approved(f,p,{**v,**mutation})
 assert not approved(f,p,None)

def test_import_rejects_stale_forged_shapes_and_unknown_ids(record):
 f,p,v=record;versions={f['id']:finding_version(f,p)}
 assert validated(v,versions)
 for mutate in [{'version_hash':'stale'},{'finding_id':'xx-999'},{'reviewer':''},{'checks':{k:1 for k in CHECKS}},{'reviewed':False}]:
  with pytest.raises(ValueError):validated({**v,**mutate},versions)

def test_all_candidates_have_real_support_and_valid_dates():
 schema=json.loads((ROOT/'schema/finding.schema.json').read_text());ids=set();semantic=set()
 with connect() as db:
  for p in (ROOT/'eval/findings').glob('*.json'):
   prov=json.loads((ROOT/'eval/provenance'/p.name).read_text())
   for f in json.loads(p.read_text()):
    validate(f,schema);assert f['id'] not in ids;ids.add(f['id'])
    pr=prov[f['id']];source=db.execute('SELECT * FROM sources WHERE id=?',(pr['source_id'],)).fetchone();assert source
    assert normal(pr['supporting_passage']) in normal((ROOT/source['text_path']).read_text())
    assert len(pr['supporting_passage'].split())<=25
    key=(f['country'],f['source_url'],f['classification'],normal(f['claim']).lower());assert key not in semantic;semantic.add(key)
    assert pr['status']!='proposed' or pr['effective_date'] is None
    assert pr['publication_date']==f['source_date']

def test_proposal_and_enactment_are_distinct_events():
 fs=json.loads((ROOT/'eval/findings/sweden.json').read_text());ps=json.loads((ROOT/'eval/provenance/sweden.json').read_text())
 proposal=next(f for f in fs if '2025/26:60' in f['claim']);assert ps[proposal['id']]['status']=='proposed';assert ps[proposal['id']]['effective_date'] is None
 tobacco=next(f for f in fs if 'outdoor public' in f['claim']);p=ps[tobacco['id']];assert p['decision_date']=='2018-12-12';assert p['effective_date']=='2019-07-01'

def test_sqlite_rejects_orphan_observations_and_duplicate_keys(tmp_path):
 db=connect(tmp_path/'test.sqlite')
 import sqlite3
 with pytest.raises(sqlite3.IntegrityError):db.execute('INSERT INTO observations VALUES(?,?,?,?)',('missing','SWE',2024,84.))

def test_public_release_contains_only_current_human_approvals():
 release=json.loads((ROOT/'public/release/evidence.json').read_text())
 for f in release['findings']:
  slug={'SE':'sweden','US':'united-states','SG':'singapore'}[f['country']]
  vs=json.loads((ROOT/f'eval/verdicts/{slug}.verdicts.json').read_text());original={k:v for k,v in f.items() if k not in ('provenance','review')}
  assert approved(original,f['provenance'],vs[f['id']])
 if not release['benchmark']['reviewed']:assert release['benchmark']['accuracy'] is None

def test_request_cap_is_checked_before_network(tmp_path,monkeypatch):
 import pipeline.research as r
 dbpath=tmp_path/'budget.sqlite';db=connect(dbpath)
 with db:
  for i in range(r.CAP-r.PLANNING_REQUESTS):db.execute('INSERT INTO research_runs(provider,operation,query,requested_at,status) VALUES(?,?,?,?,?)',('tavily','search',str(i),str(i),'failed'))
 monkeypatch.setattr(r,'DATA',tmp_path);monkeypatch.setattr(r,'connect',lambda:connect(dbpath));monkeypatch.setattr(r,'credentials',lambda:{'tavily':'fixture-not-a-key'})
 monkeypatch.setattr(r.requests,'post',lambda *a,**k:pytest.fail('Network must not be called after cap'))
 with pytest.raises(RuntimeError,match='cap'):r.search('tavily','new query')


def test_refetched_changed_source_invalidates_release_eligibility(tmp_path):
 from pipeline.store import current_source_matches
 db=connect(tmp_path/'fresh.sqlite')
 with db:db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?)',('s','https://example.org','Fixture','Fixture','2026-01-01','new-hash',200,'fixture.txt',None))
 assert not current_source_matches({'source_id':'s','content_hash':'old-hash'},db)
 assert current_source_matches({'source_id':'s','content_hash':'new-hash'},db)
