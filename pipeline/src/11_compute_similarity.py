"""
Script: 11_compute_similarity.py
Purpose: A0からB0へのTop-k近傍類似度とfield-level similarityを計算する。
Output:
  - data/processed/similarity/A0_to_B0_{problem|solution|fulltext}_topk.csv
  - data/processed/similarity/field_level_similarity_summary.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


EMB_TYPES = ["problem", "solution", "fulltext"]


def resolve_dir(path: str, pipeline_dir: Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = pipeline_dir / p
    if p.exists():
        return p
    if "processed" in p.parts:
        alt = pipeline_dir / "data" / "processed" / Path(*p.parts[p.parts.index("processed") + 1:])
        if alt.exists():
            return alt
    return p


def resolve_output_dir(path: str, pipeline_dir: Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    if p.parts and p.parts[0] == "processed":
        return pipeline_dir / "data" / "processed" / Path(*p.parts[1:])
    return pipeline_dir / p


def suffixed(name: str, suffix: str) -> str:
    if not suffix:
        return name
    stem, ext = name.rsplit(".", 1)
    return f"{stem}_{suffix}.{ext}"


def normalize(emb: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return emb / norms


def filter_meta_emb(meta: pd.DataFrame, emb: np.ndarray, include_noise: bool) -> tuple[pd.DataFrame, np.ndarray]:
    if not include_noise and "analysis_include" in meta.columns:
        mask = pd.to_numeric(meta["analysis_include"], errors="coerce").fillna(1).astype(int) == 1
        meta = meta[mask].reset_index(drop=True)
        emb = emb[mask.values]
    return meta, emb


def centroid_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = normalize(a)
    b = normalize(b)
    ca = a.mean(axis=0)
    cb = b.mean(axis=0)
    denom = np.linalg.norm(ca) * np.linalg.norm(cb)
    if denom == 0:
        return float("nan")
    return float(np.dot(ca, cb) / denom)


def topk_rows(meta_a: pd.DataFrame, emb_a: np.ndarray, meta_b: pd.DataFrame, emb_b: np.ndarray, top_k: int, chunk_size: int) -> list[dict]:
    emb_a = normalize(emb_a)
    emb_b = normalize(emb_b)
    k = min(top_k, len(meta_b))
    rows = []

    for start in range(0, len(emb_a), chunk_size):
        end = min(start + chunk_size, len(emb_a))
        sims = emb_a[start:end] @ emb_b.T
        idx = np.argpartition(-sims, kth=k - 1, axis=1)[:, :k]
        sorted_idx = np.take_along_axis(idx, np.argsort(-np.take_along_axis(sims, idx, axis=1), axis=1), axis=1)

        for local_i, b_indices in enumerate(sorted_idx):
            a_i = start + local_i
            a_row = meta_a.iloc[a_i]
            for rank, b_i in enumerate(b_indices, start=1):
                b_row = meta_b.iloc[int(b_i)]
                rows.append({
                    "a_rank_source_idx": a_i,
                    "neighbor_rank": rank,
                    "a_publication_number": a_row.get("publication_number", ""),
                    "b_publication_number": b_row.get("publication_number", ""),
                    "similarity": float(sims[local_i, int(b_i)]),
                    "a_family_id": a_row.get("family_id", ""),
                    "b_family_id": b_row.get("family_id", ""),
                    "a_year": a_row.get("filing_year", a_row.get("year", "")),
                    "b_year": b_row.get("filing_year", b_row.get("year", "")),
                    "a_application_field": a_row.get("application_field", ""),
                    "b_application_field": b_row.get("application_field", ""),
                    "a_technical_means": a_row.get("technical_means", ""),
                    "b_technical_means": b_row.get("technical_means", ""),
                    "a_is_unet_final": a_row.get("is_unet_final", ""),
                    "b_is_unet_final": b_row.get("is_unet_final", ""),
                })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="A0/B0間のTop-k類似度を計算")
    parser.add_argument("--embedding-dir", default="data/processed/embeddings")
    parser.add_argument("--output-dir", default="data/processed/similarity")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--include-noise", action="store_true")
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()

    pipeline_dir = Path(__file__).parent.parent
    embedding_dir = resolve_dir(args.embedding_dir, pipeline_dir)
    output_dir = resolve_output_dir(args.output_dir, pipeline_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    meta_a = pd.read_csv(embedding_dir / "A0_embedding_metadata.csv")
    meta_b = pd.read_csv(embedding_dir / "B0_embedding_metadata.csv")
    summary = {}

    for emb_type in EMB_TYPES:
        emb_a = np.load(embedding_dir / f"A0_{emb_type}_embeddings.npy")
        emb_b = np.load(embedding_dir / f"B0_{emb_type}_embeddings.npy")
        if len(emb_a) != len(meta_a) or len(emb_b) != len(meta_b):
            raise ValueError(f"{emb_type}: embeddingとmetadataの件数が一致しません")

        ma, ea = filter_meta_emb(meta_a.copy(), emb_a, args.include_noise)
        mb, eb = filter_meta_emb(meta_b.copy(), emb_b, args.include_noise)
        sim = centroid_similarity(ea, eb)
        summary[f"{emb_type}_field_similarity"] = sim
        summary[f"{emb_type}_A_count"] = len(ma)
        summary[f"{emb_type}_B_count"] = len(mb)

        rows = topk_rows(ma, ea, mb, eb, args.top_k, args.chunk_size)
        out = output_dir / suffixed(f"A0_to_B0_{emb_type}_topk.csv", args.output_suffix)
        pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8")
        print(f"saved: {out} rows={len(rows)}")

    summary_out = output_dir / suffixed("field_level_similarity_summary.csv", args.output_suffix)
    pd.DataFrame([summary]).to_csv(summary_out, index=False, encoding="utf-8")
    if args.output_suffix:
        pd.DataFrame([summary]).to_csv(output_dir / "field_level_similarity_summary.csv", index=False, encoding="utf-8")
    print(f"saved: {summary_out}")


if __name__ == "__main__":
    main()
