"""Supplemental funding leads, deliberately outside the frozen initial benchmark."""
import json,re
from jsonschema import validate
from .store import ROOT,COUNTRIES,connect,write_json,now,finding_version
from .research import fetch
from .curate import normal

SG_URL='https://www.moh.gov.sg/newsroom/speech-by-mr-ong-ye-kung--minister-for-health-and-coordinating-minister-for-social-policies--at-the-national-medical-research-council-awards-ceremony-and-research-symposium-2026--22-may-2026/'

def main():
    sources=json.loads((ROOT/'data/fundamental-sources.json').read_text())
    us=next(r['source'] for r in sources if r['url'].endswith('fiscal-year-2025-budget'))
    sg=fetch(SG_URL)
    specs=[
      ('US','us-201',us,'2024','US ageing-biology budget line','NIA’s fiscal-year 2025 budget justification reports US$350.997 million for extramural Aging Biology in the FY2023 Final column. This is an institute programme budget-authority proxy, not total US spending on fundamental ageing research.','Detail: Aging Biology','USD',350997000,'FY2023 Final','final_budget_authority','ageing_biology_programme_proxy'),
      ('SG','sg-201',sg,'2026-05-22','Singapore’s longevity research commitment','Singapore’s health minister announced a S$350 million commitment under RIE2030 for the Grand Challenge on Maximising Healthy and Successful Longevity. Its scope includes translation and socio-environmental innovation; it is not an annual fundamental-ageing research total.','the Government has committed $350 million','SGD',350000000,'RIE2030 programme envelope','announced_commitment','broad_longevity_research')]
    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS funding_observations (
          id TEXT PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(id),
          country TEXT NOT NULL, currency TEXT NOT NULL, amount REAL NOT NULL CHECK(amount>=0),
          period TEXT NOT NULL, financial_stage TEXT NOT NULL, scope TEXT NOT NULL,
          is_national_fundamental_total INTEGER NOT NULL CHECK(is_national_fundamental_total IN (0,1)),
          comparability_note TEXT NOT NULL)''')
    for c,fid,source,pub,title,claim,anchor,currency,amount,period,stage,scope in specs:
        text=normal((ROOT/source['text_path']).read_text());start=text.lower().index(anchor.lower());excerpt=' '.join(text[start:].split()[:22])
        note='Supplemental mentor lead; not part of the 34-record initial benchmark. Human approval is still required for public release.'
        if c=='US':note+=' Table units are thousands of US dollars; 350,997 × 1,000 = 350,997,000. FY2024 CR and FY2025 request columns must not be used as FY2023 final expenditure. Source year comes from the linked March 2024 FY2025 budget publication.'
        else:note+=' A multi-year programme commitment is not annual expenditure; no equal annual split is assumed.'
        f={'id':fid,'type':'finding','country':c,'classification':'funding','claim':claim,'source_url':source['canonical_url'],'source_date':pub,'confidence':'medium','retrieved_at':source['retrieved_at'],'source_note':note}
        validate(f,json.loads((ROOT/'schema/finding.schema.json').read_text()))
        p={'title':title,'source_id':source['id'],'publisher':source['publisher'],'source_title':source['title'],'canonical_url':source['canonical_url'],'retrieved_at':source['retrieved_at'],'content_hash':source['content_hash'],'retrieval_method':source.get('retrieval_method','direct_https'),'hash_basis':source.get('hash_basis','original response bytes'),'publication_date':pub,'decision_date':None,'effective_date':None,'status':stage,'date_note':note,'supporting_passage':excerpt,'passage_location':'US: Budget Authority by Activity table, dollars in thousands, FY2023 Final column. Singapore: paragraph 21 of ministerial speech.','relevance':'Lead for research-funding transparency. Excluded from the life-expectancy model.','classification_rationale':'A dated programme budget-authority line or announced research commitment.','contradictions':['US FY2023 enacted estimate in the earlier FY2024 book differs from FY2023 final in the later FY2025 book; do not mix vintages.'] if c=='US' else [],'review_status':'pending'}
        with connect() as db:
            db.execute('INSERT OR REPLACE INTO policy_events VALUES(?,?,?,?,?,?,?,?,?,?,?)',(fid,c,source['id'],stage,pub,None,None,note,p['relevance'],excerpt,p['passage_location']))
            db.execute('INSERT INTO findings VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,version_hash=excluded.version_hash',(fid,fid,c,'funding',json.dumps(f),finding_version(f,p),now()))
            db.execute('INSERT OR REPLACE INTO funding_observations VALUES(?,?,?,?,?,?,?,?,?,?)',(fid,fid,c,currency,amount,period,stage,scope,0,'Different programme scope, fiscal period and financial stage. No cross-country ranking or annualisation.'))
        slug=COUNTRIES[c][0];fp=ROOT/f'eval/findings/{slug}.json';pp=ROOT/f'eval/provenance/{slug}.json'
        fs=[r for r in json.loads(fp.read_text()) if r['id']!=fid];fs.append(f);ps=json.loads(pp.read_text());ps[fid]=p;write_json(fp,fs);write_json(pp,ps)
    print('Added two supplemental funding candidates; initial benchmark remains frozen at 34.')

if __name__=='__main__':main()
