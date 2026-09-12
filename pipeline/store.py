"""Local evidence store. Raw material never belongs in the public build."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DB_PATH = DATA / 'longview.sqlite'
COUNTRIES = {'SE': ('sweden', 'SWE', 'Sweden'), 'US': ('united-states', 'USA', 'United States'), 'SG': ('singapore', 'SGP', 'Singapore')}
CHECKS = ('source_resolves', 'date_correct', 'classification_correct', 'claim_supported')

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    tmp.replace(path)

def connect(path=DB_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS research_runs (
      id INTEGER PRIMARY KEY, provider TEXT NOT NULL, operation TEXT NOT NULL,
      query TEXT NOT NULL, requested_at TEXT NOT NULL, status TEXT NOT NULL,
      response_hash TEXT, error TEXT, UNIQUE(provider, operation, query, requested_at));
    CREATE TABLE IF NOT EXISTS sources (
      id TEXT PRIMARY KEY, canonical_url TEXT NOT NULL UNIQUE, publisher TEXT NOT NULL,
      title TEXT NOT NULL, retrieved_at TEXT NOT NULL, content_hash TEXT NOT NULL,
      http_status INTEGER NOT NULL, text_path TEXT, publication_date TEXT);
    CREATE TABLE IF NOT EXISTS policy_events (
      id TEXT PRIMARY KEY, country TEXT NOT NULL CHECK(country IN ('SE','US','SG')),
      source_id TEXT NOT NULL REFERENCES sources(id), status TEXT NOT NULL,
      publication_date TEXT, decision_date TEXT, effective_date TEXT, date_note TEXT NOT NULL,
      relevance TEXT NOT NULL, supporting_passage TEXT NOT NULL, passage_location TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS findings (
      id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES policy_events(id),
      country TEXT NOT NULL, classification TEXT NOT NULL, payload TEXT NOT NULL,
      version_hash TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS reviews (
      id INTEGER PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(id),
      version_hash TEXT NOT NULL, reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL,
      checks TEXT NOT NULL, correct INTEGER NOT NULL CHECK(correct IN (0,1)), note TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS datasets (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, source_url TEXT NOT NULL,
      licence TEXT NOT NULL, units TEXT NOT NULL, definition TEXT NOT NULL,
      retrieved_at TEXT NOT NULL, revision_date TEXT NOT NULL, content_hash TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS observations (
      dataset_id TEXT NOT NULL REFERENCES datasets(id), country TEXT NOT NULL,
      year INTEGER NOT NULL, value REAL, PRIMARY KEY(dataset_id,country,year));
    CREATE TABLE IF NOT EXISTS coverage (
      country TEXT NOT NULL, classification TEXT NOT NULL, status TEXT NOT NULL,
      query_count INTEGER NOT NULL, note TEXT NOT NULL, updated_at TEXT NOT NULL,
      PRIMARY KEY(country,classification));
    ''')
    return db

def finding_version(finding, provenance):
    return digest({'finding': finding, 'provenance': provenance})

def approved(finding, provenance, verdict):
    return bool(verdict and verdict.get('reviewer','').strip()
        and verdict.get('version_hash') == finding_version(finding, provenance)
        and verdict.get('reviewed') is True and verdict.get('correct') is True
        and all(verdict.get('checks',{}).get(c) is True for c in CHECKS))


def current_source_matches(provenance, db):
    row = db.execute('SELECT content_hash FROM sources WHERE id=?', (provenance.get('source_id'),)).fetchone()
    return bool(row and row['content_hash'] == provenance.get('content_hash'))
