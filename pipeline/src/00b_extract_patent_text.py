#!/usr/bin/env python3
"""
特許テキスト（タイトル・アブストラクト）を xlsx から抽出する

処理フロー:
  Step1: sheet2.xml をストリーム解析 → 各特許の Title(I列) / Abstract(J列) 文字列インデックスを収集
  Step2: sharedStrings.xml をストリーム解析 → 必要なインデックスのテキストを取得
  Step3: 結合して CSV 出力（サンプリングオプション付き）

入力: config.yaml の a0_xlsx / b0_xlsx
出力:
  data/processed/A0_with_text.csv
  data/processed/B0_with_text.csv

使用方法:
  python src/00b_extract_patent_text.py --config config/config.yaml
  python src/00b_extract_patent_text.py --config config/config.yaml --sample 2000
"""

import argparse
import datetime
import html
import logging
import os
import re
import struct
import sys
import zlib
from pathlib import Path

import yaml

# ─── ログ設定 ─────────────────────────────────────────────────
LOG_FMT = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def setup_dirs(config: dict) -> Path:
    base = Path(config["data"]["processed_dir"])
    base.mkdir(parents=True, exist_ok=True)
    log_dir = Path(config["data"]["output_dir"]) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return base


# ─── xlsx 内部ファイルのオフセット取得 ──────────────────────────────
def get_offsets(xlsx_path: str) -> dict:
    file_size = os.path.getsize(xlsx_path)
    offsets = {}
    with open(xlsx_path, "rb") as f:
        buf = f.read(10000)
        pos = 0
        while pos < len(buf) - 30:
            if buf[pos : pos + 4] != b"PK\x03\x04":
                pos += 1
                continue
            csize = struct.unpack_from("<I", buf, pos + 18)[0]
            nlen = struct.unpack_from("<H", buf, pos + 26)[0]
            elen = struct.unpack_from("<H", buf, pos + 28)[0]
            name = buf[pos + 30 : pos + 30 + nlen].decode("utf-8", errors="replace")
            dstart = pos + 30 + nlen + elen
            if csize > 0:
                offsets[name] = (dstart, csize)
                next_pos = dstart + csize
                if next_pos > len(buf):
                    f.seek(next_pos)
                    nb = f.read(200)
                    if nb[:4] == b"PK\x03\x04":
                        nlen2 = struct.unpack_from("<H", nb, 26)[0]
                        elen2 = struct.unpack_from("<H", nb, 28)[0]
                        csize2 = struct.unpack_from("<I", nb, 18)[0]
                        name2 = nb[30 : 30 + nlen2].decode("utf-8", errors="replace")
                        ds2 = next_pos + 30 + nlen2 + elen2
                        offsets[name2] = (ds2, file_size - ds2 if csize2 == 0 else csize2)
                    break
                pos = next_pos
            else:
                nxt = buf.find(b"PK\x03\x04", pos + 4)
                offsets[name] = (dstart, (nxt - dstart) if nxt != -1 else (file_size - dstart))
                if nxt == -1:
                    break
                pos = nxt
    return offsets


# ─── セル値抽出 ─────────────────────────────────────────────────
def extract_cell_value(row: bytes, col_bytes: bytes) -> bytes | None:
    tag = b'<c r="' + col_bytes
    pos = row.find(tag)
    if pos < 0:
        return None
    open_tag_end = row.find(b">", pos)
    if open_tag_end < 0:
        return None
    if row[open_tag_end - 1 : open_tag_end] == b"/":
        return None  # 自己閉じタグ
    cc = row.find(b"</c>", open_tag_end)
    if cc < 0:
        return None
    vs = row.find(b"<v>", open_tag_end)
    if vs < 0 or vs >= cc:
        return None
    ve = row.find(b"</v>", vs)
    if ve < 0 or ve >= cc:
        return None
    return row[vs + 3 : ve]


def excel_to_year(serial_str: str) -> int | None:
    try:
        s = int(float(serial_str))
        if s <= 0:
            return None
        if s > 59:
            s -= 1
        import datetime
        d = datetime.date(1899, 12, 31) + datetime.timedelta(days=s)
        return d.year
    except Exception:
        return None


# ─── Step1: sheet2 から文字列インデックスを収集 ────────────────────────
def collect_string_indices(
    xlsx_path: str,
    sheet_offset: int,
    sheet_size: int,
    sample_n: int | None = None,
    seed: int = 42,
) -> tuple[list[dict], set[int]]:
    """
    sheet2.xml をストリーム解析して各特許の
    B(pub), D(year), E(family), I(title_idx), J(abstract_idx) を収集する
    """
    import random
    rng = random.Random(seed)

    CHUNK = 8 * 1024 * 1024
    d = zlib.decompressobj(-15)
    buf = bytearray()
    records = []
    needed_indices = set()
    row_count = 0

    cur_year = None
    cur_fam = None
    cur_is_unet = False
    cur_title_idx = None
    cur_abstract_idx = None
    in_patent = False

    UNET_RE = re.compile(rb"U-?Net|UNet|nnU-?Net", re.IGNORECASE)

    with open(xlsx_path, "rb") as f:
        f.seek(sheet_offset)
        remaining = sheet_size

        while remaining > 0:
            to_read = min(CHUNK, remaining)
            compressed = f.read(to_read)
            remaining -= len(compressed)
            try:
                buf.extend(d.decompress(compressed))
            except zlib.error:
                break

            while True:
                rs = buf.find(b"<row ")
                re_ = buf.find(b"</row>", rs if rs >= 0 else 0)
                if rs < 0 or re_ < 0:
                    last = buf.rfind(b"<row ")
                    if last > 0:
                        del buf[:last]
                    break

                row = bytes(buf[rs : re_ + 6])
                del buf[: re_ + 6]
                row_count += 1

                # 行番号確認
                r_m = row.find(b'<row r="')
                if r_m >= 0:
                    r_end = row.find(b'"', r_m + 8)
                    try:
                        r_num = int(row[r_m + 8 : r_end])
                        if r_num <= 2:
                            continue
                    except Exception:
                        continue

                # B列があるかチェック（非空値）
                b_val = None
                if b'<c r="B' in row:
                    b_val = extract_cell_value(row, b"B")

                if b_val is not None:
                    # 前の特許を保存
                    if in_patent and cur_fam is not None:
                        records.append(
                            {
                                "family_idx": cur_fam,
                                "year": cur_year,
                                "is_unet": int(cur_is_unet),
                                "title_idx": cur_title_idx,
                                "abstract_idx": cur_abstract_idx,
                            }
                        )
                        if cur_title_idx is not None:
                            needed_indices.add(cur_title_idx)
                        if cur_abstract_idx is not None:
                            needed_indices.add(cur_abstract_idx)

                    # 新しい特許を開始
                    in_patent = True
                    d_val = extract_cell_value(row, b"D")
                    e_val = extract_cell_value(row, b"E")
                    cur_year = excel_to_year(d_val.decode()) if d_val else None
                    cur_fam = e_val.decode() if e_val else None
                    cur_is_unet = False
                    cur_title_idx = None
                    cur_abstract_idx = None

                # I列とJ列のインデックスを取得
                if in_patent:
                    for col_b, attr in [(b"I", "title_idx"), (b"J", "abstract_idx")]:
                        v = extract_cell_value(row, col_b)
                        if v:
                            try:
                                idx = int(v)
                                if attr == "title_idx" and cur_title_idx is None:
                                    cur_title_idx = idx
                                elif attr == "abstract_idx" and cur_abstract_idx is None:
                                    cur_abstract_idx = idx
                            except Exception:
                                pass

                    # U-Netフラグ（ルールベースでチェック）
                    if not cur_is_unet:
                        if UNET_RE.search(row):
                            cur_is_unet = True

            if row_count % 50000 == 0 and row_count > 0:
                log.info(f"  sheet2 行処理: {row_count}行, 特許候補: {len(records)}")

        # 最後の特許
        if in_patent and cur_fam is not None:
            records.append(
                {
                    "family_idx": cur_fam,
                    "year": cur_year,
                    "is_unet": int(cur_is_unet),
                    "title_idx": cur_title_idx,
                    "abstract_idx": cur_abstract_idx,
                }
            )
            if cur_title_idx is not None:
                needed_indices.add(cur_title_idx)
            if cur_abstract_idx is not None:
                needed_indices.add(cur_abstract_idx)

    log.info(f"  sheet2 完了: {len(records)}件, 必要インデックス: {len(needed_indices)}")

    # サンプリング
    if sample_n and len(records) > sample_n:
        log.info(f"  サンプリング: {len(records)} → {sample_n}")
        # U-Net特許を優先して含める
        unet_recs = [r for r in records if r["is_unet"]]
        non_unet_recs = [r for r in records if not r["is_unet"]]
        n_unet = min(len(unet_recs), sample_n // 3)
        n_non = sample_n - n_unet
        sampled = unet_recs[:n_unet] + rng.sample(non_unet_recs, min(n_non, len(non_unet_recs)))
        # 必要なインデックスを再計算
        needed_indices = set()
        for r in sampled:
            if r["title_idx"] is not None:
                needed_indices.add(r["title_idx"])
            if r["abstract_idx"] is not None:
                needed_indices.add(r["abstract_idx"])
        records = sampled
        log.info(f"  サンプリング後: {len(records)}件 (U-Net: {n_unet}, 非U-Net: {len(records)-n_unet})")

    return records, needed_indices


# ─── Step2: sharedStrings から必要なテキストを取得 ──────────────────────
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_XML_ENTITIES = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'"
}

def clean_text(raw: bytes) -> str:
    """HTML/XML タグを除去してプレーンテキストに変換"""
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        return ""
    # XML エンティティをデコード
    text = html.unescape(text)
    # HTMLタグを除去
    text = _HTML_TAG_RE.sub(" ", text)
    # 連続空白を正規化
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2000]  # 最大2000文字


def resolve_string_indices(
    xlsx_path: str,
    ss_offset: int,
    ss_size: int,
    needed_indices: set[int],
) -> dict[int, str]:
    """sharedStrings.xml をストリーム解析して必要なインデックスのテキストを返す"""
    log.info(f"  sharedStrings 解析中 ({ss_size//1024//1024}MB圧縮) ...")

    CHUNK = 16 * 1024 * 1024
    SI_OPEN = b"<si>"
    SI_CLOSE = b"</si>"

    result = {}
    idx = 0
    buf = bytearray()
    d = zlib.decompressobj(-15)

    sorted_needed = sorted(needed_indices)
    max_needed = sorted_needed[-1] if sorted_needed else -1

    with open(xlsx_path, "rb") as f:
        f.seek(ss_offset)
        remaining = ss_size

        while remaining > 0 and idx <= max_needed:
            to_read = min(CHUNK, remaining)
            compressed = f.read(to_read)
            remaining -= len(compressed)
            try:
                buf.extend(d.decompress(compressed))
            except zlib.error:
                break

            while True:
                si_s = buf.find(SI_OPEN)
                si_e = buf.find(SI_CLOSE, si_s if si_s >= 0 else 0)
                if si_s < 0 or si_e < 0:
                    last = buf.rfind(SI_OPEN)
                    if last > 0:
                        del buf[:last]
                    break

                si_content = bytes(buf[si_s : si_e + len(SI_CLOSE)])
                if idx in needed_indices:
                    result[idx] = clean_text(si_content)

                idx += 1
                del buf[: si_e + len(SI_CLOSE)]

                if idx > max_needed:
                    break

            if idx % 200000 == 0 and idx > 0:
                log.info(f"    {idx} strings処理済, 解決済: {len(result)}/{len(needed_indices)}")

    log.info(f"  sharedStrings 完了: {len(result)}/{len(needed_indices)} インデックス解決")
    return result


# ─── Step3: 結合と保存 ─────────────────────────────────────────────
def build_dataframe(records: list[dict], string_map: dict[int, str]):
    import pandas as pd
    rows = []
    for r in records:
        title = string_map.get(r["title_idx"], "") if r["title_idx"] is not None else ""
        abstract = string_map.get(r["abstract_idx"], "") if r["abstract_idx"] is not None else ""
        rows.append(
            {
                "family_idx": r["family_idx"],
                "year": r["year"],
                "is_unet": r["is_unet"],
                "title": title,
                "abstract": abstract,
                "title_abstract_text": (title + " " + abstract).strip(),
            }
        )
    return pd.DataFrame(rows)


# ─── メイン ─────────────────────────────────────────────────────
def process_domain(
    label: str,
    xlsx_path: str,
    out_dir: Path,
    sample_n: int | None,
    past_start: int,
    past_end: int,
):
    if not os.path.exists(xlsx_path):
        log.error(f"[{label}] xlsx が見つかりません: {xlsx_path}")
        return None

    log.info(f"\n=== {label}: {os.path.basename(xlsx_path)} ===")
    offsets = get_offsets(xlsx_path)

    if "xl/sharedStrings.xml" not in offsets or "xl/worksheets/sheet2.xml" not in offsets:
        log.error(f"[{label}] 必要なファイルが見つかりません: {list(offsets.keys())}")
        return None

    ss_start, ss_size = offsets["xl/sharedStrings.xml"]
    sh_start, sh_size = offsets["xl/worksheets/sheet2.xml"]

    # Step1: sheet2 からインデックス収集
    log.info(f"[{label}] Step1: sheet2 解析 ({sh_size//1024//1024}MB圧縮)...")
    records, needed_indices = collect_string_indices(
        xlsx_path, sh_start, sh_size, sample_n=sample_n
    )

    if not records:
        log.warning(f"[{label}] レコードが取得できませんでした")
        return None

    # Step2: sharedStrings からテキスト解決
    log.info(f"[{label}] Step2: {len(needed_indices)} インデックスを解決...")
    string_map = resolve_string_indices(xlsx_path, ss_start, ss_size, needed_indices)

    # Step3: DataFrame 構築
    import pandas as pd
    df = build_dataframe(records, string_map)

    # 年フィルタ
    if "year" in df.columns:
        df = df[df["year"].between(2015, 2024)]

    out_path = out_dir / f"{label}_with_text.csv"
    df.to_csv(out_path, index=False)
    log.info(f"[{label}] 保存: {out_path} ({len(df)}行)")

    # サマリー
    n_has_title = (df["title"].str.len() > 0).sum()
    n_has_abstract = (df["abstract"].str.len() > 0).sum()
    n_unet = df["is_unet"].sum()
    n_past = df[df["year"].between(past_start, past_end)].shape[0]
    log.info(
        f"  タイトルあり: {n_has_title}, アブストあり: {n_has_abstract}, "
        f"U-Net: {n_unet}, 過去期間: {n_past}"
    )

    return df


def main():
    parser = argparse.ArgumentParser(description="特許テキスト抽出スクリプト")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--sample", type=int, default=None, help="サンプル件数 (指定なし=全件)")
    parser.add_argument("--domain", choices=["A0", "B0", "both"], default="both")
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = setup_dirs(cfg)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(Path(cfg["data"]["output_dir"]) / "logs" / f"00b_extract_text_{ts}.log")
    fh.setFormatter(logging.Formatter(LOG_FMT))
    logging.getLogger().addHandler(fh)

    log.info("=== 00b_extract_patent_text.py 開始 ===")
    log.info(f"  sample={args.sample}, domain={args.domain}")

    past_start = cfg["periods"]["past_start"]
    past_end = cfg["periods"]["past_end"]
    sample_n = args.sample

    targets = []
    if args.domain in ("A0", "both"):
        targets.append(("A0", cfg["data"]["a0_xlsx"]))
    if args.domain in ("B0", "both"):
        targets.append(("B0", cfg["data"]["b0_xlsx"]))

    for label, xlsx_path in targets:
        process_domain(label, xlsx_path, out_dir, sample_n, past_start, past_end)

    log.info("=== 00b_extract_patent_text.py 完了 ===")


if __name__ == "__main__":
    main()
