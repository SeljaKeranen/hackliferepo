"""Package only the current static instrument, without raw corpora or ratios."""
import argparse
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def package(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Choose a new output directory; existing files are never overwritten')
    packet = json.loads((HERE / 'output/packet.json').read_text())
    predictions = json.loads((HERE / 'output/predictions.json').read_text())
    if packet['packet_id'] != predictions['packet_id']:
        raise ValueError('Source and prediction versions differ; rebuild before packaging')
    # Explicit allowlist; never copy a repository tree or human storage.
    paths = ['index.html', 'ratio/index.html', 'ratio/benchmark/sheet.html',
             'ratio/instrument/app.mjs', 'ratio/instrument/review.mjs',
             'ratio/instrument/style.css', 'ratio/instrument/taxonomy.json',
             'ratio/instrument/output/packet.json', 'ratio/instrument/output/predictions.json',
             'ratio/instrument/output/audit.json', 'ratio/INSTRUMENT.md',
             'ratio/data/funnel.json', 'data/Track3_C2/output/DATA_LICENCES.md']
    for relative in paths:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (destination / 'vercel.json').write_text(json.dumps({'version': 2, 'framework': None,
        'cleanUrls': False, 'headers': [{'source': '/(.*)', 'headers': [
            {'key': 'X-Content-Type-Options', 'value': 'nosniff'},
            {'key': 'Referrer-Policy', 'value': 'strict-origin-when-cross-origin'}]}]}, indent=2) + '\n')
    print(json.dumps({'directory': str(destination), 'packet_id': packet['packet_id'], 'files': len(paths),
                      'human_labels_included': False, 'funding_results_included': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    package(parser.parse_args().directory)
