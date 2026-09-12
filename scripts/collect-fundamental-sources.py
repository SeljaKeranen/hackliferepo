"""Retrieve the supplemental funding sources, preserving failed retrievals explicitly."""
from pipeline.research import fetch, extract
from pipeline.store import DATA, write_json
URLS = [
 'https://www.nia.nih.gov/about/budget/fiscal-year-2025-budget',
 'https://www.nia.nih.gov/about/budget/fiscal-year-2024-budget',
 'https://forte.se/en/what-we-do/areas-of-coordination/elderly-and-ageing',
 'https://www.vr.se/english/analysis/swedish-research-in-figures.html',
 'https://www.nmrc.gov.sg/grants/competitive-research-grants/healthy-longevity-global-grand-challenge/healthy-longevity-catalyst-awards-2024',
]
def main():
 records=[]
 for url in URLS:
  try:
   try: source=fetch(url)
   except Exception: source=extract(url)
   records.append({'url':url,'source':source})
  except Exception as exc: records.append({'url':url,'error':type(exc).__name__})
 write_json(DATA/'fundamental-sources.json',records)
 print(f"Retrieved {sum('source' in r for r in records)}/{len(records)} funding sources; failures remain explicit.")
if __name__=='__main__': main()
