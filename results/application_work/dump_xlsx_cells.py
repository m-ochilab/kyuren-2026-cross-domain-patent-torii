from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from lxml import etree


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def shared_strings(zf: zipfile.ZipFile) -> list[str]:
    root = etree.fromstring(zf.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall("main:si", NS):
        out.append("".join(t.text or "" for t in si.findall(".//main:t", NS)))
    return out


def cell_text(c, shared: list[str]) -> str:
    t = c.get("t")
    if t == "s":
        v = c.find("main:v", NS)
        return shared[int(v.text)] if v is not None and v.text is not None else ""
    if t == "inlineStr":
        return "".join(n.text or "" for n in c.findall(".//main:t", NS))
    v = c.find("main:v", NS)
    if v is not None and v.text is not None:
        return v.text
    f = c.find("main:f", NS)
    if f is not None:
        return "=" + (f.text or "")
    return ""


def workbook_map(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    wb = etree.fromstring(zf.read("xl/workbook.xml"))
    rels = etree.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_by_id = {r.get("Id"): r.get("Target") for r in rels.findall("pkgrel:Relationship", NS)}
    sheets = []
    for s in wb.findall("main:sheets/main:sheet", NS):
        rid = s.get(f"{{{NS['rel']}}}id")
        target = rel_by_id[rid]
        if not target.startswith("xl/"):
            target = "xl/" + target
        sheets.append((s.get("name"), target))
    return sheets


def main() -> None:
    path = Path(sys.argv[1])
    sheet_index = int(sys.argv[2])
    with zipfile.ZipFile(path) as zf:
        shared = shared_strings(zf)
        sheets = workbook_map(zf)
        name, target = sheets[sheet_index - 1]
        root = etree.fromstring(zf.read(target))
        print(f"--- {sheet_index}: {name} ({target})")
        for row in root.findall(".//main:sheetData/main:row", NS):
            parts = []
            for c in row.findall("main:c", NS):
                value = cell_text(c, shared).replace("\n", "\\n")
                parts.append(f"{c.get('r')}[s={c.get('s')},t={c.get('t')}]:{value[:80]}")
            if parts:
                print(" | ".join(parts))


if __name__ == "__main__":
    main()
