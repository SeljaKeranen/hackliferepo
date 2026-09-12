"""Conservative, inspectable classification without paid model calls."""
import csv, html, json, re
from collections import Counter
from .common import *

TAXONOMY_VERSION='ageing-objectives-v1'
RULES_VERSION='funding-rules-v2'
AGE=re.compile(r'\b(ageing|aging|aged|elderly|geriatric|geroscience|healthspan|lifespan|longevity|older adults?|older people|older persons|senescen\w*|åldrande|äldre|livslängd)\b',re.I)
MECHANISM=re.compile(r'\b(senescen\w*|proteostasis|autophagy|mitochondri\w*|epigenetic|telomer\w*|stem.cell|nutrient.sensing|inflammaging|regenerat\w*|cell renewal|metabolic|metabolism|neurodegener\w*)\b',re.I)
DISEASE=re.compile(r"\b(alzheimer\w*|dementia|parkinson\w*|cancer|carcinoma|tumou?r|diabet\w*|cardiovascular|atherosclero\w*|osteoporo\w*|sarcopenia|frailty|macular degeneration|stroke|heart failure|demens|cancersjukdom\w*)\b",re.I)
BIO=re.compile(r'\b((biology|biological mechanisms?|molecular mechanisms?|mechanisms?|process(?:es)?) of (human )?ag(e|i)ng|biological ag(e|i)ng|aging biology|ageing biology|cellular senescence|replicative senescence|hallmarks of ag(e|i)ng|epigenetic clock\w*|comparative longevity)\b',re.I)
INTERVENTION=re.compile(r'\b(geroprotect\w*|senolytic\w*|senomorph\w*|slow(?:ing)? (?:biological )?ag(e|i)ng|extend\w* (?:healthy )?(?:life|health)span|lifespan extension|rapamycin|dietary restriction|calori[ce] restriction)\b',re.I)
CARE=re.compile(r'\b(caregiv\w*|nursing homes?|long.term care|elder care|eldercare|home care|elderly care|äldreomsorg)\b',re.I)
SOCIAL=re.compile(r'\b(retirement|pension|social isolation|loneliness|healthy ag(e|i)ng|cognitive ag(e|i)ng|population ag(e|i)ng|social determinants|ageism|later life|housing environments)\b',re.I)
NONBIO=re.compile(r'\b(batter(?:y|ies)|galax\w*|stellar|steel|concrete|asphalt|photovoltaic|polymer|semiconductor|superconduct\w*)\b',re.I)

def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s or ''))).strip()
def normalize(s):return re.sub(r'[^\w]+',' ',clean(s).lower()).strip()
def passage(text,pattern=None):
 if not text:return ''
 start=0
 if pattern:
  match=pattern.search(text)
  if match:start=max(0,text.rfind('.',0,match.start())+1)
 return ' '.join(text[start:].split()[:22])

def candidate(r,prior=None):
 text=clean(r.get('abstract',''));title=clean(r['title']);whole=title+' '+text
 label='unresolved';reason='The objective needs a person to resolve its ageing relevance or category.';pattern=None;method=RULES_VERSION
 if len(text)<100:reason='The source abstract is missing or too short to classify reliably.'
 elif NONBIO.search(title) and not DISEASE.search(whole) and not re.search(r'\b(cell|human|patient|mouse|mice|clinical)\b',whole,re.I):
  label='outside_scope';reason='The stated objective concerns materials or physical systems rather than biological ageing.';pattern=NONBIO
 elif re.search(r'\b(pediatric|paediatric|childhood|pregnancy|adolescents|infant)\b',title,re.I) and not AGE.search(title):
  label='outside_scope';reason='The title identifies a childhood or pregnancy objective, with no stated ageing objective.'
 elif r.get('abstract_language')=='sv':reason='The available abstract is Swedish; language-specific objective review is required.'
 elif CARE.search(title) and AGE.search(whole):
  label='care_research';reason='The title identifies care or support research for older people.';pattern=CARE
 elif SOCIAL.search(title) and AGE.search(whole):
  label='other_aging_research';reason='The title identifies a social or population-ageing research objective.';pattern=SOCIAL
 elif INTERVENTION.search(whole) and AGE.search(whole):
  if re.search(r'\b(lifespan|healthspan|geroprotect\w*|senolytic\w*|slow(?:ing)? (?:biological )?ag(e|i)ng)\b',whole,re.I):label='intervention';reason='The source explicitly describes an intervention targeting ageing or senescence.';pattern=INTERVENTION
 elif BIO.search(whole):label='fundamental_aging';reason='The source explicitly names ageing biology or a defined ageing mechanism.';pattern=BIO
 elif DISEASE.search(whole) and not (MECHANISM.search(whole) and AGE.search(whole)):
  label='age_related_disease';reason='The stated focus is an age-related disease; an ageing-mechanism objective is not established by this rule.';pattern=DISEASE
 elif CARE.search(whole) and AGE.search(whole):label='care_research';reason='The award studies care or support for older people; the amount is research funding, not care expenditure.';pattern=CARE
 elif SOCIAL.search(whole) and AGE.search(whole):label='other_aging_research';reason='The source states a social, behavioural or population-ageing research objective.';pattern=SOCIAL
 elif not AGE.search(whole) and not MECHANISM.search(whole) and not DISEASE.search(whole):
  label='outside_scope';reason='No ageing objective, age-related disease or mechanism requiring further review was found in the full abstract.'
 # Prior classifications are reused only as candidates with matching year, amount,
 # title and a verbatim source passage, and agreement with the current rule.
 reused=False
 if prior:
  old={'care':'care_research','ambiguous':'unresolved'}.get(prior['llm_category'],prior['llm_category'])
  quote=clean(prior.get('llm_quote',''))
  reused=(old==label and label!='unresolved' and str(prior['year'])==str(r['year']) and cents(prior.get('amount'))==r['amount_minor'] and normalize(prior['title'])==normalize(title) and len(quote.split())>=4 and normalize(quote) in normalize(text))
  if reused:method='existing-model-candidate + '+RULES_VERSION
 result={'category':label,'method':method,'taxonomy_version':TAXONOMY_VERSION,'rationale':reason,'supporting_passage':passage(text,pattern),'prior_candidate_reused':reused,'human_verified':False}
 assert not result['supporting_passage'] or normalize(result['supporting_passage']) in normalize(text)
 return result

def main():
 rows=load(DATA/'records.json',[]);assert rows,'Collect the portfolios first'
 old={}
 for name in ['nih_reporter.csv','swecris.csv']:
  p=ROOT/'data/Track3_C2/output'/name
  if p.exists():
   for row in csv.DictReader(p.open(encoding='utf-8-sig')):old[(row['record_id'].split(':',1)[1],str(row['year']))]=row
 output=[]
 with db() as c:
  for row in rows:
   pred=candidate(row,old.get((row['project_number'],str(row['year']))))
   label={**pred,'grant_id':row['id'],'source_version':row['version_hash']}
   label['version_hash']=digest({'source':row['version_hash'],'prediction':pred,'rules':RULES_VERSION})
   c.execute('INSERT INTO funding_labels VALUES(?,?,?,?,?) ON CONFLICT(grant_id) DO UPDATE SET category=excluded.category,method=excluded.method,taxonomy_version=excluded.taxonomy_version,payload=excluded.payload',(row['id'],label['category'],label['method'],TAXONOMY_VERSION,json.dumps(label)))
   output.append(label)
 write_json(DATA/'labels.json',output)
 print(json.dumps({'records':len(rows),'countries':{country:dict(Counter(p['category'] for r,p in zip(rows,output) if r['country']==country)) for country in PORTFOLIOS},'prior_labels_reused':sum(p['prior_candidate_reused'] for p in output),'paid_model_calls':0},indent=2))
if __name__=='__main__':main()
