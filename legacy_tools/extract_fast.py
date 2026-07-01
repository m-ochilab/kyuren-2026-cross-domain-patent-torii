#!/usr/bin/env python3
"""
高速特許データ抽出スクリプト v3
- sharedStrings: gzip展開→grep でU-Netインデックス検出
- sheet2: gzip展開→awk で B列がある行のみCSV抽出
"""
import zlib, re, struct, sys, datetime, json, subprocess, os
from pathlib import Path
from collections import Counter

def excel_to_year(serial_str):
    try:
        s = int(float(serial_str))
        if s <= 0: return None
        if s > 59: s -= 1
        d = datetime.date(1899, 12, 31) + datetime.timedelta(days=s)
        return d.year
    except:
        return None

def get_offsets(path):
    file_size = os.path.getsize(path)
    offsets = {}
    with open(path, 'rb') as f:
        buf = f.read(10000)
        pos = 0
        while pos < len(buf) - 30:
            if buf[pos:pos+4] != b'PK\x03\x04':
                pos += 1
                continue
            csize  = struct.unpack_from('<I', buf, pos+18)[0]
            nlen   = struct.unpack_from('<H', buf, pos+26)[0]
            elen   = struct.unpack_from('<H', buf, pos+28)[0]
            name   = buf[pos+30:pos+30+nlen].decode('utf-8', errors='replace')
            dstart = pos + 30 + nlen + elen
            if csize > 0:
                offsets[name] = (dstart, csize)
                next_pos = dstart + csize
                if next_pos > len(buf):
                    f.seek(next_pos)
                    nb = f.read(200)
                    if nb[:4] == b'PK\x03\x04':
                        nlen2  = struct.unpack_from('<H', nb, 26)[0]
                        elen2  = struct.unpack_from('<H', nb, 28)[0]
                        csize2 = struct.unpack_from('<I', nb, 18)[0]
                        name2  = nb[30:30+nlen2].decode('utf-8', errors='replace')
                        dstart2 = next_pos + 30 + nlen2 + elen2
                        offsets[name2] = (dstart2, file_size - dstart2 if csize2 == 0 else csize2)
                    break
                pos = next_pos
            else:
                nxt = buf.find(b'PK\x03\x04', pos+4)
                offsets[name] = (dstart, (nxt - dstart) if nxt != -1 else (file_size - dstart))
                if nxt == -1: break
                pos = nxt
    return offsets

def decompress_file(src_path, offset, size, out_path):
    d = zlib.decompressobj(-15)
    CHUNK = 16 * 1024 * 1024
    with open(src_path, 'rb') as fin, open(out_path, 'wb') as fout:
        fin.seek(offset)
        remaining = size
        while remaining > 0:
            data = fin.read(min(CHUNK, remaining))
            remaining -= len(data)
            try: fout.write(d.decompress(data))
            except zlib.error: break

def find_unet_indices(ss_path):
    print('  grep U-Net...', flush=True)
    r = subprocess.run(['grep', '-n', '-iE', 'U-Net|UNet', ss_path],
                       capture_output=True, text=True)
    grep_lines = [l for l in r.stdout.strip().split('\n') if ':' in l]
    print(f'  {len(grep_lines)} lines found', flush=True)
    target_lines = sorted({int(l.split(':')[0]) for l in grep_lines})

    unet_indices = set()
    si_count = 0
    line_num  = 0
    t_idx = 0
    SI_END = b'</si>'

    with open(ss_path, 'rb') as f:
        for raw in f:
            line_num += 1
            si_count += raw.count(SI_END)
            if t_idx < len(target_lines) and line_num == target_lines[t_idx]:
                unet_indices.add(si_count - 1)
                t_idx += 1
                if t_idx >= len(target_lines):
                    break

    print(f'  {len(unet_indices)} U-Net indices', flush=True)
    return unet_indices

def parse_sheet2_fast(sh_path, unet_indices):
    """Parse decompressed sheet2.xml using streaming byte search for B-column rows"""
    print('  Scanning sheet2.xml...', flush=True)

    file_size = os.path.getsize(sh_path)
    CHUNK = 32 * 1024 * 1024  # 32MB

    records = []
    buf = b''
    total_rows = 0
    patent_rows = 0

    with open(sh_path, 'rb') as f:
        while True:
            data = f.read(CHUNK)
            if not data:
                break
            buf += data

            # Process complete rows
            while True:
                rs = buf.find(b'<row ')
                re_ = buf.find(b'</row>', rs if rs >= 0 else 0)
                if rs < 0 or re_ < 0:
                    last = buf.rfind(b'<row ')
                    buf = buf[last:] if last >= 0 else b''
                    break

                row = buf[rs:re_+6]
                buf = buf[re_+6:]
                total_rows += 1

                r_m = row.find(b'<row r="')
                if r_m < 0:
                    continue
                r_end = row.find(b'"', r_m+8)
                try:
                    r_num = int(row[r_m+8:r_end])
                except:
                    continue
                if r_num <= 2:
                    continue

                # Fast check: must have B column
                if b'<c r="B' not in row:
                    continue

                # Extract B, D, E, I, J columns
                cells = {}
                pos = 0
                while True:
                    c_start = row.find(b'<c r="', pos)
                    if c_start < 0:
                        break
                    col_start = c_start + 6
                    col_end = col_start
                    while col_end < len(row) and row[col_end:col_end+1].isalpha():
                        col_end += 1
                    col = row[col_start:col_end]
                    if col in (b'B', b'D', b'E', b'I', b'J'):
                        v_start = row.find(b'<v>', c_start)
                        v_end   = row.find(b'</v>', v_start) if v_start >= 0 else -1
                        c_close = row.find(b'</c>', c_start)
                        if v_start >= 0 and v_end >= 0 and (c_close < 0 or v_start < c_close):
                            cells[col] = row[v_start+3:v_end]
                    pos = row.find(b'</c>', c_start)
                    if pos < 0:
                        pos = c_start + 6

                if b'B' not in cells:
                    continue

                patent_rows += 1
                year = excel_to_year(cells[b'D'].decode()) if b'D' in cells else None
                fam  = cells.get(b'E', b'').decode()

                is_unet = False
                for col in (b'I', b'J'):
                    if col in cells:
                        try:
                            if int(cells[col]) in unet_indices:
                                is_unet = True
                                break
                        except:
                            pass

                records.append({'family_idx': fam, 'year': year, 'is_unet': is_unet})

            if patent_rows % 2000 == 0 and patent_rows > 0:
                print(f'    {patent_rows} patents ({total_rows} rows)', flush=True)

    print(f'  Done: {len(records)} patents / {total_rows} rows', flush=True)
    return records

def analyze(records, label):
    total = len(records)
    unet_n = sum(1 for r in records if r['is_unet'])
    all_fam  = {r['family_idx'] for r in records if r['family_idx']}
    unet_fam = {r['family_idx'] for r in records if r['is_unet'] and r['family_idx']}

    yr_total = Counter(r['year'] for r in records if r['year'])
    yr_unet  = Counter(r['year'] for r in records if r['is_unet'] and r['year'])

    print(f'\n{label} Summary:')
    print(f'  Publications: {total}, U-Net: {unet_n} ({unet_n/total*100:.2f}%)')
    print(f'  Families: {len(all_fam)}, U-Net families: {len(unet_fam)} ({len(unet_fam)/len(all_fam)*100:.2f}%)')
    for yr in sorted(yr_total):
        t, u = yr_total[yr], yr_unet.get(yr, 0)
        print(f'  {yr}: total={t}, unet={u}, rate={u/t*100:.2f}%')

    return {
        'total': total, 'unet': unet_n,
        'families': len(all_fam), 'unet_families': len(unet_fam),
        'year_total': {str(k): v for k, v in yr_total.items()},
        'year_unet':  {str(k): v for k, v in yr_unet.items()},
    }

if __name__ == '__main__':
    tmp_dir = Path('/tmp/sotsuron_extract')
    tmp_dir.mkdir(exist_ok=True)
    out_dir = Path('/Users/h-torii4649/Downloads/sotsuron_latex_set')
    results = {}

    for label, filename in [('A0', 'A0_Core_combined.xlsx'), ('B0', 'B0_Core_combined.xlsx')]:
        src = str(Path('/Users/h-torii4649/Downloads') / filename)
        print(f'\n{"="*50}\n{label}: {filename}\n{"="*50}')

        offsets = get_offsets(src)
        ss_start, ss_size = offsets['xl/sharedStrings.xml']
        sh_start, sh_size = offsets['xl/worksheets/sheet2.xml']

        # Decompress sharedStrings
        ss_tmp = str(tmp_dir / f'{label}_ss.xml')
        print(f'  Decompressing sharedStrings ({ss_size//1024//1024}MB)...', flush=True)
        decompress_file(src, ss_start, ss_size, ss_tmp)
        print(f'  -> {os.path.getsize(ss_tmp)//1024//1024}MB', flush=True)

        unet_indices = find_unet_indices(ss_tmp)
        os.remove(ss_tmp)

        # Decompress sheet2
        sh_tmp = str(tmp_dir / f'{label}_sheet2.xml')
        print(f'  Decompressing sheet2 ({sh_size//1024//1024}MB)...', flush=True)
        decompress_file(src, sh_start, sh_size, sh_tmp)
        print(f'  -> {os.path.getsize(sh_tmp)//1024//1024}MB', flush=True)

        records = parse_sheet2_fast(sh_tmp, unet_indices)
        os.remove(sh_tmp)

        out_path = out_dir / f'{label}_records.json'
        with open(out_path, 'w') as f:
            json.dump(records, f)

        stats = analyze(records, label)
        results[label] = stats

    summary_path = out_dir / 'experiment_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'\nSaved: {summary_path}')
