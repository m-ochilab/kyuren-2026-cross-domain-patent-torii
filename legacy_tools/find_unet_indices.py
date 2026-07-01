#!/usr/bin/env python3
"""
sharedStrings.xmlをストリーム解析してU-Netを含む文字列のインデックスを見つける
（XMLは1行形式の可能性があるため行番号方式は使わない）
"""
import sys, re

UNET_RE = re.compile(rb'U-Net|UNet|nnU-Net|U-Net\+\+|UNet\+\+', re.IGNORECASE)

def find_unet_indices(ss_xml_path, out_path):
    SI_OPEN  = b'<si>'
    SI_CLOSE = b'</si>'

    unet_indices = []
    idx = 0
    buf = bytearray()
    CHUNK = 32 * 1024 * 1024  # 32MB

    with open(ss_xml_path, 'rb') as f:
        while True:
            data = f.read(CHUNK)
            if data:
                buf.extend(data)

            while True:
                si_s = buf.find(SI_OPEN)
                si_e = buf.find(SI_CLOSE, si_s if si_s >= 0 else 0)

                if si_s < 0 or si_e < 0:
                    # Keep from last <si>
                    last = buf.rfind(SI_OPEN)
                    if last > 0:
                        del buf[:last]
                    elif si_s < 0:
                        buf.clear()
                    break

                si_content = bytes(buf[si_s:si_e + len(SI_CLOSE)])

                if UNET_RE.search(si_content):
                    unet_indices.append(idx)

                idx += 1
                del buf[:si_e + len(SI_CLOSE)]

                if idx % 200000 == 0:
                    print(f'  {idx} strings processed, {len(unet_indices)} U-Net found', flush=True)

            if not data:
                break

    print(f'  Total: {idx} strings, {len(unet_indices)} U-Net indices', flush=True)

    with open(out_path, 'w') as f:
        for i in unet_indices:
            f.write(f'{i}\n')

if __name__ == '__main__':
    find_unet_indices(sys.argv[1], sys.argv[2])
