"""
Script: 05_compute_domain_similarity.py
Purpose: A0とB0のドメイン間コサイン類似度を計算する。
         埋め込みが存在しない場合はスキップしてwarningを出力する。
Input:
  - outputs/embeddings/{domain}_{type}_embeddings.npy
  - outputs/embeddings/{domain}_metadata.csv
Output:
  - outputs/tables/domain_similarity_summary.csv
"""

import argparse
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore")


def cosine_similarity_mean(emb_a: np.ndarray, emb_b: np.ndarray) -> float:
    """2つの埋め込み行列の全ペア平均コサイン類似度を計算する。"""
    # ゼロベクトルを除外
    norm_a = np.linalg.norm(emb_a, axis=1, keepdims=True)
    norm_b = np.linalg.norm(emb_b, axis=1, keepdims=True)
    valid_a = (norm_a.flatten() > 1e-8)
    valid_b = (norm_b.flatten() > 1e-8)

    if valid_a.sum() == 0 or valid_b.sum() == 0:
        return float("nan")

    emb_a_valid = emb_a[valid_a]
    emb_b_valid = emb_b[valid_b]

    # 正規化
    emb_a_norm = emb_a_valid / np.linalg.norm(emb_a_valid, axis=1, keepdims=True)
    emb_b_norm = emb_b_valid / np.linalg.norm(emb_b_valid, axis=1, keepdims=True)

    # 平均コサイン類似度（全ペアの代わりに代表ベクトル法を使用）
    centroid_a = emb_a_norm.mean(axis=0)
    centroid_b = emb_b_norm.mean(axis=0)

    sim = float(np.dot(centroid_a, centroid_b) /
                (np.linalg.norm(centroid_a) * np.linalg.norm(centroid_b) + 1e-10))
    return sim


def load_embeddings_and_meta(emb_dir: Path, processed_dir: Path, domain: str, emb_type: str,
                              logger: logging.Logger):
    """埋め込みとメタデータを読み込む。失敗時はNoneを返す。"""
    emb_path = emb_dir / f"{domain}_{emb_type}_embeddings.npy"
    meta_path = emb_dir / f"{domain}_metadata.csv"

    if not emb_path.exists():
        logger.warning(f"埋め込みファイルが存在しません: {emb_path}")
        return None, None
    if not meta_path.exists():
        logger.warning(f"メタデータファイルが存在しません: {meta_path}")
        return None, None

    try:
        emb = np.load(emb_path)
        meta = pd.read_csv(meta_path)
        contexts_path = processed_dir / f"{domain}_contexts.csv"
        if contexts_path.exists():
            context_len = len(pd.read_csv(contexts_path, usecols=["publication_number"]))
            if len(meta) != context_len or len(emb) != context_len:
                logger.warning(
                    f"[{domain}/{emb_type}] 現在のcontexts.csvと件数が一致しないためスキップ: "
                    f"emb={len(emb)}, meta={len(meta)}, contexts={context_len}"
                )
                return None, None
        return emb, meta
    except Exception as e:
        logger.error(f"読み込みエラー: {e}")
        return None, None


def filter_by_period(emb: np.ndarray, meta: pd.DataFrame,
                     year_min: int, year_max: int) -> tuple:
    """期間でフィルタリングする。"""
    if "year" not in meta.columns:
        return emb, meta
    mask = (meta["year"] >= year_min) & (meta["year"] <= year_max)
    return emb[mask.values], meta[mask]


def filter_by_unet(emb: np.ndarray, meta: pd.DataFrame, is_unet: int = 1) -> tuple:
    """U-Netフラグでフィルタリングする。"""
    unet_col = "is_unet_final" if "is_unet_final" in meta.columns else "is_unet"
    if unet_col not in meta.columns:
        return emb, meta
    mask = meta[unet_col] == is_unet
    return emb[mask.values], meta[mask]


def main():
    parser = argparse.ArgumentParser(description="ドメイン間類似度の計算")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--sample", type=int, default=None)
    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    log_dir = script_dir / cfg["data"]["output_dir"] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"05_compute_domain_similarity_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 05_compute_domain_similarity.py 開始 ===")

    emb_dir = script_dir / cfg["data"]["output_dir"] / "embeddings"
    processed_dir = script_dir / cfg["data"]["processed_dir"]
    tables_dir = script_dir / cfg["data"]["output_dir"] / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    periods = cfg["periods"]
    past_start = periods["past_start"]
    past_end = periods["past_end"]
    future_start = periods["future_start"]
    future_end = periods["future_end"]

    emb_types = ["full", "problem", "solution"]
    rows = []

    any_embeddings_found = False

    for emb_type in emb_types:
        emb_a, meta_a = load_embeddings_and_meta(emb_dir, processed_dir, "A0", emb_type, logger)
        emb_b, meta_b = load_embeddings_and_meta(emb_dir, processed_dir, "B0", emb_type, logger)

        if emb_a is None or emb_b is None:
            logger.warning(f"[{emb_type}] 埋め込みファイルが不足。このタイプをスキップします。")
            continue

        any_embeddings_found = True
        logger.info(f"[{emb_type}] A0: {emb_a.shape}, B0: {emb_b.shape}")

        # 1. A0全体 vs B0全体
        sim = cosine_similarity_mean(emb_a, emb_b)
        rows.append({"comparison": "A0_all vs B0_all", "emb_type": emb_type, "similarity": sim})
        logger.info(f"[{emb_type}] A0_all vs B0_all: {sim:.4f}")

        # 2. A0_past vs B0_past
        emb_a_past, meta_a_past = filter_by_period(emb_a, meta_a, past_start, past_end)
        emb_b_past, meta_b_past = filter_by_period(emb_b, meta_b, past_start, past_end)
        if len(emb_a_past) > 0 and len(emb_b_past) > 0:
            sim = cosine_similarity_mean(emb_a_past, emb_b_past)
            rows.append({"comparison": f"A0_past({past_start}-{past_end}) vs B0_past", "emb_type": emb_type, "similarity": sim})
            logger.info(f"[{emb_type}] A0_past vs B0_past: {sim:.4f}")

        # 3. A0_future vs B0_future
        emb_a_fut, _ = filter_by_period(emb_a, meta_a, future_start, future_end)
        emb_b_fut, _ = filter_by_period(emb_b, meta_b, future_start, future_end)
        if len(emb_a_fut) > 0 and len(emb_b_fut) > 0:
            sim = cosine_similarity_mean(emb_a_fut, emb_b_fut)
            rows.append({"comparison": f"A0_future({future_start}-{future_end}) vs B0_future", "emb_type": emb_type, "similarity": sim})
            logger.info(f"[{emb_type}] A0_future vs B0_future: {sim:.4f}")

        # 4. A0_unet vs B0全体
        emb_a_unet, meta_a_unet = filter_by_unet(emb_a, meta_a, 1)
        if len(emb_a_unet) > 0:
            sim = cosine_similarity_mean(emb_a_unet, emb_b)
            rows.append({"comparison": "A0_unet vs B0_all", "emb_type": emb_type, "similarity": sim})
            logger.info(f"[{emb_type}] A0_unet vs B0_all: {sim:.4f}")

            # 5. A0_unet vs B0_unet
            emb_b_unet, _ = filter_by_unet(emb_b, meta_b, 1)
            if len(emb_b_unet) > 0:
                sim = cosine_similarity_mean(emb_a_unet, emb_b_unet)
                rows.append({"comparison": "A0_unet vs B0_unet", "emb_type": emb_type, "similarity": sim})
                logger.info(f"[{emb_type}] A0_unet vs B0_unet: {sim:.4f}")

        # 6. A0_past_unet vs B0_past
        emb_a_past_unet, _ = filter_by_unet(emb_a_past, meta_a_past, 1) if len(emb_a_past) > 0 else (np.array([]), None)
        if len(emb_a_past_unet) > 0 and len(emb_b_past) > 0:
            sim = cosine_similarity_mean(emb_a_past_unet, emb_b_past)
            rows.append({"comparison": f"A0_past_unet vs B0_past", "emb_type": emb_type, "similarity": sim})
            logger.info(f"[{emb_type}] A0_past_unet vs B0_past: {sim:.4f}")

    if not any_embeddings_found:
        logger.warning("埋め込みファイルが1つも見つかりませんでした。")
        logger.warning("先に 04_embed_patents.py を実行してください。")
        logger.warning("ダミーの結果ファイルを出力します。")
        rows.append({"comparison": "N/A", "emb_type": "N/A", "similarity": float("nan")})

    result_df = pd.DataFrame(rows)
    out_path = tables_dir / "domain_similarity_summary.csv"
    result_df.to_csv(out_path, index=False, encoding="utf-8")
    logger.info(f"保存: {out_path}")

    print("\n=== ドメイン類似度サマリー ===")
    print(result_df.to_string(index=False))

    logger.info("=== 05_compute_domain_similarity.py 完了 ===")


if __name__ == "__main__":
    main()
