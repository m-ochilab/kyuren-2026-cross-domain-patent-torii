#!/usr/bin/env python3
"""
Build publication-level CSV files from Orbis exports2 Excel files.

The exports are split into C0/S0/C1/S1 workbooks. Orbis stores one patent
publication across multiple rows when text translations, classifications,
citations, or owners have multiple values. This script reads the Results sheet
directly from the xlsx XML, merges rows by Publication number, and writes one
row per publication for downstream thesis experiments.
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
    "applicant_country_codes",
    "cpc_main",
    "cpc_others",
    "ipc_main",
    "ipc_others",
    "number_of_backward_citations",
    "backward_citations",
    "backward_citation_types",
    "forward_citations",
    "forward_citation_types",
    "current_direct_owners",
    "is_unet_title_abstract",
    "is_unet_claims",
    "is_unet_full_text",
    "is_unet_final",
    "is_unet",
    "source_files",
]

LIST_FIELDS = {
    "title",
    "abstract",
    "claims",
    "applicant_names",
    "applicant_bvd_ids",
    "applicant_country_codes",
    "cpc_main",
    "cpc_others",
    "ipc_main",
    "ipc_others",
    "backward_citations",
    "backward_citation_types",
    "forward_citations",
    "forward_citation_types",
    "current_direct_owners",
    "source_files",
}

HEADER_TO_FIELD = {
    "Publication number": "publication_number",
    "Application number": "application_number",
    "Family Identifier (Simple)": "family_id_simple",
    "Family Identifier (Extended)": "family_id_extended",
    "Title": "title",
    "Abstract": "abstract",
    "Claims": "claims",
    "Applicant(s) name(s)": "applicant_names",
    "Applicant(s) BvD ID Number(s)": "applicant_bvd_ids",
    "Applicant(s) country code(s)": "applicant_country_codes",
    "CPC code (main)": "cpc_main",
    "CPC code (others)": "cpc_others",
    "IPC code (main)": "ipc_main",
    "IPC code (others)": "ipc_others",
    "Number of backward citations": "number_of_backward_citations",
    "Backward citations": "backward_citations",
    "Backward citations type": "backward_citation_types",
    "Forward citations": "forward_citations",
    "Forward citations type": "forward_citation_types",
    "Current direct owner(s) name(s)": "current_direct_owners",
}

DATE_HEADERS = {
    "Application/filing date": ("filing_date", "filing_year"),
    "Publication date": ("publication_date", None),
    "Priority date": ("priority_date", None),
}

UNET_RE = re.compile(
    r"\b(?:U\s*-\s*Net|U\s+Net|UNet|nnU\s*-\s*Net|U\s*-\s*Net\+\+|UNet\+\+)\b",
    re.IGNORECASE,
)
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
    if not value:
        return "", ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return value[:10], value[:4]
    try:
        serial = int(float(value))
    except (TypeError, ValueError):
        return "", ""
    if serial <= 0:
        return "", ""
    # Excel leap-year bug adjustment.
    if serial > 59:
        serial -= 1
    date = dt.date(1899, 12, 31) + dt.timedelta(days=serial)
    return date.isoformat(), str(date.year)


def clean_text(value: str) -> str:
    if not value:
        return ""
    text = html.unescape(str(value))
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
    value = clean_text(value)
    if value and not record[field]:
        record[field] = value


def new_record(domain: str) -> dict[str, object]:
    rec: dict[str, object] = {col: "" for col in OUTPUT_COLUMNS}
    rec["domain"] = domain
    for field in LIST_FIELDS:
        rec[field] = []
    for col in ["is_unet_title_abstract", "is_unet_claims", "is_unet_full_text", "is_unet_final", "is_unet"]:
        rec[col] = "0"
    return rec


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
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
            row: dict[int, str] = {}
            for cell in elem.findall(NS + "c"):
                idx = col_idx(cell.attrib.get("r", ""))
                if idx >= 0:
                    row[idx] = cell_value(cell, shared)
            yield row_number, row
            elem.clear()


def merge_row(record: dict[str, object], row: dict[str, str], source_file: str) -> None:
    add_unique(record, "source_files", source_file)

    for header, value in row.items():
        if header in DATE_HEADERS:
            date_field, year_field = DATE_HEADERS[header]
            date_value, year_value = excel_serial_to_date(value)
            set_once(record, date_field, date_value)
            if year_field:
                set_once(record, year_field, year_value)
            continue

        field = HEADER_TO_FIELD.get(header)
        if not field:
            continue
        if field in LIST_FIELDS:
            add_unique(record, field, value)
        else:
            set_once(record, field, value)

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
    duplicate_publication_starts = 0
    publication_starts_seen = 0
    data_rows_seen = 0

    for file_path in files:
        if not zipfile.is_zipfile(file_path):
            raise RuntimeError(f"Not a valid xlsx/zip file: {file_path}")

        print(f"[{domain}] reading {file_path.name}", flush=True)
        with zipfile.ZipFile(file_path) as zf:
            shared = load_shared_strings(zf)
            sheets = workbook_sheets(zf)
            if "Results" not in sheets:
                raise RuntimeError(f"Results sheet not found: {file_path}")

            header_by_idx: dict[int, str] = {}
            current_pub = ""
            for row_number, raw_row in iter_sheet_rows(zf, sheets["Results"], shared):
                if row_number == 1:
                    header_by_idx = {idx: clean_text(value) for idx, value in raw_row.items() if clean_text(value)}
                    continue
                if row_number == 2:
                    continue
                if not header_by_idx:
                    raise RuntimeError(f"Header row not found in Results sheet: {file_path}")

                row = {header_by_idx[idx]: value for idx, value in raw_row.items() if idx in header_by_idx}
                if not any(clean_text(v) for v in row.values()):
                    continue
                data_rows_seen += 1

                pub = clean_text(row.get("Publication number", ""))
                if pub:
                    publication_starts_seen += 1
                    current_pub = pub
                    if pub in records:
                        duplicate_publication_starts += 1
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
        "domain": domain,
        "source_file_count": len(files),
        "data_rows_seen": data_rows_seen,
        "publication_starts_seen": publication_starts_seen,
        "unique_publications": len(records),
        "duplicate_publication_starts": duplicate_publication_starts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build publication-level CSVs from Orbis exports2 xlsx files.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--source-dir", default="source_data/orbis_exports2", help="Directory containing exports2 Excel files")
    parser.add_argument("--out-dir", default="pipeline/data/raw_exports2", help="Output directory for CSV files")
    parser.add_argument(
        "--domains",
        nargs="+",
        choices=["C0", "C1", "S0", "S1"],
        default=["C0", "S0", "C1", "S1"],
        help="Domains to build",
    )
    return parser.parse_args()


def find_domain_files(source_dir: Path) -> dict[str, list[Path]]:
    return {
        "C0": sorted(source_dir.glob("C0*.xlsx")),
        "C1": sorted(source_dir.glob("C1*.xlsx")),
        "S0": sorted(source_dir.glob("S0*.xlsx")),
        "S1": sorted(source_dir.glob("S1*.xlsx")),
    }


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    source_dir = (root / args.source_dir).resolve()
    out_dir = (root / args.out_dir).resolve()
    domain_files = find_domain_files(source_dir)

    summary_rows: list[dict[str, int | str]] = []
    for domain in args.domains:
        files = domain_files[domain]
        if not files:
            print(f"[ERROR] No files found for {domain} in {source_dir}", file=sys.stderr)
            return 1
        out_path = out_dir / f"{domain}_orbis_publication_level.csv"
        stats = build_domain_csv(domain, files, out_path)
        summary_rows.append(stats)
        print(f"[{domain}] saved {out_path}")
        print(f"[{domain}] {stats}")

    summary_path = out_dir / "exports2_build_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as fp:
        fieldnames = [
            "domain",
            "source_file_count",
            "data_rows_seen",
            "publication_starts_seen",
            "unique_publications",
            "duplicate_publication_starts",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"summary saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
