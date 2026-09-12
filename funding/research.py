"""Cross-check method and boundary cases with both budgeted discovery providers."""
from concurrent.futures import ThreadPoolExecutor
from pipeline.research import search,results,fetch,CAP,PLANNING_REQUESTS
from .common import *
QUERIES=[
 ('US','site:report.nih.gov RePORTER total cost subprojects parent projects fiscal year'),
 ('US','site:api.reporter.nih.gov award_amount fiscal_year AgencyIcAdmin funding'),
 ('SE','site:vr.se Swecris funding year funding amount granted projects multi year'),
 ('SE','site:forte.se en funding Swecris all funded projects'),
 ('SE','site:vr.se Swecris ageing metabolism neurodegeneration research'),
 ('US','site:nia.nih.gov research aging biology disease research geroscience funding'),
]
def run(task):
 country,query,provider=task
 try:
  found=results(search(provider,query,4));status='results_returned' if found else 'no_results_returned'
 except RuntimeError:found=[];status='retrieval_failed'
 return {'country':country,'provider':provider,'query':query,'checked_at':now(),'status':status,'links':[{'title':x['title'],'url':x['url']} for x in found],'interpretation':'Discovery cross-check. Original source inspection and human review are separate requirements.'}
def main():
 with ThreadPoolExecutor(max_workers=3) as pool:out=list(pool.map(run,[(c,q,p) for c,q in QUERIES for p in ['you.com','tavily']]))
 with db() as conn:used=conn.execute('SELECT COUNT(*) FROM research_runs').fetchone()[0]+PLANNING_REQUESTS
 write_json(ROOT/'docs/funding/source-crosschecks.json',{'checked_at':now(),'attempted_requests_total':used,'combined_cap':CAP,'checks':out})
 for x in out:print(x['provider'],x['status'],x['query'])
 print('Combined attempted requests:',used,'of',CAP)
if __name__=='__main__':main()
