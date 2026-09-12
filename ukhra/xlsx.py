"""Minimal stdlib XLSX reader.

openpyxl is not installed and this repo is stdlib-only (see
docs/funding-atlas-v2-migration.md's dependency decision). Streams
sharedStrings and worksheets via iterparse so a 58MB string table never
becomes a DOM. Supports exactly what ukhra_benchmark.py needs: shared
strings, inline strings, and raw numeric cells. No formulas, no dates
(Excel serial numbers are returned as-is), no styles.
"""
from __future__ import annotations

import re
import zipfile
from typing import Dict, Iterator, List
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def sheet_map(z: zipfile.ZipFile) -> Dict[str, str]:
    """{sheet name: worksheet path}, resolving rIds through workbook rels."""
    rels = {}
    for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
        target = rel.get("Target")
        if target.startswith("/"):
            target = target[1:]
        elif not target.startswith("xl/"):
            target = "xl/" + target
        rels[rel.get("Id")] = target
    return {
        sheet.get("name"): rels.get(sheet.get(f"{RNS}id"))
        for sheet in ET.fromstring(z.read("xl/workbook.xml")).iter(f"{NS}sheet")
    }


def shared_strings(z: zipfile.ZipFile) -> List[str]:
    strings: List[str] = []
    with z.open("xl/sharedStrings.xml") as fh:
        buf: List[str] = []
        for event, elem in ET.iterparse(fh, events=("end",)):
            if elem.tag == f"{NS}t":
                buf.append(elem.text or "")
            elif elem.tag == f"{NS}si":
                strings.append("".join(buf))
                buf = []
                elem.clear()
    return strings


def _col_index(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref or "A").group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def rows(z: zipfile.ZipFile, path: str, strings: List[str],
         limit: int = None) -> Iterator[List[str]]:
    """Yields each row as a list of cell values, padded out by column index
    so a row with gaps still aligns with the header row."""
    with z.open(path) as fh:
        count = 0
        for event, elem in ET.iterparse(fh, events=("end",)):
            if elem.tag != f"{NS}row":
                continue
            cells = {}
            for c in elem.iter(f"{NS}c"):
                idx = _col_index(c.get("r"))
                cell_type = c.get("t")
                if cell_type == "inlineStr":
                    node = c.find(f"{NS}is")
                    val = "".join(x.text or "" for x in node.iter(f"{NS}t")) if node is not None else ""
                else:
                    v = c.find(f"{NS}v")
                    val = v.text if v is not None and v.text is not None else ""
                    if cell_type == "s" and val != "":
                        val = strings[int(val)]
                cells[idx] = val
            width = (max(cells) + 1) if cells else 0
            yield [cells.get(i, "") for i in range(width)]
            elem.clear()
            count += 1
            if limit and count >= limit:
                return
