#!/usr/bin/env python3
"""Build the current four-label instrument or compare versioned human exports.

The older JSONL benchmark and taxonomy remain in Git history. They are not
silently converted into current human evidence. No final PASS/FAIL is issued
from the already inspected development corpus.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('sheet', help='Build the source-bound four-category review packet')
    score = commands.add_parser('score', help='Compare each human reviewer and overlapping pairs')
    score.add_argument('--labels', nargs='+', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'sheet':
        from ratio.instrument.build import build
        build()
        print('Open /ratio/#label; /ratio/benchmark/sheet.html redirects there.')
        return 0
    return subprocess.run(['node', str(ROOT / 'ratio/instrument/score.mjs'),
                           *[str(p.resolve()) for p in args.labels]], cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
