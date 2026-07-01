#!/bin/bash
# 特許データ抽出メインスクリプト
set -e

WORKDIR="/Users/h-torii4649/Downloads/sotsuron_latex_set"
DATADIR="/Users/h-torii4649/Downloads"
TMPDIR="/tmp/sotsuron_extract"
mkdir -p "$TMPDIR"

cd "$WORKDIR"

decompress_part() {
    # $1: xlsx path, $2: start offset, $3: size, $4: output path
    python3 -c "
import zlib, sys

path, offset, size, out_path = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
d = zlib.decompressobj(-15)
CHUNK = 16 * 1024 * 1024
with open(path, 'rb') as fin, open(out_path, 'wb') as fout:
    fin.seek(offset)
    remaining = size
    while remaining > 0:
        data = fin.read(min(CHUNK, remaining))
        remaining -= len(data)
        try: fout.write(d.decompress(data))
        except zlib.error: break
" "$1" "$2" "$3" "$4"
}

get_offsets() {
    # $1: xlsx path
    python3 -c "
import struct, os, sys

path = sys.argv[1]
file_size = os.path.getsize(path)
with open(path, 'rb') as f:
    buf = f.read(10000)
    pos = 0
    while pos < len(buf) - 30:
        if buf[pos:pos+4] != b'PK\x03\x04':
            pos += 1; continue
        csize = struct.unpack_from('<I', buf, pos+18)[0]
        nlen  = struct.unpack_from('<H', buf, pos+26)[0]
        elen  = struct.unpack_from('<H', buf, pos+28)[0]
        name  = buf[pos+30:pos+30+nlen].decode()
        dstart = pos + 30 + nlen + elen
        if csize > 0:
            print(f'{name}\t{dstart}\t{csize}')
            next_pos = dstart + csize
            if next_pos > len(buf):
                f.seek(next_pos)
                nb = f.read(200)
                if nb[:4] == b'PK\x03\x04':
                    nlen2 = struct.unpack_from('<H', nb, 26)[0]
                    elen2 = struct.unpack_from('<H', nb, 28)[0]
                    csize2 = struct.unpack_from('<I', nb, 18)[0]
                    name2 = nb[30:30+nlen2].decode()
                    ds2 = next_pos + 30 + nlen2 + elen2
                    print(f'{name2}\t{ds2}\t{file_size - ds2 if csize2==0 else csize2}')
                break
            pos = next_pos
        else:
            nxt = buf.find(b'PK\x03\x04', pos+4)
            sz = (nxt - dstart) if nxt != -1 else (file_size - dstart)
            print(f'{name}\t{dstart}\t{sz}')
            if nxt == -1: break
            pos = nxt
" "$1"
}

find_unet_indices() {
    # $1: sharedStrings.xml path, $2: output indices file
    echo "  Streaming U-Net index search..."
    python3 "$WORKDIR/find_unet_indices.py" "$1" "$2"
}

process_label() {
    LABEL=$1
    XLSX="$DATADIR/${2}"
    echo ""
    echo "========================================"
    echo "$LABEL: $2"
    echo "========================================"

    # Get offsets
    echo "Getting file offsets..."
    OFFSETS=$(get_offsets "$XLSX")

    SS_START=$(echo "$OFFSETS" | grep 'xl/sharedStrings.xml' | awk '{print $2}')
    SS_SIZE=$(echo "$OFFSETS" | grep 'xl/sharedStrings.xml' | awk '{print $3}')
    SH_START=$(echo "$OFFSETS" | grep 'xl/worksheets/sheet2.xml' | awk '{print $2}')
    SH_SIZE=$(echo "$OFFSETS" | grep 'xl/worksheets/sheet2.xml' | awk '{print $3}')

    echo "  sharedStrings: start=$SS_START size=$SS_SIZE"
    echo "  sheet2: start=$SH_START size=$SH_SIZE"

    # Decompress sharedStrings
    SS_TMP="$TMPDIR/${LABEL}_ss.xml"
    echo "Decompressing sharedStrings ($(( SS_SIZE / 1024 / 1024 ))MB compressed)..."
    decompress_part "$XLSX" "$SS_START" "$SS_SIZE" "$SS_TMP"
    echo "  -> $(du -sh $SS_TMP | awk '{print $1}')"

    # Find U-Net indices
    UNET_IDX="$TMPDIR/${LABEL}_unet_indices.txt"
    find_unet_indices "$SS_TMP" "$UNET_IDX"
    rm "$SS_TMP"

    # Decompress sheet2
    SH_TMP="$TMPDIR/${LABEL}_sheet2.xml"
    echo "Decompressing sheet2 ($(( SH_SIZE / 1024 / 1024 ))MB compressed)..."
    decompress_part "$XLSX" "$SH_START" "$SH_SIZE" "$SH_TMP"
    echo "  -> $(du -sh $SH_TMP | awk '{print $1}')"

    # Parse sheet2
    CSV_OUT="$WORKDIR/${LABEL}_data.csv"
    echo "Parsing sheet2.xml..."
    python3 "$WORKDIR/parse_sheet2.py" "$SH_TMP" "$UNET_IDX" "$CSV_OUT"
    rm "$SH_TMP"

    echo "CSV saved: $CSV_OUT ($(wc -l < $CSV_OUT) lines)"
}

process_label "A0" "A0_Core_combined.xlsx"
process_label "B0" "B0_Core_combined.xlsx"

# Analyze results
echo ""
echo "========================================"
echo "Analyzing results..."
echo "========================================"
python3 "$WORKDIR/analyze_results.py"
echo "Done!"
