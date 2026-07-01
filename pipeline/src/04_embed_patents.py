"""
Script: 04_embed_patents.py
Purpose: PatentSBERTa（またはフォールバックモデル）で特許テキストの埋め込みベクトルを計算する。
         テキストがない場合はゼロベクトルを割り当てる。チェックポイント保存対応。
Input:
  - data/processed/A0_contexts.csv
  - data/processed/B0_contexts.csv
Output:
  - outputs/embeddings/{domain}_{type}_embeddings.npy
  - outputs/embeddings/{domain}_metadata.csv
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


def get_device(device_cfg: str) -> str:
    if device_cfg == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"
    return device_cfg


def load_model(model_name: str, fallback_name: str, device: str, logger: logging.Logger):
    """モデルをロードする。失敗時はフォールバックを使用。"""
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"モデルをロード中: {model_name}")
        model = SentenceTransformer(model_name, device=device)
        logger.info(f"モデルロード成功: {model_name}")
        return model, model_name
    except Exception as e:
        logger.warning(f"メインモデルのロード失敗: {e}")
        logger.info(f"フォールバックモデルをロード中: {fallback_name}")
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(fallback_name, device=device)
            logger.info(f"フォールバックモデルロード成功: {fallback_name}")
            return model, fallback_name
        except Exception as e2:
            logger.error(f"フォールバックモデルもロード失敗: {e2}")
            return None, None


def embed_texts(model, texts: list, batch_size: int, max_length: int,
                checkpoint_dir: Path, prefix: str, logger: logging.Logger) -> np.ndarray:
    """テキストリストの埋め込みを計算する（チェックポイント対応）。"""
    try:
        from tqdm import tqdm
        use_tqdm = True
    except ImportError:
        use_tqdm = False

    n = len(texts)
    # 最初の1件でdimを確認
    sample_text = next((t for t in texts if t and t.strip()), "test")
    try:
        sample_emb = model.encode([sample_text], show_progress_bar=False)
        dim = sample_emb.shape[1]
    except Exception as e:
        logger.error(f"サンプル埋め込みエラー: {e}")
        return None

    # チェックポイントファイル
    ckpt_file = checkpoint_dir / f"{prefix}_checkpoint.npy"
    ckpt_idx_file = checkpoint_dir / f"{prefix}_checkpoint_idx.txt"

    start_idx = 0
    if ckpt_file.exists() and ckpt_idx_file.exists():
        try:
            embeddings = np.load(ckpt_file)
            with open(ckpt_idx_file, "r") as f:
                start_idx = int(f.read().strip())
            logger.info(f"チェックポイント読み込み: {start_idx}/{n} 件完了済み")
            if start_idx >= n:
                logger.info("すべての埋め込みが完了済みです。")
                return embeddings
        except Exception:
            start_idx = 0
            embeddings = np.zeros((n, dim), dtype=np.float32)
    else:
        embeddings = np.zeros((n, dim), dtype=np.float32)

    checkpoint_interval = 100
    iterator = range(start_idx, n, batch_size)
    if use_tqdm:
        iterator = tqdm(iterator, desc=f"Embedding {prefix}", total=(n - start_idx) // batch_size + 1)

    for batch_start in iterator:
        batch_end = min(batch_start + batch_size, n)
        batch_texts = texts[batch_start:batch_end]

        # 空テキストのマスク
        valid_mask = [bool(t and t.strip()) for t in batch_texts]
        valid_texts = [t for t, v in zip(batch_texts, valid_mask) if v]

        if valid_texts:
            try:
                batch_emb = model.encode(
                    valid_texts,
                    show_progress_bar=False,
                    batch_size=min(batch_size, len(valid_texts)),
                )
                valid_idx = 0
                for i, is_valid in enumerate(valid_mask):
                    if is_valid:
                        embeddings[batch_start + i] = batch_emb[valid_idx]
                        valid_idx += 1
            except Exception as e:
                logger.warning(f"バッチ {batch_start}-{batch_end} でエラー: {e}")

        # チェックポイント保存
        if (batch_end - start_idx) % checkpoint_interval == 0 or batch_end == n:
            np.save(ckpt_file, embeddings)
            with open(ckpt_idx_file, "w") as f:
                f.write(str(batch_end))

    # チェックポイントファイルを削除（完了）
    if ckpt_file.exists():
        ckpt_file.unlink()
    if ckpt_idx_file.exists():
        ckpt_idx_file.unlink()

    return embeddings


def main():
    parser = argparse.ArgumentParser(description="特許テキストの埋め込み計算")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--domain", default="both", choices=["A0", "B0", "both"])
    parser.add_argument("--type", default="all", choices=["full", "problem", "solution", "all"])
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
    log_file = log_dir / f"04_embed_patents_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 04_embed_patents.py 開始 ===")

    emb_cfg = cfg["embedding"]
    device = get_device(emb_cfg["device"])
    logger.info(f"デバイス: {device}")

    model, model_used = load_model(
        emb_cfg["model_name"], emb_cfg["fallback_model_name"], device, logger
    )
    if model is None:
        logger.error("モデルをロードできませんでした。終了します。")
        sys.exit(1)

    processed_dir = script_dir / cfg["data"]["processed_dir"]
    emb_dir = script_dir / cfg["data"]["output_dir"] / "embeddings"
    emb_dir.mkdir(parents=True, exist_ok=True)

    domains = ["A0", "B0"] if args.domain == "both" else [args.domain]
    types = ["full", "problem", "solution"] if args.type == "all" else [args.type]

    # テキスト列のマッピング
    text_col_map = {
        "full": "full_text",
        "problem": "problem_context",
        "solution": "solution_context",
    }

    for domain in domains:
        in_path = processed_dir / f"{domain}_contexts.csv"
        if not in_path.exists():
            logger.error(f"[{domain}] 入力ファイルが存在しません: {in_path}")
            logger.error("先に 03_extract_problem_solution_contexts.py を実行してください。")
            continue

        df = pd.read_csv(in_path)
        logger.info(f"[{domain}] 読み込み: {len(df)}行")

        if args.sample and args.sample < len(df):
            df = df.sample(n=args.sample, random_state=42).reset_index(drop=True)
            logger.info(f"[{domain}] サンプリング: {len(df)}行")

        has_text = bool(df.get("has_text", pd.Series([False])).iloc[0])

        # メタデータ保存
        meta_cols = []
        for col in [
            "publication_number", "family_id", "year",
            "is_unet", "is_unet_final", "is_unet_title_abstract",
            "is_unet_claims", "is_unet_full_text",
        ]:
            if col in df.columns:
                meta_cols.append(col)
        meta_df = df[meta_cols].copy()
        meta_df["idx"] = range(len(meta_df))
        meta_df["model_used"] = model_used
        meta_df["has_text"] = has_text

        meta_out = emb_dir / f"{domain}_metadata.csv"
        meta_df.to_csv(meta_out, index=False, encoding="utf-8")
        logger.info(f"[{domain}] メタデータ保存: {meta_out}")

        for emb_type in types:
            col = text_col_map[emb_type]
            if col not in df.columns:
                logger.warning(f"[{domain}] 列 '{col}' が存在しません。スキップ。")
                continue

            texts = df[col].fillna("").tolist()
            nonempty_count = sum(1 for t in texts if t and t.strip())
            logger.info(f"[{domain}/{emb_type}] テキスト: {nonempty_count}/{len(texts)} 件が非空")

            if nonempty_count == 0 and not has_text:
                logger.warning(f"[{domain}/{emb_type}] テキストなしモード: ゼロベクトルを保存")
                # ダミーで次元を取得
                dummy_emb = model.encode(["dummy"], show_progress_bar=False)
                dim = dummy_emb.shape[1]
                embeddings = np.zeros((len(df), dim), dtype=np.float32)
            else:
                embeddings = embed_texts(
                    model, texts,
                    batch_size=emb_cfg["batch_size"],
                    max_length=emb_cfg["max_length"],
                    checkpoint_dir=emb_dir,
                    prefix=f"{domain}_{emb_type}",
                    logger=logger,
                )
                if embeddings is None:
                    logger.error(f"[{domain}/{emb_type}] 埋め込み計算失敗。スキップ。")
                    continue

            out_path = emb_dir / f"{domain}_{emb_type}_embeddings.npy"
            np.save(out_path, embeddings)
            logger.info(f"[{domain}/{emb_type}] 保存: {out_path} shape={embeddings.shape}")

    logger.info("=== 04_embed_patents.py 完了 ===")


if __name__ == "__main__":
    main()
