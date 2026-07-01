#!/usr/bin/env python3
"""
Build publication-level CSV files from split Orbis IP Excel exports.

The Orbis "Results" sheet stores one publication across multiple rows when
multi-valued fields such as CPC, IPC, citations, or owners are present. This
script normalizes those rows into one row per Publication number and keeps
Title, Abstract, and Claims as plain text for downstream LLM extraction.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import re
import sys
import zipfile
from collections import OrderedDict
from pathlib import Path
from xml.etree import ElementTree as ET


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

HEADERS = [
    "",
    "Publication number",
    "Application number",
    "Application/filing date",
    "Family Identifier (Simple)",
    "Family Identifier (Extended)",
    "Publication date",
    "Priority date",
    "Title",
    "Abstract",
    "Applicant(s) name(s)",
    "Applicant(s) BvD ID Number(s)",
    "CPC code (main)",
    "CPC code (others)",
    "IPC code (main)",
    "IPC code (others)",
    "Number of backward citations",
    "Backward citations",
    "Backward citations type",
    "Forward citations",
    "Claims",
    "Current direct owner(s) name(s)",
]

OUTPUT_COLUMNS = [
    "domain",
    "publication_number",
    "application_number",
    "filing_date",
    "filing_year",
    "family_id_simple",
    "family_id_extended",
    "publication_date",
    "priority_date",
    "title",
    "abstract",
    "claims",
    "applicant_names",
    "applicant_bvd_ids",
    "cpc_main",
    "cpc_others",
    "ipc_main",
    "ipc_others",
    "number_of_backward_citations",
    "backward_citations",
    "backward_citation_types",
    "forward_citations",
    "current_direct_owners",
    "is_unet_title_abstract",
    "is_unet_claims",
    "is_unet_full_text",
    "is_unet_final",
    "is_unet",
    "source_files",
]

SINGULAR_FIELDS = {
    "publication_number",
    "application_number",
    "filing_date",
    "filing_year",
    "family_id_simple",
    "family_id_extended",
    "publication_date",
    "priority_date",
    "number_of_backward_citations",
}

LIST_FIELDS = {
    "title",
    "abstract",
    "claims",
    "applicant_names",
    "applicant_bvd_ids",
    "cpc_main",
    "cpc_others",
    "ipc_main",
    "ipc_others",
    "backward_citations",
    "backward_citation_types",
    "forward_citations",
    "current_direct_owners",
    "source_files",
}

UNET_RE = re.compile(r"\b(?:U\s*-\s*Net|U\s+Net|UNet|nnU\s*-\s*Net|U\s*-\s*Net\+\+|UNet\+\+)\b", re.I)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def col_idx(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return -1
    idx = 0
    for ch in match.group(1):
        idx = idx * 26 + ord(ch) - 64
    return idx - 1


def excel_serial_to_date(value: str) -> tuple[str, str]:
    try:
        serial = int(float(value))
    except (TypeError, ValueError):
        return "", ""
    if serial <= 0:
        return "", ""
    if serial > 59:
        serial -= 1
    date = dt.date(1899, 12, 31) + dt.timedelta(days=serial)
    return date.isoformat(), str(date.year)


def clean_text(value: str) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = TAG_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text).strip()
    return text


def add_unique(record: dict[str, object], field: str, value: str) -> None:
    value = clean_text(value)
    if not value:
        return
    values = record[field]
    assert isinstance(values, list)
    if value not in values:
        values.append(value)


def set_once(record: dict[str, object], field: str, value: str) -> None:
    if value and not record[field]:
        record[field] = value


def new_record(domain: str) -> dict[str, object]:
    rec: dict[str, object] = {col: "" for col in OUTPUT_COLUMNS}
    rec["domain"] = domain
    for field in LIST_FIELDS:
        rec[field] = []
    rec["is_unet_title_abstract"] = "0"
    rec["is_unet_claims"] = "0"
    rec["is_unet_full_text"] = "0"
    rec["is_unet_final"] = "0"
    rec["is_unet"] = "0"
    return rec


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    values: list[str] = []
    with zf.open("xl/sharedStrings.xml") as fp:
        for _event, elem in ET.iterparse(fp, events=("end",)):
            if elem.tag == NS + "si":
                values.append("".join(t.text or "" for t in elem.findall(".//" + NS + "t")))
                elem.clear()
    return values


def workbook_sheets(zf: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheets: dict[str, str] = {}
    for sheet in workbook.findall(".//" + NS + "sheet"):
        name = sheet.attrib["name"]
        rid = sheet.attrib[REL_NS + "id"]
        target = rid_to_target[rid]
        sheets[name] = "xl/" + target if not target.startswith("/") else target[1:]
    return sheets


def cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//" + NS + "t"))
    value = cell.find(NS + "v")
    if value is None or value.text is None:
        return ""
    raw = value.text
    if cell_type == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return raw
    return raw


def iter_sheet_rows(zf: zipfile.ZipFile, sheet_path: str, shared: list[str]):
    with zf.open(sheet_path) as fp:
        for _event, elem in ET.iterparse(fp, events=("end",)):
            if elem.tag != NS + "row":
                continue
            row_number = int(elem.attrib.get("r", "0") or 0)
            row: dict[str, str] = {}
            for cell in elem.findall(NS + "c"):
                idx = col_idx(cell.attrib.get("r", ""))
                if 0 <= idx < len(HEADERS):
                    row[HEADERS[idx]] = cell_value(cell, shared)
            yield row_number, row
            elem.clear()


def merge_row(record: dict[str, object], row: dict[str, str], source_file: str) -> None:
    add_unique(record, "source_files", source_file)

    pub = clean_text(row.get("Publication number", ""))
    if pub:
        set_once(record, "publication_number", pub)
    set_once(record, "application_number", clean_text(row.get("Application number", "")))
    set_once(record, "family_id_simple", clean_text(row.get("Family Identifier (Simple)", "")))
    set_once(record, "family_id_extended", clean_text(row.get("Family Identifier (Extended)", "")))

    filing_date, filing_year = excel_serial_to_date(row.get("Application/filing date", ""))
    pub_date, _ = excel_serial_to_date(row.get("Publication date", ""))
    priority_date, _ = excel_serial_to_date(row.get("Priority date", ""))
    set_once(record, "filing_date", filing_date)
    set_once(record, "filing_year", filing_year)
    set_once(record, "publication_date", pub_date)
    set_once(record, "priority_date", priority_date)
    set_once(record, "number_of_backward_citations", clean_text(row.get("Number of backward citations", "")))

    mapping = {
        "Title": "title",
        "Abstract": "abstract",
        "Claims": "claims",
        "Applicant(s) name(s)": "applicant_names",
        "Applicant(s) BvD ID Number(s)": "applicant_bvd_ids",
        "CPC code (main)": "cpc_main",
        "CPC code (others)": "cpc_others",
        "IPC code (main)": "ipc_main",
        "IPC code (others)": "ipc_others",
        "Backward citations": "backward_citations",
        "Backward citations type": "backward_citation_types",
        "Forward citations": "forward_citations",
        "Current direct owner(s) name(s)": "current_direct_owners",
    }
    for source, target in mapping.items():
        add_unique(record, target, row.get(source, ""))

    title_abstract_text = " ".join(
        " ".join(record[field]) if isinstance(record[field], list) else str(record[field])
        for field in ("title", "abstract")
    )
    claims_text = " ".join(record["claims"]) if isinstance(record["claims"], list) else str(record["claims"])
    full_text = f"{title_abstract_text} {claims_text}"

    if UNET_RE.search(title_abstract_text):
        record["is_unet_title_abstract"] = "1"
    if UNET_RE.search(claims_text):
        record["is_unet_claims"] = "1"
    if UNET_RE.search(full_text):
        record["is_unet_full_text"] = "1"

    # Default final判定は卒論本文の主集計に合わせてTitle/Abstract由来にする。
    if record["is_unet_title_abstract"] == "1":
        record["is_unet_final"] = "1"
        record["is_unet"] = "1"


def finalize_record(record: dict[str, object]) -> dict[str, str]:
    out: dict[str, str] = {}
    for col in OUTPUT_COLUMNS:
        value = record[col]
        if col in LIST_FIELDS:
            assert isinstance(value, list)
            sep = "\n\n" if col in {"abstract", "claims"} else "; "
            out[col] = sep.join(value)
        else:
            out[col] = str(value)
    return out


def build_domain_csv(domain: str, files: list[Path], out_path: Path) -> dict[str, int]:
    records: OrderedDict[str, dict[str, object]] = OrderedDict()
    duplicate_rows = 0
    total_pub_rows = 0

    for file_path in files:
        if not zipfile.is_zipfile(file_path):
            raise RuntimeError(f"Not a valid xlsx/zip file: {file_path}")

        print(f"[{domain}] reading {file_path.name}", flush=True)
        with zipfile.ZipFile(file_path) as zf:
            shared = load_shared_strings(zf)
            sheets = workbook_sheets(zf)
            if "Results" not in sheets:
                raise RuntimeError(f"Results sheet not found: {file_path}")

            current_pub = ""
            for row_number, row in iter_sheet_rows(zf, sheets["Results"], shared):
                if row_number <= 2:
                    continue
                pub = clean_text(row.get("Publication number", ""))
                if pub:
                    total_pub_rows += 1
                    current_pub = pub
                    if pub in records:
                        duplicate_rows += 1
                    else:
                        records[pub] = new_record(domain)
                if not current_pub:
                    continue
                merge_row(records[current_pub], row, file_path.name)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for record in records.values():
            writer.writerow(finalize_record(record))

    return {
        "publication_rows_seen": total_pub_rows,
        "unique_publications": len(records),
        "duplicate_publication_rows": duplicate_rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build A0/B0 publication-level CSVs from split Orbis xlsx files.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument(
        "--source-dir",
        default="source_data/orbis_exports/split",
        help="Directory containing split Orbis Excel exports.",
    )
    parser.add_argument("--out-dir", default="pipeline/data/raw", help="Output directory for CSV files")
    parser.add_argument(
        "--domains",
        nargs="+",
        choices=["A0", "A1", "B0", "B1"],
        default=["A0", "B0"],
        help="Domains to build. Defaults to A0 B0.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    source_dir = (root / args.source_dir).resolve()
    out_dir = (root / args.out_dir).resolve()

    domain_files = {
        "A0": sorted(source_dir.glob("A0-Core *.xlsx")),
        "A1": sorted(source_dir.glob("A1-Core*.xlsx")),
        "B0": sorted(source_dir.glob("B0-Core *.xlsx")),
        "B1": sorted(source_dir.glob("B1-Core*.xlsx")),
    }

    for domain in args.domains:
        files = domain_files[domain]
        if not files:
            print(f"[ERROR] No files found for {domain}", file=sys.stderr)
            return 1
        out_path = out_dir / f"{domain}_orbis_publication_level.csv"
        stats = build_domain_csv(domain, files, out_path)
        print(f"[{domain}] saved {out_path}")
        print(f"[{domain}] {stats}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
