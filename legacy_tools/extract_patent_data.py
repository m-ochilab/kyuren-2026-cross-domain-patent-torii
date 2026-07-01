#!/usr/bin/env python3
"""
特許データ抽出スクリプト - 高速版
シークベースで xlsxファイルから直接データを抽出する
"""
import zlib, re, struct, sys, datetime, json
from pathlib import Path

UNET_RE = re.compile(rb'U[-\s]?Net', re.IGNORECASE)

def excel_serial_to_year(serial_str):
    try:
        serial = int(float(serial_str))
        if serial <= 0:
            return None
        if serial > 59:
            serial -= 1
        d = datetime.date(1899, 12, 31) + datetime.timedelta(days=serial)
        return d.year
    except:
        return None

def find_file_offsets(path):
    """Find offsets of files in the xlsx (zip) archive using file seeks"""
    offsets = {}
    with open(path, 'rb') as f:
        data = f.read(300000)  # Read only first 300KB for header scanning

    pos = 0
    while pos < len(data) - 30:
        if data[pos:pos+4] == b'PK\x03\x04':
            compression = struct.unpack_from('<H', data, pos+8)[0]
            compressed_size = struct.unpack_from('<I', data, pos+18)[0]
            name_len = struct.unpack_from('<H', data, pos+26)[0]
            extra_len = struct.unpack_from('<H', data, pos+28)[0]
            name = data[pos+30:pos+30+name_len].decode('utf-8', errors='replace')
            data_start = pos + 30 + name_len + extra_len
            offsets[name] = (data_start, compressed_size, compression)
            if compressed_size > 0:
                pos = data_start + compressed_size
            else:
                nxt = data.find(b'PK\x03\x04', pos+4)
                if nxt == -1:
                    break
                offsets[name] = (data_start, nxt - data_start, compression)
                pos = nxt
        else:
            pos += 1
    return offsets

def find_unet_indices_fast(path, ss_start, ss_size):
    """Find sharedStrings indices containing U-Net by text scanning decompressed data"""
    print('  Finding U-Net string indices...', flush=True)

    CHUNK = 16 * 1024 * 1024  # 16MB compressed chunks
    unet_indices = set()
    si_count = 0

    d = zlib.decompressobj(-15)
    buffer = b''

    with open(path, 'rb') as f:
        f.seek(ss_start)
        processed = 0

        while processed < ss_size:
            to_read = min(CHUNK, ss_size - processed)
            compressed = f.read(to_read)
            processed += len(compressed)

            try:
                decompressed = d.decompress(compressed)
            except zlib.error:
                break

            buffer += decompressed

            # Process complete <si>...</si> blocks
            # Count </si> to track index, search for U-Net
            search_pos = 0
            while True:
                si_start_pos = buffer.find(b'<si>', search_pos)
                si_end_pos = buffer.find(b'</si>', si_start_pos if si_start_pos >= 0 else 0)

                if si_start_pos == -1 or si_end_pos == -1:
                    # Keep from last <si> onwards
                    last = buffer.rfind(b'<si>')
                    buffer = buffer[last:] if last >= 0 else b''
                    break

                si_block = buffer[si_start_pos:si_end_pos+5]
                if UNET_RE.search(si_block):
                    unet_indices.add(si_count)

                si_count += 1
                search_pos = si_end_pos + 5
                buffer = buffer[si_end_pos + 5:]
                search_pos = 0

            if si_count % 200000 == 0 and si_count > 0:
                print(f'    {si_count} strings, {len(unet_indices)} U-Net found', flush=True)

    print(f'  Done: {si_count} total strings, {len(unet_indices)} contain U-Net', flush=True)
    return unet_indices

def parse_sheet2_records(path, sheet_start, sheet_size, unet_indices):
    """Parse sheet2.xml and extract patent records"""
    print('  Parsing sheet2.xml...', flush=True)

    CHUNK = 16 * 1024 * 1024
    d = zlib.decompressobj(-15)
    buffer = b''
    records = []
    row_count = 0
    patent_rows = 0

    # Column letters to look for
    COLS_NEEDED = {b'B', b'D', b'E', b'I', b'J'}

    with open(path, 'rb') as f:
        f.seek(sheet_start)
        processed = 0

        while processed < sheet_size:
            to_read = min(CHUNK, sheet_size - processed)
            compressed = f.read(to_read)
            processed += len(compressed)

            try:
                decompressed = d.decompress(compressed)
            except zlib.error:
                break

            buffer += decompressed

            # Process complete rows
            while True:
                row_start = buffer.find(b'<row ')
                row_end = buffer.find(b'</row>', row_start if row_start >= 0 else 0)

                if row_start == -1 or row_end == -1:
                    last = buffer.rfind(b'<row ')
                    buffer = buffer[last:] if last >= 0 else b''
                    break

                row_xml = buffer[row_start:row_end+6]
                buffer = buffer[row_end+6:]
                row_count += 1

                # Skip header rows
                r_match = re.search(rb'<row r="(\d+)"', row_xml)
                if not r_match or int(r_match.group(1)) <= 2:
                    continue

                # Quick check: does this row have a B column value?
                if b'<c r="B' not in row_xml:
                    continue

                # Extract cells
                cells = {}
                for m in re.finditer(rb'<c r="([A-Z]+)\d+"[^>]*>(?:<v>([^<]*)</v>)?', row_xml):
                    col, val = m.group(1), m.group(2)
                    if col in COLS_NEEDED and val:
                        cells[col] = val

                if b'B' not in cells:
                    continue

                patent_rows += 1

                year = None
                if b'D' in cells:
                    year = excel_serial_to_year(cells[b'D'].decode())

                family_idx = cells.get(b'E', b'').decode()

                is_unet = False
                for col in (b'I', b'J'):
                    if col in cells:
                        try:
                            idx = int(cells[col])
                            if idx in unet_indices:
                                is_unet = True
                                break
                        except:
                            pass

                records.append({
                    'family_idx': family_idx,
                    'year': year,
                    'is_unet': is_unet,
                })

            if patent_rows % 5000 == 0 and patent_rows > 0:
                print(f'    {patent_rows} patents from {row_count} rows', flush=True)

    print(f'  Done: {len(records)} patent records from {row_count} rows', flush=True)
    return records

def extract_from_xlsx(path):
    print(f'Extracting from {Path(path).name}...', flush=True)
    offsets = find_file_offsets(path)

    ss_start, ss_size, _ = offsets['xl/sharedStrings.xml']
    unet_indices = find_unet_indices_fast(path, ss_start, ss_size)

    sheet_start, sheet_size, _ = offsets['xl/worksheets/sheet2.xml']
    records = parse_sheet2_records(path, sheet_start, sheet_size, unet_indices)

    return records

def analyze(records, label):
    total = len(records)
    unet_total = sum(1 for r in records if r['is_unet'])

    # Unique family IDs
    all_families = set(r['family_idx'] for r in records if r['family_idx'])
    unet_families = set(r['family_idx'] for r in records if r['is_unet'] and r['family_idx'])

    print(f'\n{label} Summary:')
    print(f'  Total publications: {total}')
    print(f'  U-Net publications: {unet_total} ({unet_total/total*100:.2f}%)')
    print(f'  Total family IDs: {len(all_families)}')
    print(f'  U-Net family IDs: {len(unet_families)} ({len(unet_families)/len(all_families)*100:.2f}%)')

    # By year
    from collections import Counter
    year_total = Counter(r['year'] for r in records if r['year'])
    year_unet = Counter(r['year'] for r in records if r['is_unet'] and r['year'])

    print(f'\n  Year breakdown:')
    for yr in sorted(year_total.keys()):
        t = year_total[yr]
        u = year_unet.get(yr, 0)
        print(f'    {yr}: total={t}, unet={u}, rate={u/t*100:.2f}%')

    return {
        'total': total, 'unet': unet_total,
        'families': len(all_families), 'unet_families': len(unet_families),
        'year_total': dict(year_total), 'year_unet': dict(year_unet),
    }

if __name__ == '__main__':
    results = {}

    for label, filename in [('A0', 'A0_Core_combined.xlsx'), ('B0', 'B0_Core_combined.xlsx')]:
        path = str(Path('/Users/h-torii4649/Downloads') / filename)
        print(f'\n{"="*50}')
        print(f'Processing {label}: {filename}')
        print('='*50)

        records = extract_from_xlsx(path)

        # Save raw records
        out_path = Path('/Users/h-torii4649/Downloads/sotsuron_latex_set') / f'{label}_records.json'
        with open(out_path, 'w') as f:
            json.dump(records, f)

        stats = analyze(records, label)
        results[label] = stats

    # Save summary
    summary_path = Path('/Users/h-torii4649/Downloads/sotsuron_latex_set') / 'experiment_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'\nSummary saved to {summary_path}')
