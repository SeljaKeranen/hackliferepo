import json
import numpy as np
from pipeline.store import ROOT,connect
from pipeline.model import panel,FEATURES,HOLDOUT

def test_published_temporal_and_country_holdouts():
 r=json.loads((ROOT/'docs/model-evaluation.json').read_text())
 for split in r['test_splits']:assert split['latest_training_outcome']<=split['origin']
 assert set(r['country_holdout'])==HOLDOUT
 assert r['selected_model']==min(r['validation_mae'],key=r['validation_mae'].get)

def test_lagged_inputs_and_five_year_targets_come_from_correct_rows():
 observed,rows,_=panel();sample=rows[(rows.country=='SWE')&(rows.year==2014)].iloc[0]
 history=observed[observed.country=='SWE'].set_index('year')
 assert sample.health_spending==history.loc[2013].health_spending
 assert sample.pm25==history.loc[2013].pm25
 assert sample.target==history.loc[2019].life_expectancy-history.loc[2014].life_expectancy
 assert sample.past_change==history.loc[2014].life_expectancy-history.loc[2009].life_expectancy
 assert np.isfinite(rows[FEATURES].to_numpy()).all()

def test_pyramid_denominators_and_finite_country_outputs():
 q=json.loads((ROOT/'public/release/quantitative.json').read_text())
 for c in q['countries']:
  assert len(c['pyramid'])==17
  for sex in ['male','female']:assert abs(sum(p[sex] for p in c['pyramid'])-100)<.1
  assert c['input_year']==c['origin']-1
  assert c['forecast_year']==c['origin']+5
  assert 50<c['forecast']<100

def test_nulls_preserved_and_datasets_documented():
 with connect() as db:
  assert db.execute('SELECT COUNT(*) FROM observations WHERE value IS NULL').fetchone()[0]>0
  assert not db.execute("SELECT * FROM datasets WHERE licence='' OR units='' OR source_url='' OR content_hash='' ").fetchall()
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert not db.execute('PRAGMA foreign_key_check').fetchall()


def test_funding_proxies_are_not_national_fundamental_totals():
 with connect() as db:
  rows={r['country']:dict(r) for r in db.execute('SELECT * FROM funding_observations')}
 assert rows['US']['amount']==350997000
 assert rows['US']['currency']=='USD' and rows['US']['period']=='FY2023 Final'
 assert rows['SG']['amount']==350000000 and rows['SG']['currency']=='SGD'
 assert all(r['is_national_fundamental_total']==0 for r in rows.values())
 assert rows['US']['financial_stage']!=rows['SG']['financial_stage']
