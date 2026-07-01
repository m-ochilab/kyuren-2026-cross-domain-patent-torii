"""
Script: 10_vectorize_contexts.py
Purpose: problem/solution/full text embeddingsを既存contexts CSVから作成する。
Output:
  - data/processed/embeddings/{domain}_{problem|solution|fulltext}_embeddings.npy
  - data/processed/embeddings/{domain}_embedding_metadata.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd


DOMAINS = ["A0", "B0"]
TEXT_TYPES = {
    "problem": "problem_context",
    "solution": "solution_context",
    "fulltext": "full_text",
}
METADATA_COLUMNS = [
    "publication_number",
    "family_id",
    "filing_year",
    "year",
    "application_field",
    "analysis_include",
    "domain_noise_flag",
    "is_unet_final",
    "is_unet_title_abstract",
    "is_unet_claims",
    "is_unet_full_text",
    "technical_means",
]


def resolve_processed_dir(path: str, pipeline_dir: Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = pipeline_dir / p
    if p.exists():
        return p
    if "processed" in p.parts:
        parts = p.parts[p.parts.index("processed") + 1:]
        fallback = pipeline_dir / "data" / "processed" / Path(*parts)
        if fallback.exists():
            return fallback
    return p


def resolve_output_dir(path: str, pipeline_dir: Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    if p.parts and p.parts[0] == "processed":
        return pipeline_dir / "data" / "processed" / Path(*p.parts[1:])
    return pipeline_dir / p


def setup_logger() -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
    return logging.getLogger(__name__)


def l2_normalize(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (arr / norms).astype(np.float32)


def build_fulltext(df: pd.DataFrame) -> pd.Series:
    if "full_text" in df.columns:
        return df["full_text"].fillna("").astype(str)
    parts = []
    for col in ["title", "abstract", "claims"]:
        if col in df.columns:
            parts.append(df[col].fillna("").astype(str))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "\n" + parts[1] + "\n" + parts[2]


def metadata_frame(df: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for col in METADATA_COLUMNS:
        if col in df.columns:
            out[col] = df[col]
        elif col == "filing_year" and "year" in df.columns:
            out[col] = df["year"]
        else:
            logger.warning(f"metadata列が存在しません: {col}")
            out[col] = ""
    out.insert(0, "embedding_idx", range(len(out)))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="文脈テキストをSentenceTransformerでベクトル化")
    parser.add_argument("--input-dir", default="data/processed")
    parser.add_argument("--output-dir", default="data/processed/embeddings")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-normalize", action="store_true")
    args = parser.parse_args()

    pipeline_dir = Path(__file__).parent.parent
    input_dir = resolve_processed_dir(args.input_dir, pipeline_dir)
    output_dir = resolve_output_dir(args.output_dir, pipeline_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logger()
    logger.info(f"input_dir={input_dir}")
    logger.info(f"output_dir={output_dir}")
    logger.info(f"model={args.model}")

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(args.model)

    for domain in DOMAINS:
        in_path = input_dir / f"{domain}_contexts.csv"
        if not in_path.exists():
            logger.warning(f"[{domain}] 入力なし: {in_path}")
            continue

        df = pd.read_csv(in_path)
        if args.sample and args.sample < len(df):
            df = df.sample(args.sample, random_state=42).reset_index(drop=True)
            logger.info(f"[{domain}] sample={len(df)}")

        meta = metadata_frame(df, logger)
        meta_out = output_dir / f"{domain}_embedding_metadata.csv"
        if meta_out.exists() and not args.overwrite:
            logger.info(f"[{domain}] metadata exists, skip: {meta_out}")
        else:
            meta.to_csv(meta_out, index=False, encoding="utf-8")
            logger.info(f"[{domain}] metadata saved: {meta_out}")

        for emb_type, col in TEXT_TYPES.items():
            out_path = output_dir / f"{domain}_{emb_type}_embeddings.npy"
            if out_path.exists() and not args.overwrite:
                logger.info(f"[{domain}/{emb_type}] exists, skip: {out_path}")
                continue

            if emb_type == "fulltext":
                texts = build_fulltext(df)
            elif col in df.columns:
                texts = df[col].fillna("").astype(str)
            else:
                logger.warning(f"[{domain}/{emb_type}] 列なし: {col}; 空文字で処理")
                texts = pd.Series([""] * len(df), index=df.index)

            empty_count = int((texts.str.strip() == "").sum())
            logger.info(f"[{domain}/{emb_type}] rows={len(texts)}, empty={empty_count}")

            embeddings = model.encode(
                texts.tolist(),
                batch_size=args.batch_size,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=False,
            ).astype(np.float32)
            if not args.no_normalize:
                embeddings = l2_normalize(embeddings)
            np.save(out_path, embeddings)
            logger.info(f"[{domain}/{emb_type}] saved: {out_path} shape={embeddings.shape}")


if __name__ == "__main__":
    main()
