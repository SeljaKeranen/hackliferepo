"""Prepare an isolated static host directory, resolving social metadata URLs."""
import argparse,json,shutil,re
from urllib.parse import urlsplit
from .common import ROOT,load

def main(origin,output):
 parsed=urlsplit(origin)
 if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.query or parsed.fragment or parsed.path not in {'','/'}:raise ValueError('Use the HTTPS hosting origin without a path or credentials')
 origin=origin.rstrip('/');output=output.resolve()
 if not output.is_relative_to((ROOT/'outputs').resolve()):raise ValueError('Host staging must be inside ignored outputs/')
 shutil.copytree(ROOT/'dist',output,dirs_exist_ok=True)
 config=load(ROOT/'vercel.json');(output/'vercel.json').write_text(json.dumps({'framework':None,'rewrites':config['rewrites'],'headers':config['headers']},indent=2)+'\n')
 # Only host metadata changes. Offline files retain local relative URLs; source
 # amounts, versions and review statuses in the frozen report are untouched.
 for p in [output/'index.html',*output.glob('reports/*/*/index.html')]:
  text=p.read_text().replace('content="/funding/social-preview.png"',f'content="{origin}/funding/social-preview.png"')
  page='/' if p==output/'index.html' else '/'+str(p.parent.relative_to(output))+'/'
  text=text.replace('</head>',f'<meta property="og:url" content="{origin}{page}"/></head>');p.write_text(text)
 print('Prepared static host metadata and routes for',origin)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--origin',required=True);p.add_argument('--output',type=__import__('pathlib').Path,required=True);a=p.parse_args();main(a.origin,a.output)
