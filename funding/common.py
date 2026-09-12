from pathlib import Path
from decimal import Decimal
from pipeline.store import ROOT, now, digest, write_json, connect

DATA = ROOT / 'data/funding'
YEAR = 2024
CATEGORIES = {
 'fundamental_aging': 'Ageing biology',
 'intervention': 'Interventions targeting ageing',
 'age_related_disease': 'Age-related disease research',
 'care_research': 'Care and support research',
 'other_aging_research': 'Other ageing research',
 'outside_scope': 'Outside ageing research',
 'unresolved': 'Unresolved',
}
TARGET = {'fundamental_aging', 'intervention'}
AGING = set(CATEGORIES) - {'outside_scope', 'unresolved'}
PORTFOLIOS = {
 'SE': {'name':'Sweden','currency':'SEK','label':'Swedish Research Council + Forte','period':'Funding year 2024','funders':['202100-5208','202100-5240'],'basis':'Grant commitments recorded in Swecris for funding year 2024. Amounts can cover several years; they are not annual expenditure.'},
 'US': {'name':'United States','currency':'USD','label':'NIA-administered federal research awards','period':'Fiscal year 2024','funders':['NIA'],'basis':'Parent award amounts recorded in NIH RePORTER for FY2024. The fiscal year runs October 2023–September 2024; amounts are awards, not measured expenditure.'},
}
SOURCE_CHECKS = ['source_resolves','financial_details_correct','government_scope_correct']
REPORT_CHECKS = ['source_scope_correct','financial_basis_correct','arithmetic_correct','uncertainty_visible']

def load(path, default=None):
 p=Path(path)
 return __import__('json').loads(p.read_text()) if p.exists() else default

def db():
 c=connect()
 c.executescript('''
 CREATE TABLE IF NOT EXISTS funding_grants (
  id TEXT PRIMARY KEY, country TEXT NOT NULL CHECK(country IN ('SE','US')),
  source_hash TEXT NOT NULL, version_hash TEXT NOT NULL, payload TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS funding_labels (
  grant_id TEXT PRIMARY KEY REFERENCES funding_grants(id), category TEXT NOT NULL,
  method TEXT NOT NULL, taxonomy_version TEXT NOT NULL, payload TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS funding_review_events (
  event_hash TEXT PRIMARY KEY, grant_id TEXT NOT NULL REFERENCES funding_grants(id),
  version_hash TEXT NOT NULL, reviewed_at TEXT NOT NULL, payload TEXT NOT NULL);
 ''')
 return c

def cents(value):
 if value is None or value=='':return None
 number=Decimal(str(value))
 if not number.is_finite() or number<0:raise ValueError('Invalid funding amount')
 return int((number*100).quantize(Decimal('1')))

def source_version(record):
 return digest({k:v for k,v in record.items() if k not in {'retrieved_at','source_hash','version_hash','abstract_path'}})
