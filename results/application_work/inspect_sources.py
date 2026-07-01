from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pdfplumber
from lxml import etree


BASE = Path("/Users/h-torii4649/Downloads/公募要領･申請書類フォーマット(第２回用)")
OUT = Path("application_work/inspect_outputs")
OUT.mkdir(parents=True, exist_ok=True)


def inspect_xlsx(path: Path) -> dict:
    ns = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(path) as zf:
        workbook = etree.fromstring(zf.read("xl/workbook.xml"))
        rels = etree.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        shared_xml = etree.fromstring(zf.read("xl/sharedStrings.xml"))
        shared_strings = []
        for si in shared_xml.findall("main:si", ns):
            texts = si.findall(".//main:t", ns)
            shared_strings.append("".join(t.text or "" for t in texts))

        rel_by_id = {
            rel.get("Id"): rel.get("Target")
            for rel in rels.findall("pkgrel:Relationship", ns)
        }

        result = {"path": str(path), "sheets": []}
        for sheet_node in workbook.findall("main:sheets/main:sheet", ns):
            title = sheet_node.get("name")
            rel_id = sheet_node.get(f"{{{ns['rel']}}}id")
            target = rel_by_id[rel_id]
            if not target.startswith("xl/"):
                target = "xl/" + target
            ws_xml = etree.fromstring(zf.read(target))
            dimension = ws_xml.find("main:dimension", ns)
            merged = [
                node.get("ref")
                for node in ws_xml.findall("main:mergeCells/main:mergeCell", ns)
            ]
            sheet = {
                "title": title,
                "target": target,
                "dimension": dimension.get("ref") if dimension is not None else None,
                "merged_ranges": merged,
                "non_empty": [],
            }
            for c in ws_xml.findall(".//main:c", ns):
                value = cell_text(c, shared_strings, ns)
                if value is None or value == "":
                    continue
                sheet["non_empty"].append(
                    {
                        "cell": c.get("r"),
                        "style": c.get("s"),
                        "type": c.get("t"),
                        "value": value.replace("\n", "\\n")[:500],
                    }
                )
            result["sheets"].append(sheet)
    return result


def cell_text(c, shared_strings: list[str], ns: dict[str, str]) -> str | None:
    cell_type = c.get("t")
    if cell_type == "s":
        v = c.find("main:v", ns)
        if v is None or v.text is None:
            return None
        return shared_strings[int(v.text)]
    if cell_type == "inlineStr":
        texts = c.findall(".//main:t", ns)
        return "".join(t.text or "" for t in texts)
    v = c.find("main:v", ns)
    if v is not None:
        return v.text
    f = c.find("main:f", ns)
    if f is not None:
        return "=" + (f.text or "")
    return None


def extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = etree.fromstring(xml)
    lines: list[str] = []
    for para in root.findall(".//w:p", ns):
        texts = [node.text or "" for node in para.findall(".//w:t", ns)]
        line = "".join(texts).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def extract_pdf_text(path: Path, max_pages: int = 8) -> str:
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages], start=1):
            text = page.extract_text() or ""
            text = re.sub(r"\n{3,}", "\n\n", text)
            chunks.append(f"--- page {i} ---\n{text}")
    return "\n\n".join(chunks)


def main() -> None:
    xlsx_paths = sorted(BASE.glob("*.xlsx"))
    docx_paths = sorted(BASE.glob("*.docx"))
    pdf_paths = sorted(BASE.glob("*.pdf"))

    for path in xlsx_paths:
        out = OUT / f"{path.stem}_inspection.json"
        out.write_text(json.dumps(inspect_xlsx(path), ensure_ascii=False, indent=2), encoding="utf-8")

    for path in docx_paths:
        out = OUT / f"{path.stem}_text.txt"
        out.write_text(extract_docx_text(path), encoding="utf-8")

    for path in pdf_paths:
        out = OUT / f"{path.stem}_first_pages.txt"
        out.write_text(extract_pdf_text(path), encoding="utf-8")

    print(f"wrote inspections to {OUT}")


if __name__ == "__main__":
    main()
