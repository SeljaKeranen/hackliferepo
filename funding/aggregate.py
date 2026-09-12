"""Monetary shares with explicit unresolved and missing funding."""
from .common import *

def aggregate(records,labels):
 if len(records)!=len({r['id'] for r in records}):raise ValueError('Duplicate awards cannot be summed')
 if len({(r['country'],r['currency'],r['year']) for r in records})>1:raise ValueError('Mixed countries, currencies or funding years cannot be summed')
 totals={k:0 for k in CATEGORIES};counts={k:0 for k in CATEGORIES};missing=0;zero=0
 for r in records:
  category=labels[r['id']]['category'];assert category in CATEGORIES
  counts[category]+=1
  if r['amount_minor'] is None:missing+=1;continue
  assert r['amount_minor']>=0
  if r['amount_minor']==0:zero+=1
  totals[category]+=r['amount_minor']
 numerator=sum(totals[k] for k in TARGET);denominator=sum(totals[k] for k in AGING);unknown=totals['unresolved'];known=sum(totals.values())
 return {'records':len(records),'category_counts':counts,'category_amount_minor':totals,'known_amount_minor':known,'missing_amount_records':missing,'zero_amount_records':zero,'numerator_minor':numerator,'denominator_minor':denominator,'unresolved_minor':unknown,'outside_scope_minor':totals['outside_scope'],'ratio':numerator/denominator if denominator else None,'biology_only_ratio':totals['fundamental_aging']/denominator if denominator else None,'sensitivity_lower':numerator/(denominator+unknown) if denominator else None,'sensitivity_upper':(numerator+unknown)/(denominator+unknown) if denominator else None,'unresolved_known_money_share':unknown/known if known else None,'range_note':'Classification sensitivity among known amounts, not a confidence interval. Missing amounts are excluded from these bounds.'}

def public_grant(r,label=None):
 keys=['id','country','source','source_id','project_number','title','funder','funder_id','government_funder','year','currency','amount_minor','amount_basis','funding_start','funding_end','source_date','source_date_note','source_url','api_url','retrieved_at','source_hash','version_hash','source_location']
 result={k:r.get(k) for k in keys}
 result['classification']=label if label else None
 return result
