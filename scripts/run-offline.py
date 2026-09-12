"""Serve the frozen offline demo on this computer; no network research is performed."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
import os, argparse, errno
os.chdir(Path(__file__).resolve().parent)
class Handler(SimpleHTTPRequestHandler):
 def do_GET(self):
  route=urlsplit(self.path).path
  if route=='/explore' or route.startswith('/explore/'):
   self.path='/index.html'
  super().do_GET()
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8000);args=parser.parse_args()
 try: server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
 except OSError as error:
  if error.errno!=errno.EADDRINUSE:raise
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
 print(f'Open http://127.0.0.1:{server.server_address[1]} — Ctrl+C stops the offline demo.',flush=True)
 server.serve_forever()
