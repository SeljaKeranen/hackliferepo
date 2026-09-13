"""Batch and judgment storage.

A batch is the set of grants shown to labellers. A judgment is one person's
answer on one grant. Every labeller sees every grant in the batch -- overlap
is the point, because inter-rater agreement is the thing Andrew needs and it
cannot be computed from a partitioned queue.

Judgments are stored per grant as a LIST, never merged or averaged. Five
researchers disagreeing is the finding, not a problem to resolve on write.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List

LABEL_DIR = Path(__file__).resolve().parent
BATCH_DIR = LABEL_DIR / "batches"
JUDGMENT_DIR = LABEL_DIR / "judgments"

# Batch ids and labeller ids end up in filenames, so keep them boring.
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def is_slug(value: str) -> bool:
    return isinstance(value, str) and bool(SLUG_RE.fullmatch(value))


def atomic_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def record_fingerprint(record: dict) -> str:
    """Hash of what the labeller actually read. If the batch text is later
    edited, existing judgments are visibly stale rather than quietly
    reattributed to different words."""
    core = json.dumps(
        [record.get("record_id"), record.get("title"), record.get("abstract")],
        ensure_ascii=False,
    )
    return hashlib.sha256(core.encode("utf-8")).hexdigest()[:16]


def list_batches() -> List[str]:
    if not BATCH_DIR.is_dir():
        return []
    return sorted(
        p.stem for p in BATCH_DIR.glob("*.json") if is_slug(p.stem)
    )


def batch_path(batch_id: str) -> Path:
    return BATCH_DIR / f"{batch_id}.json"


def judgments_path(batch_id: str) -> Path:
    return JUDGMENT_DIR / f"{batch_id}.judgments.json"


def load_batch(batch_id: str) -> dict:
    return load_json(batch_path(batch_id), {})


def load_judgments(batch_id: str) -> Dict[str, list]:
    data = load_json(judgments_path(batch_id), {})
    return data if isinstance(data, dict) else {}


def save_judgment(batch_id: str, record_id: str, judgment: dict) -> Dict[str, list]:
    """Adds or replaces one labeller's judgment on one grant, leaving every
    other labeller's judgment on that grant untouched. Raises on an
    unreadable file rather than overwriting evidence with {}."""
    path = judgments_path(batch_id)
    if path.exists():
        existing = load_json(path, None)
        if not isinstance(existing, dict):
            raise ValueError(
                f"{path} is unreadable; fix it by hand before saving more judgments"
            )
    else:
        existing = {}
    entries = [
        e for e in existing.get(record_id, [])
        if isinstance(e, dict) and e.get("labeller_id") != judgment["labeller_id"]
    ]
    entries.append(judgment)
    existing[record_id] = entries
    atomic_write_json(path, existing)
    return existing
