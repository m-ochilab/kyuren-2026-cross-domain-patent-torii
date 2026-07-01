from __future__ import annotations

import csv
import json
import re
import zipfile
from collections import OrderedDict
from pathlib import Path
from xml.etree.ElementTree import iterparse


DOWNLOADS = Path("/Users/h-torii4649/Downloads")
OUTPUT_DIR = Path("pipeline/data/raw_heterogeneous")
XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

GROUPS: dict[str, list[str]] = {
    "C0": [f"C0 異分野 {i:02d}.xlsx" for i in range(1, 14)],
    "C1": ["C1 異分野.xlsx"],
    "S0": [f"S0 異分野 {i:02d}.xlsx" for i in range(1, 5)],
    "S1": ["S1 異分野 01.xlsx"],
}


def strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalize_header(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip()


def make_unique_headers(headers: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    result: list[str] = []
    for idx, header in enumerate(headers, start=1):
        name = normalize_header(header) or f"unnamed_{idx}"
        counts[name] = counts.get(name, 0) + 1
        if counts[name] > 1:
            name = f"{name}_{counts[name]}"
        result.append(name)
    return result


def column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref)
    if not letters:
        return 0
    index = 0
    for char in letters.group(0):
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def data_sheet_info(zf: zipfile.ZipFile) -> tuple[str, str]:
    workbook_xml = zf.read("xl/workbook.xml")
    rels_xml = zf.read("xl/_rels/workbook.xml.rels")

    sheets: list[tuple[str, str]] = []
    for _, elem in iterparse_bytes(workbook_xml):
        if strip_ns(elem.tag) == "sheet":
            name = elem.attrib.get("name", "Sheet1")
            rel_id = elem.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id",
                "",
            )
            sheets.append((name, rel_id))

    rel_targets: dict[str, str] = {}
    for _, elem in iterparse_bytes(rels_xml):
        if strip_ns(elem.tag) == "Relationship":
            rel_targets[elem.attrib.get("Id", "")] = elem.attrib.get("Target", "")

    sheet_name, rel_id = next(
        (item for item in sheets if item[0].lower() == "results"),
        sheets[0] if sheets else ("Sheet1", ""),
    )
    target = rel_targets.get(rel_id, "worksheets/sheet1.xml")
    if target.startswith("/"):
        target = target.lstrip("/")
    elif not target.startswith("xl/"):
        target = f"xl/{target}"
    return sheet_name, target


def iterparse_bytes(data: bytes):
    from io import BytesIO

    yield from iterparse(BytesIO(data), events=("end",))


def shared_string_text(elem) -> str:
    texts: list[str] = []
    for child in elem.iter():
        if strip_ns(child.tag) == "t" and child.text is not None:
            texts.append(child.text)
    return "".join(texts)


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []

    strings: list[str] = []
    with zf.open("xl/sharedStrings.xml") as fp:
        for _, elem in iterparse(fp, events=("end",)):
            if strip_ns(elem.tag) == "si":
                strings.append(shared_string_text(elem))
                elem.clear()
    return strings


def cell_text(cell, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(".//main:is", XML_NS)
        return shared_string_text(inline) if inline is not None else ""

    value_elem = cell.find("main:v", XML_NS)
    if value_elem is None or value_elem.text is None:
        return ""

    value = value_elem.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return value
    if cell_type == "b":
        return "TRUE" if value == "1" else "FALSE"
    return value


def iter_xlsx_rows(path: Path):
    with zipfile.ZipFile(path) as zf:
        sheet_name, sheet_path = data_sheet_info(zf)
        shared_strings = load_shared_strings(zf)
        with zf.open(sheet_path) as fp:
            for _, elem in iterparse(fp, events=("end",)):
                if strip_ns(elem.tag) != "row":
                    continue
                values_by_col: dict[int, str] = {}
                max_col = -1
                for cell in elem:
                    if strip_ns(cell.tag) != "c":
                        continue
                    ref = cell.attrib.get("r", "")
                    col = column_index(ref)
                    max_col = max(max_col, col)
                    values_by_col[col] = cell_text(cell, shared_strings)
                row = [values_by_col.get(i, "") for i in range(max_col + 1)]
                elem.clear()
                yield sheet_name, row


def read_header(path: Path) -> tuple[str, list[str], int]:
    try:
        sheet_name, row = next(iter_xlsx_rows(path))
    except StopIteration:
        return "Sheet1", [], 0
    return sheet_name, make_unique_headers(row), 0


def collect_headers(paths: list[Path]) -> list[str]:
    ordered: OrderedDict[str, None] = OrderedDict()
    for path in paths:
        _, headers, _ = read_header(path)
        for header in headers:
            ordered.setdefault(header, None)
    return list(ordered)


def write_group_csv(group: str, filenames: list[str]) -> dict[str, object]:
    paths = [DOWNLOADS / name for name in filenames]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing input files for {group}: {missing}")

    headers = collect_headers(paths)
    output_path = OUTPUT_DIR / f"{group}_heterogeneous_publication_level.csv"
    row_count = 0
    file_summaries = []

    with output_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["source_group", "source_file", "source_sheet", *headers],
            extrasaction="ignore",
        )
        writer.writeheader()

        for path in paths:
            rows = iter_xlsx_rows(path)
            try:
                sheet_name, header_row = next(rows)
            except StopIteration:
                continue
            file_headers = make_unique_headers(header_row)

            written_for_file = 0
            for _, values in rows:
                if not any(value != "" for value in values):
                    continue
                record = dict(zip(file_headers, values, strict=False))
                record["source_group"] = group
                record["source_file"] = path.name
                record["source_sheet"] = sheet_name
                writer.writerow(record)
                written_for_file += 1

            file_summaries.append(
                {
                    "file": path.name,
                    "sheet": sheet_name,
                    "data_rows": written_for_file,
                    "columns": len(file_headers),
                }
            )
            row_count += written_for_file

    return {
        "group": group,
        "output": str(output_path),
        "input_files": len(paths),
        "data_rows": row_count,
        "columns": len(headers) + 3,
        "files": file_summaries,
    }


def write_all_csv(group_outputs: list[dict[str, object]]) -> dict[str, object]:
    group_paths = [Path(item["output"]) for item in group_outputs]
    all_headers: OrderedDict[str, None] = OrderedDict()

    for path in group_paths:
        with path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.reader(fp)
            header = next(reader)
            for column in header:
                all_headers.setdefault(column, None)

    output_path = OUTPUT_DIR / "heterogeneous_publication_level_all.csv"
    row_count = 0
    with output_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(all_headers), extrasaction="ignore")
        writer.writeheader()
        for path in group_paths:
            with path.open("r", encoding="utf-8-sig", newline="") as group_fp:
                reader = csv.DictReader(group_fp)
                for row in reader:
                    writer.writerow(row)
                    row_count += 1

    return {
        "group": "ALL",
        "output": str(output_path),
        "input_files": len(group_paths),
        "data_rows": row_count,
        "columns": len(all_headers),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    group_outputs = [write_group_csv(group, names) for group, names in GROUPS.items()]
    all_output = write_all_csv(group_outputs)
    summary = {
        "groups": group_outputs,
        "combined_all": all_output,
    }
    summary_path = OUTPUT_DIR / "merge_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
