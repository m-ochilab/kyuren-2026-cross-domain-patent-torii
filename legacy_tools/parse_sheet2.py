#!/usr/bin/env python3
"""
sheet2.xml を高速スキャンして特許データを抽出する（改訂版）
特許ブロック全体（B列のある行 + 続く行すべて）でU-Netを検索する
"""
import sys, re, datetime

def excel_to_year(serial_str):
    try:
        s = int(float(serial_str))
        if s <= 0: return ''
        if s > 59: s -= 1
        d = datetime.date(1899, 12, 31) + datetime.timedelta(days=s)
        return str(d.year)
    except:
        return ''

def extract_cell(row, col_bytes):
    """Extract <v>...</v> value for given column letter(s) from a row bytes.
    Correctly handles self-closing empty cells like <c r="B4" s="3"/>."""
    tag = b'<c r="' + col_bytes
    pos = row.find(tag)
    if pos < 0:
        return None

    # Find the end of the opening tag (the first '>' after pos)
    open_tag_end = row.find(b'>', pos)
    if open_tag_end < 0:
        return None

    # Check if it's self-closing (char before '>' is '/')
    if row[open_tag_end - 1:open_tag_end] == b'/':
        return None  # Self-closing cell, no value

    # Find the closing </c> tag
    cc = row.find(b'</c>', open_tag_end)
    if cc < 0:
        return None

    # Look for <v>...</v> within the cell bounds [open_tag_end, cc]
    vs = row.find(b'<v>', open_tag_end)
    if vs < 0 or vs >= cc:
        return None
    ve = row.find(b'</v>', vs)
    if ve < 0 or ve >= cc:
        return None
    return row[vs+3:ve]

def get_v_value(row, col_bytes):
    """Get numeric/string index value for column"""
    v = extract_cell(row, col_bytes)
    return v.decode() if v else None

def check_unet_in_row(row, unet_indices, check_cols=(b'I', b'J', b'U')):
    """Check if any target column in this row references a U-Net string"""
    for col in check_cols:
        v = get_v_value(row, col)
        if v:
            try:
                if int(v) in unet_indices:
                    return True
            except:
                pass
    return False

def main(sheet_path, unet_indices_path, out_path):
    with open(unet_indices_path) as f:
        unet_indices = set(int(x.strip()) for x in f if x.strip())

    print(f'Loaded {len(unet_indices)} U-Net indices', flush=True)

    ROW_START = b'<row '
    ROW_END   = b'</row>'
    B_TAG     = b'<c r="B'

    row_count     = 0
    patent_count  = 0

    # Current patent state
    cur_year  = ''
    cur_fam   = ''
    cur_unet  = False
    in_patent = False

    with open(sheet_path, 'rb') as fin, open(out_path, 'w') as fout:
        fout.write('year,family_idx,is_unet\n')

        buf = bytearray()
        CHUNK = 64 * 1024 * 1024  # 64MB

        def flush_patent():
            nonlocal in_patent
            if in_patent:
                fout.write(f'{cur_year},{cur_fam},{"1" if cur_unet else "0"}\n')
                in_patent = False

        while True:
            data = fin.read(CHUNK)
            if data:
                buf.extend(data)

            start = 0
            while True:
                rs = buf.find(ROW_START, start)
                if rs < 0:
                    buf = buf[start:]
                    start = 0
                    break
                re_ = buf.find(ROW_END, rs)
                if re_ < 0:
                    if rs > 0:
                        del buf[:rs]
                    start = 0
                    break

                row_end = re_ + len(ROW_END)
                row = bytes(buf[rs:row_end])
                start = row_end
                row_count += 1

                # Get row number, skip header rows
                r_m = row.find(b'<row r="')
                if r_m >= 0:
                    r_end_q = row.find(b'"', r_m+8)
                    try:
                        r_num = int(row[r_m+8:r_end_q])
                        if r_num <= 2:
                            continue
                    except:
                        continue

                # Check if B column has an actual value (not just an empty styled cell)
                b_val = get_v_value(row, b'B') if B_TAG in row else None
                has_b = b_val is not None

                if has_b:
                    # New patent block: flush previous
                    flush_patent()
                    patent_count += 1
                    in_patent = True

                    # Extract year and family ID from this main row
                    d_val = get_v_value(row, b'D')
                    e_val = get_v_value(row, b'E')
                    cur_year  = excel_to_year(d_val) if d_val else ''
                    cur_fam   = e_val or ''
                    cur_unet  = False

                    if patent_count % 5000 == 0:
                        print(f'  {patent_count} patents / {row_count} rows', flush=True)

                # Check U-Net in this row (both main and continuation rows)
                if in_patent and not cur_unet:
                    if check_unet_in_row(row, unet_indices, (b'I', b'J')):
                        cur_unet = True

            if start > 0:
                del buf[:start]

            if not data:
                flush_patent()
                break

    print(f'Done: {patent_count} patents / {row_count} rows', flush=True)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
