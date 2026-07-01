#!/usr/bin/env python3
"""
Heterogeneous cross-domain patent analysis for cleaning/removal/rinse technologies.

This pipeline extracts invention-subject-level candidates whose problem context
is close to semiconductor cleaning (S0) while the source-side solution context
may be heterogeneous (C0/C1). S1 is handled separately as a known-positive check
to avoid leakage in candidate search.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


TEXT_TYPES = {
    "problem": "problem_context",
    "solution": "solution_context",
    "fulltext": "full_text",
}

CONTEXT_COLUMNS = [
    "dataset_key",
    "dataset_id",
    "dataset_version",
    "role",
    "publication_number",
    "family_id",
    "family_id_simple",
    "application_number",
    "filing_year",
    "filing_date",
    "publication_date",
    "title",
    "abstract",
    "claims",
    "claims_short",
    "full_text",
    "applicant_names",
    "applicant_normalized",
    "is_kao",
    "ipc_codes",
    "cpc_codes",
    "problem_context",
    "solution_context",
    "effect_context",
    "target_object",
    "technical_means",
    "context_extraction_method",
]

SUMMARY_COLUMNS = [
    "dataset_key",
    "dataset_id",
    "dataset_version",
    "role",
    "publication_records",
    "unique_publications",
    "family_records",
    "title_nonempty_rate",
    "abstract_nonempty_rate",
    "claims_nonempty_rate",
    "kao_publications",
    "filing_year_min",
    "filing_year_max",
]

PROBLEM_PATTERNS = [
    r"problem", r"challenge", r"drawback", r"disadvantage", r"need", r"required",
    r"residue", r"particle", r"contaminant", r"stain", r"redeposition", r"damage",
    r"corrosion", r"defect", r"remaining", r"difficult", r"課題", r"問題", r"残渣",
    r"粒子", r"汚染", r"再付着", r"損傷", r"腐食", r"除去", r"清浄", r"缺陷",
    r"残留", r"颗粒", r"污染", r"损伤",
]

SOLUTION_PATTERNS = [
    r"composition", r"solution", r"liquid", r"agent", r"surfactant", r"chelating",
    r"dispersant", r"inhibitor", r"method", r"process", r"rins", r"clean",
    r"remov", r"strip", r"etch", r"substrate", r"wafer", r"comprises", r"including",
    r"組成物", r"溶液", r"液", r"剤", r"界面活性", r"キレート", r"分散",
    r"方法", r"処理", r"洗浄", r"除去", r"剥離", r"基板", r"晶圆", r"清洗",
]

EFFECT_PATTERNS = [
    r"improve", r"reduce", r"prevent", r"suppress", r"remove", r"low damage",
    r"cleanability", r"corrosion", r"residue", r"particle", r"向上", r"低減",
    r"防止", r"抑制", r"除去", r"低ダメージ", r"洗浄性", r"腐食", r"残渣",
]

TARGET_OBJECT_RULES = [
    ("semiconductor substrate", [r"semiconductor substrate", r"半導体基板"]),
    ("silicon wafer", [r"silicon wafer", r"wafer", r"ウェハ", r"晶圆"]),
    ("microelectronic substrate", [r"microelectronic substrate", r"microelectronic"]),
    ("substrate", [r"substrate", r"基板"]),
    ("metal surface", [r"metal surface", r"metal", r"金属"]),
    ("hard surface", [r"hard surface", r"硬質表面"]),
    ("textile", [r"textile", r"fabric", r"繊維", r"布"]),
    ("electronic component", [r"electronic component", r"electronic device", r"電子部品"]),
]

TECHNICAL_MEANS_RULES = [
    ("cleaning composition", [r"cleaning composition", r"洗浄.*組成物", r"清洗.*组合物"]),
    ("cleaning solution", [r"cleaning solution", r"cleaning liquid", r"洗浄液", r"清洗液"]),
    ("rinsing liquid", [r"rinsing solution", r"rinsing liquid", r"rinse liquid", r"リンス液"]),
    ("residue removal composition", [r"residue removal", r"残渣.*除去", r"残留.*去除"]),
    ("particle removal", [r"particle removal", r"particle.*remov", r"粒子.*除去", r"颗粒.*去除"]),
    ("contaminant removal", [r"contaminant removal", r"汚染.*除去", r"污染.*去除"]),
    ("anti-redeposition", [r"anti[- ]redeposition", r"redeposition", r"再付着"]),
    ("surfactant", [r"surfactant", r"界面活性"]),
    ("chelating agent", [r"chelating agent", r"chelator", r"キレート"]),
    ("dispersant", [r"dispersant", r"分散剤"]),
    ("corrosion inhibitor", [r"corrosion inhibitor", r"防食", r"腐食.*抑制"]),
    ("post-CMP cleaning", [r"post[- ]CMP", r"CMP.*clean", r"CMP後"]),
    ("photoresist removal", [r"photoresist removal", r"resist stripping", r"フォトレジスト", r"レジスト.*剥離"]),
    ("substrate cleaning method", [r"substrate cleaning method", r"基板.*洗浄.*方法"]),
    ("wafer cleaning", [r"wafer cleaning", r"ウェハ.*洗浄", r"晶圆.*清洗"]),
    ("surface cleaning", [r"surface cleaning", r"表面.*洗浄", r"表面.*清洗"]),
]

KAO_RE = re.compile(r"\bKAO\b|KAO CORPORATION|花王", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")


@dataclass
class DatasetSpec:
    key: str
    dataset_id: str
    role: str
    version: str
    publication_csv: Path
    family_csv: Path


def clean_value(value: Any, limit: int | None = None) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = SPACE_RE.sub(" ", str(value).replace("\r", " ").replace("\n", " ")).strip()
    if text.lower() == "nan":
        return ""
    return text[:limit] if limit else text


def nonempty_rate(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return float(series.fillna("").astype(str).str.strip().ne("").mean())


def normalize_applicant(text: str) -> str:
    text = clean_value(text).upper()
    text = re.sub(r"[^A-Z0-9一-龥ぁ-んァ-ン]+", " ", text)
    return SPACE_RE.sub(" ", text).strip()


def is_kao_applicant(text: str) -> int:
    return int(bool(KAO_RE.search(clean_value(text))))


def normalize_codes(*values: Any) -> str:
    seen = []
    for value in values:
        for token in re.split(r"[;\n,]+", clean_value(value)):
            token = token.strip().upper()
            if token and token not in seen:
                seen.append(token)
    return "; ".join(seen)


def df_to_markdown(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """Small dependency-free Markdown table writer."""
    view = df.head(max_rows).copy() if max_rows else df.copy()
    cols = [str(c) for c in view.columns]
    rows = [[clean_value(v) for v in row] for row in view.to_numpy()]
    widths = []
    for i, col in enumerate(cols):
        width = len(col)
        for row in rows:
            width = max(width, len(row[i]))
        widths.append(min(width, 80))

    def fmt(values: list[str]) -> str:
        clipped = [v[:77] + "..." if len(v) > 80 else v for v in values]
        return "| " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(clipped)) + " |"

    lines = [fmt(cols), "| " + " | ".join("-" * w for w in widths) + " |"]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)


def split_sentences(text: str) -> list[str]:
    text = clean_value(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+|(?<=。)|(?<=！)|(?<=？)|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 12]


def first_matches(sentences: list[str], patterns: list[str], limit: int) -> list[str]:
    out: list[str] = []
    pattern = re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)
    for sent in sentences:
        if pattern.search(sent) and sent not in out:
            out.append(sent)
        if len(out) >= limit:
            break
    return out


def detect_labeled_terms(text: str, rules: list[tuple[str, list[str]]], limit: int = 6) -> str:
    found = []
    for label, patterns in rules:
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            found.append(label)
        if len(found) >= limit:
            break
    return "; ".join(found)


def extract_context_row(row: pd.Series) -> dict[str, str]:
    title = clean_value(row.get("title", ""))
    abstract = clean_value(row.get("abstract", ""))
    claims = clean_value(row.get("claims", ""))
    full = clean_value(row.get("full_text", "")) or clean_value(f"{title} {abstract} {claims}")

    abstract_sents = split_sentences(abstract)
    claim_sents = split_sentences(claims)
    problem_parts = first_matches(abstract_sents, PROBLEM_PATTERNS, 3)
    if not problem_parts and abstract_sents:
        problem_parts = abstract_sents[:2]
    if not problem_parts and title:
        problem_parts = [title]

    solution_parts = first_matches(abstract_sents, SOLUTION_PATTERNS, 2)
    solution_parts += first_matches(claim_sents, SOLUTION_PATTERNS, 2)
    if not solution_parts and claim_sents:
        solution_parts = claim_sents[:2]
    if not solution_parts and abstract_sents:
        solution_parts = abstract_sents[-2:]

    effect_parts = first_matches(abstract_sents, EFFECT_PATTERNS, 2)

    solution_context = clean_value(" ".join(dict.fromkeys(solution_parts)), 1400)
    problem_context = clean_value(" ".join(dict.fromkeys(problem_parts)), 1200)
    effect_context = clean_value(" ".join(dict.fromkeys(effect_parts)), 600)
    technical_means = detect_labeled_terms(f"{solution_context} {claims} {title}", TECHNICAL_MEANS_RULES)
    target_object = detect_labeled_terms(f"{title} {abstract}", TARGET_OBJECT_RULES, limit=4)

    return {
        "problem_context": problem_context,
        "solution_context": solution_context,
        "effect_context": effect_context,
        "target_object": target_object,
        "technical_means": technical_means,
        "context_extraction_method": "heuristic_cleaning_semiconductor",
        "full_text": full or clean_value(f"{title} {abstract}") if not claims else full,
    }


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def resolve_pipeline_path(pipeline_dir: Path, path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else pipeline_dir / p


def dataset_specs(cfg: dict[str, Any], pipeline_dir: Path) -> dict[str, DatasetSpec]:
    out = {}
    for key, value in cfg["datasets"].items():
        out[key] = DatasetSpec(
            key=key,
            dataset_id=value["dataset_id"],
            role=value["role"],
            version=value.get("dataset_version", ""),
            publication_csv=resolve_pipeline_path(pipeline_dir, value["publication_csv"]),
            family_csv=resolve_pipeline_path(pipeline_dir, value["family_csv"]),
        )
    return out


def count_csv_rows(path: Path, usecols: list[str] | None = None, chunksize: int = 5000) -> int:
    total = 0
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize):
        total += len(chunk)
    return total


def write_dataset_summary(specs: dict[str, DatasetSpec], output_dir: Path, chunksize: int) -> pd.DataFrame:
    rows = []
    for spec in specs.values():
        pub_total = 0
        pub_seen: set[str] = set()
        title_nonempty = abstract_nonempty = claims_nonempty = kao_count = 0
        years: list[int] = []
        for chunk in pd.read_csv(spec.publication_csv, chunksize=chunksize, dtype=str, keep_default_na=False):
            pub_total += len(chunk)
            pub_seen.update(chunk["publication_number"].astype(str).tolist())
            title_nonempty += int(chunk["title"].astype(str).str.strip().ne("").sum())
            abstract_nonempty += int(chunk["abstract"].astype(str).str.strip().ne("").sum())
            claims_nonempty += int(chunk["claims"].astype(str).str.strip().ne("").sum())
            kao_count += int(chunk["applicant_names"].map(is_kao_applicant).sum())
            year_values = pd.to_numeric(chunk.get("year", 0), errors="coerce").dropna().astype(int)
            years.extend([y for y in year_values.tolist() if y > 0])
        family_total = count_csv_rows(spec.family_csv, usecols=["family_id"], chunksize=chunksize)
        rows.append({
            "dataset_key": spec.key,
            "dataset_id": spec.dataset_id,
            "dataset_version": spec.version,
            "role": spec.role,
            "publication_records": pub_total,
            "unique_publications": len(pub_seen),
            "family_records": family_total,
            "title_nonempty_rate": round(title_nonempty / pub_total, 6) if pub_total else 0,
            "abstract_nonempty_rate": round(abstract_nonempty / pub_total, 6) if pub_total else 0,
            "claims_nonempty_rate": round(claims_nonempty / pub_total, 6) if pub_total else 0,
            "kao_publications": kao_count,
            "filing_year_min": min(years) if years else "",
            "filing_year_max": max(years) if years else "",
        })

    summary = pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "dataset_summary.csv", index=False, encoding="utf-8")
    md = ["# Dataset Summary", "", df_to_markdown(summary), ""]
    (output_dir / "dataset_summary.md").write_text("\n".join(md), encoding="utf-8")
    return summary


def context_path(cache_dir: Path, spec: DatasetSpec) -> Path:
    return cache_dir / "contexts" / f"{spec.dataset_id}_contexts.csv"


def build_contexts(specs: dict[str, DatasetSpec], cache_dir: Path, chunksize: int, overwrite: bool) -> None:
    ctx_dir = cache_dir / "contexts"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    for spec in specs.values():
        out_path = context_path(cache_dir, spec)
        if out_path.exists() and not overwrite:
            print(f"[contexts] skip existing: {out_path}")
            continue
        if out_path.exists():
            out_path.unlink()
        first = True
        print(f"[contexts] building {spec.dataset_id}", flush=True)
        for chunk in pd.read_csv(spec.publication_csv, chunksize=chunksize, dtype=str, keep_default_na=False):
            out_rows = []
            for _, row in chunk.iterrows():
                extracted = extract_context_row(row)
                applicant = clean_value(row.get("applicant_names", ""))
                full_text = extracted.pop("full_text")
                out_rows.append({
                    "dataset_key": spec.key,
                    "dataset_id": spec.dataset_id,
                    "dataset_version": spec.version,
                    "role": spec.role,
                    "publication_number": clean_value(row.get("publication_number", "")),
                    "family_id": clean_value(row.get("family_id", "")),
                    "family_id_simple": clean_value(row.get("family_id_simple", "")),
                    "application_number": clean_value(row.get("application_number", "")),
                    "filing_year": clean_value(row.get("year", "")),
                    "filing_date": clean_value(row.get("filing_date", "")),
                    "publication_date": clean_value(row.get("publication_date", "")),
                    "title": clean_value(row.get("title", ""), 500),
                    "abstract": clean_value(row.get("abstract", ""), 1600),
                    "claims": clean_value(row.get("claims", ""), 4000),
                    "claims_short": clean_value(row.get("claims", ""), 700),
                    "full_text": clean_value(full_text, 5000),
                    "applicant_names": applicant,
                    "applicant_normalized": normalize_applicant(applicant),
                    "is_kao": is_kao_applicant(applicant),
                    "ipc_codes": normalize_codes(row.get("ipc_main", ""), row.get("ipc_others", "")),
                    "cpc_codes": normalize_codes(row.get("cpc_main", ""), row.get("cpc_others", "")),
                    **extracted,
                })
            out_df = pd.DataFrame(out_rows, columns=CONTEXT_COLUMNS)
            out_df.to_csv(out_path, index=False, encoding="utf-8", mode="w" if first else "a", header=first)
            first = False


def l2_normalize(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (arr / norms).astype(np.float32)


def metadata_columns() -> list[str]:
    return [
        "embedding_idx",
        "dataset_key",
        "dataset_id",
        "dataset_version",
        "role",
        "publication_number",
        "family_id",
        "family_id_simple",
        "filing_year",
        "title",
        "abstract",
        "claims_short",
        "problem_context",
        "solution_context",
        "technical_means",
        "target_object",
        "effect_context",
        "applicant_names",
        "is_kao",
        "ipc_codes",
        "cpc_codes",
    ]


def vectorize_contexts(
    specs: dict[str, DatasetSpec],
    cache_dir: Path,
    output_dir: Path,
    model_name: str,
    batch_size: int,
    device: str,
    chunksize: int,
    normalize: bool,
    overwrite: bool,
) -> pd.DataFrame:
    from sentence_transformers import SentenceTransformer

    emb_dir = cache_dir / "embeddings"
    emb_dir.mkdir(parents=True, exist_ok=True)
    if device == "auto":
        device = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = "mps"
        except Exception:
            device = "cpu"
    print(f"[vectorize] model={model_name} device={device}", flush=True)
    model = SentenceTransformer(model_name, device=device)
    summaries = []
    run_at = datetime.now().isoformat(timespec="seconds")

    for spec in specs.values():
        ctx = context_path(cache_dir, spec)
        if not ctx.exists():
            raise FileNotFoundError(ctx)

        meta_path = emb_dir / f"{spec.dataset_id}_embedding_metadata.csv"
        if meta_path.exists() and not overwrite:
            meta = pd.read_csv(meta_path)
        else:
            meta_chunks = []
            offset = 0
            meta_usecols = [c for c in metadata_columns() if c != "embedding_idx"]
            for chunk in pd.read_csv(ctx, chunksize=chunksize, dtype=str, keep_default_na=False, usecols=meta_usecols):
                sub = chunk[[c for c in metadata_columns() if c != "embedding_idx"]].copy()
                sub.insert(0, "embedding_idx", range(offset, offset + len(sub)))
                offset += len(sub)
                meta_chunks.append(sub)
            meta = pd.concat(meta_chunks, ignore_index=True)
            meta.to_csv(meta_path, index=False, encoding="utf-8")

        for emb_type, text_col in TEXT_TYPES.items():
            out_path = emb_dir / f"{spec.dataset_id}_{emb_type}_vectors.npy"
            if out_path.exists() and not overwrite:
                arr = np.load(out_path, mmap_mode="r")
                summaries.append({
                    "dataset_id": spec.dataset_id,
                    "embedding_type": emb_type,
                    "model_name": model_name,
                    "dimension": arr.shape[1],
                    "input_records": arr.shape[0],
                    "run_at": run_at,
                    "output_path": str(out_path),
                    "status": "cached",
                })
                continue

            print(f"[vectorize] {spec.dataset_id}/{emb_type}", flush=True)
            parts = []
            total = 0
            empty = 0
            for chunk in pd.read_csv(ctx, chunksize=chunksize, dtype=str, keep_default_na=False, usecols=[text_col]):
                texts = chunk[text_col].fillna("").astype(str).tolist()
                empty += sum(1 for t in texts if not t.strip())
                emb = model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=False,
                ).astype(np.float32)
                if normalize:
                    emb = l2_normalize(emb)
                parts.append(emb)
                total += len(texts)
                print(f"[vectorize] {spec.dataset_id}/{emb_type}: {total} rows", flush=True)
            arr = np.vstack(parts) if parts else np.empty((0, 0), dtype=np.float32)
            np.save(out_path, arr)
            summaries.append({
                "dataset_id": spec.dataset_id,
                "embedding_type": emb_type,
                "model_name": model_name,
                "dimension": arr.shape[1] if arr.ndim == 2 and arr.shape[0] else "",
                "input_records": total,
                "empty_texts": empty,
                "run_at": run_at,
                "output_path": str(out_path),
                "status": "created",
            })

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(output_dir / "vectorization_summary.csv", index=False, encoding="utf-8")
    return summary_df


def load_meta(cache_dir: Path, dataset_id: str) -> pd.DataFrame:
    return pd.read_csv(cache_dir / "embeddings" / f"{dataset_id}_embedding_metadata.csv")


def load_vectors(cache_dir: Path, dataset_id: str, emb_type: str) -> np.ndarray:
    return np.load(cache_dir / "embeddings" / f"{dataset_id}_{emb_type}_vectors.npy")


def topk_indices(query: np.ndarray, corpus: np.ndarray, top_k: int, chunk_size: int) -> tuple[np.ndarray, np.ndarray]:
    k = min(top_k, len(corpus))
    all_idx = []
    all_sim = []
    for start in range(0, len(query), chunk_size):
        end = min(start + chunk_size, len(query))
        sims = query[start:end] @ corpus.T
        idx = np.argpartition(-sims, kth=k - 1, axis=1)[:, :k]
        order = np.argsort(-np.take_along_axis(sims, idx, axis=1), axis=1)
        sorted_idx = np.take_along_axis(idx, order, axis=1)
        sorted_sim = np.take_along_axis(sims, sorted_idx, axis=1)
        all_idx.append(sorted_idx)
        all_sim.append(sorted_sim)
    return np.vstack(all_idx), np.vstack(all_sim)


def specificity_factor(technical_means: str) -> float:
    terms = [t.strip() for t in clean_value(technical_means).split(";") if t.strip()]
    return min(1.2, 0.6 + 0.15 * len(terms))


def target_gap_factor(problem: str) -> float:
    text = clean_value(problem).lower()
    score = 1.0
    for pattern in ["residue", "particle", "contaminant", "redeposition", "damage", "残渣", "粒子", "汚染", "再付着", "損傷"]:
        if pattern in text:
            score += 0.05
    return min(score, 1.25)


def why_candidate(row: pd.Series) -> str:
    means = clean_value(row.get("source_technical_means", "")) or "洗浄・除去・リンス系の解決手段"
    target = clean_value(row.get("target_problem_context", ""), 80)
    return (
        f"半導体洗浄側の課題文脈（{target}）と近いproblem_contextを持ち、"
        f"参照分野側では{means}を解決手段としているため、専門家確認候補として抽出された。"
    )


def possible_connection(row: pd.Series) -> str:
    means = clean_value(row.get("source_technical_means", "")) or "洗浄手段"
    target_object = clean_value(row.get("source_target_object", "")) or "表面・基材"
    return f"{means}による{target_object}への残渣・粒子・汚染制御が、半導体洗浄課題との発明主題レベルの比較対象になりうる。"


def build_similarity_and_rankings(
    specs: dict[str, DatasetSpec],
    cfg: dict[str, Any],
    cache_dir: Path,
    output_dir: Path,
) -> pd.DataFrame:
    source_keys = cfg["analysis"]["source_datasets"]
    target_key = cfg["analysis"]["target_dataset"]
    top_k = int(cfg["analysis"]["top_k"])
    candidate_limit = int(cfg["analysis"]["candidate_limit"])
    chunk_size = int(cfg["analysis"].get("similarity_chunk_size", 256))

    source_metas = []
    source_problem = []
    source_solution = []
    source_fulltext = []
    for key in source_keys:
        spec = specs[key]
        source_metas.append(load_meta(cache_dir, spec.dataset_id))
        source_problem.append(load_vectors(cache_dir, spec.dataset_id, "problem"))
        source_solution.append(load_vectors(cache_dir, spec.dataset_id, "solution"))
        source_fulltext.append(load_vectors(cache_dir, spec.dataset_id, "fulltext"))
    meta_source = pd.concat(source_metas, ignore_index=True)
    emb_source_problem = np.vstack(source_problem)
    emb_source_solution = np.vstack(source_solution)
    emb_source_fulltext = np.vstack(source_fulltext)

    target_spec = specs[target_key]
    meta_target = load_meta(cache_dir, target_spec.dataset_id)
    emb_target_problem = load_vectors(cache_dir, target_spec.dataset_id, "problem")
    emb_target_solution = load_vectors(cache_dir, target_spec.dataset_id, "solution")
    emb_target_fulltext = load_vectors(cache_dir, target_spec.dataset_id, "fulltext")

    idx, problem_sims = topk_indices(emb_target_problem, emb_source_problem, top_k, chunk_size)
    problem_rows = []
    candidate_rows = []
    for target_i in range(idx.shape[0]):
        t = meta_target.iloc[target_i]
        for rank in range(idx.shape[1]):
            source_i = int(idx[target_i, rank])
            s = meta_source.iloc[source_i]
            problem_sim = float(problem_sims[target_i, rank])
            solution_sim = float(np.dot(emb_target_solution[target_i], emb_source_solution[source_i]))
            fulltext_sim = float(np.dot(emb_target_fulltext[target_i], emb_source_fulltext[source_i]))
            spec_factor = specificity_factor(s.get("technical_means", ""))
            gap_factor = target_gap_factor(t.get("problem_context", ""))
            novelty_a = max(0.0, 1.0 - solution_sim)
            novelty_b = max(0.0, 1.0 - abs(solution_sim - 0.5))
            score_a = problem_sim * novelty_a * spec_factor * gap_factor
            score_b = problem_sim * novelty_b * spec_factor * gap_factor
            score_c = problem_sim * spec_factor * gap_factor
            base = {
                "target_publication_number": t.get("publication_number", ""),
                "source_publication_number": s.get("publication_number", ""),
                "target_problem_context": t.get("problem_context", ""),
                "source_problem_context": s.get("problem_context", ""),
                "target_solution_context": t.get("solution_context", ""),
                "source_solution_context": s.get("solution_context", ""),
                "problem_similarity": problem_sim,
                "solution_similarity": solution_sim,
                "fulltext_similarity": fulltext_sim,
                "source_technical_means": s.get("technical_means", ""),
                "source_target_object": s.get("target_object", ""),
                "target_object": t.get("target_object", ""),
                "applicant_names": s.get("applicant_names", ""),
                "family_id_simple": s.get("family_id_simple", ""),
                "filing_year": s.get("filing_year", ""),
                "source_dataset_id": s.get("dataset_id", ""),
                "source_family_id": s.get("family_id", ""),
                "source_title": s.get("title", ""),
                "source_abstract": s.get("abstract", ""),
                "source_claims_short": s.get("claims_short", ""),
                "target_title": t.get("title", ""),
                "ipc_codes": s.get("ipc_codes", ""),
                "cpc_codes": s.get("cpc_codes", ""),
                "source_specificity_factor": spec_factor,
                "target_gap_factor": gap_factor,
                "heterogeneous_score_a": score_a,
                "heterogeneous_score_b": score_b,
                "heterogeneous_score_c": score_c,
                "is_kao": s.get("is_kao", 0),
            }
            problem_rows.append({
                **{k: base[k] for k in [
                    "target_publication_number",
                    "source_publication_number",
                    "target_problem_context",
                    "source_problem_context",
                    "target_solution_context",
                    "source_solution_context",
                    "problem_similarity",
                    "source_technical_means",
                    "target_object",
                    "applicant_names",
                    "family_id_simple",
                    "filing_year",
                ]},
                "neighbor_rank": rank + 1,
            })
            candidate_rows.append(base)

    pd.DataFrame(problem_rows).to_csv(output_dir / "problem_similarity_topk.csv", index=False, encoding="utf-8")
    candidates = pd.DataFrame(candidate_rows)
    candidates = candidates.sort_values(["heterogeneous_score_a", "problem_similarity"], ascending=False)
    candidates = candidates.drop_duplicates("source_publication_number", keep="first").reset_index(drop=True)
    candidates.insert(0, "rank", range(1, len(candidates) + 1))
    candidates["human_review_label"] = ""
    candidates["human_review_note"] = ""
    candidates.head(candidate_limit).to_csv(output_dir / "heterogeneous_candidate_ranking.csv", index=False, encoding="utf-8")
    return candidates.head(candidate_limit)


def known_positive_checks(
    specs: dict[str, DatasetSpec],
    cfg: dict[str, Any],
    cache_dir: Path,
    output_dir: Path,
    ranking: pd.DataFrame,
) -> None:
    s1_spec = specs[cfg["analysis"]["known_positive_dataset"]]
    s0_spec = specs[cfg["analysis"]["target_dataset"]]
    c1_spec = specs["C1"]
    s1_meta = load_meta(cache_dir, s1_spec.dataset_id)
    s0_meta = load_meta(cache_dir, s0_spec.dataset_id)
    c1_meta = load_meta(cache_dir, c1_spec.dataset_id)
    s1_problem = load_vectors(cache_dir, s1_spec.dataset_id, "problem")
    s1_solution = load_vectors(cache_dir, s1_spec.dataset_id, "solution")
    s0_problem = load_vectors(cache_dir, s0_spec.dataset_id, "problem")
    c1_problem = load_vectors(cache_dir, c1_spec.dataset_id, "problem")

    s0_centroid = s0_problem.mean(axis=0)
    s0_centroid = s0_centroid / (np.linalg.norm(s0_centroid) or 1.0)
    c1_centroid = c1_problem.mean(axis=0)
    c1_centroid = c1_centroid / (np.linalg.norm(c1_centroid) or 1.0)
    s1_s0_sim = s1_problem @ s0_centroid
    s1_c1_sim = s1_problem @ c1_centroid
    idx, sims = topk_indices(s1_problem, s0_problem, top_k=5, chunk_size=128)

    rows = []
    for i, row in s1_meta.iterrows():
        rows.append({
            "s1_publication_number": row.get("publication_number", ""),
            "s1_title": row.get("title", ""),
            "s1_problem_context": row.get("problem_context", ""),
            "s1_solution_context": row.get("solution_context", ""),
            "s1_technical_means": row.get("technical_means", ""),
            "is_kao": row.get("is_kao", ""),
            "similarity_to_s0_problem_centroid": float(s1_s0_sim[i]),
            "similarity_to_c1_problem_centroid": float(s1_c1_sim[i]),
            "nearest_s0_publication_number": s0_meta.iloc[int(idx[i, 0])].get("publication_number", "") if len(s0_meta) else "",
            "nearest_s0_problem_similarity": float(sims[i, 0]) if len(s0_meta) else math.nan,
        })
    pd.DataFrame(rows).to_csv(output_dir / "s1_known_positive_summary.csv", index=False, encoding="utf-8")

    if len(s1_solution):
        s1_solution_centroid = s1_solution.mean(axis=0)
        s1_solution_centroid = s1_solution_centroid / (np.linalg.norm(s1_solution_centroid) or 1.0)
        ranking = ranking.copy()
        source_ids = ranking["source_dataset_id"].astype(str).tolist()
        source_nums = ranking["source_publication_number"].astype(str).tolist()
        source_meta_map = {}
        source_solution_map = {}
        for key in cfg["analysis"]["source_datasets"]:
            spec = specs[key]
            meta = load_meta(cache_dir, spec.dataset_id)
            emb = load_vectors(cache_dir, spec.dataset_id, "solution")
            for j, pub in enumerate(meta["publication_number"].astype(str)):
                source_meta_map[(spec.dataset_id, pub)] = j
                source_solution_map[spec.dataset_id] = emb
        nearest = []
        for ds, pub in zip(source_ids, source_nums):
            j = source_meta_map.get((ds, pub))
            if j is None:
                nearest.append(math.nan)
            else:
                nearest.append(float(np.dot(source_solution_map[ds][j], s1_solution_centroid)))
        ranking["similarity_to_s1_solution_centroid"] = nearest
        ranking.sort_values("similarity_to_s1_solution_centroid", ascending=False).head(500).to_csv(
            output_dir / "s1_no_leakage_check.csv", index=False, encoding="utf-8"
        )
    else:
        pd.DataFrame().to_csv(output_dir / "s1_no_leakage_check.csv", index=False, encoding="utf-8")

    cards = ["# S1 Core Representative Patent Cards", ""]
    for i, row in s1_meta.head(20).iterrows():
        cards += [
            f"## {i + 1}. {row.get('publication_number', '')}",
            "",
            f"- Title: {row.get('title', '')}",
            f"- Problem: {row.get('problem_context', '')}",
            f"- Solution: {row.get('solution_context', '')}",
            f"- Technical means: {row.get('technical_means', '')}",
            "",
        ]
    (output_dir / "s1_representative_patent_cards.md").write_text("\n".join(cards), encoding="utf-8")


def build_manual_review(output_dir: Path, ranking: pd.DataFrame, limit: int) -> None:
    rows = []
    for _, row in ranking.head(limit).iterrows():
        rows.append({
            "review_id": f"HR-{len(rows) + 1:04d}",
            "rank": row.get("rank", ""),
            "candidate_type": "heterogeneous_solution",
            "source_publication_number": row.get("source_publication_number", ""),
            "source_title": row.get("source_title", ""),
            "source_abstract": row.get("source_abstract", ""),
            "source_claims_short": row.get("source_claims_short", ""),
            "source_problem_context": row.get("source_problem_context", ""),
            "source_solution_context": row.get("source_solution_context", ""),
            "source_technical_means": row.get("source_technical_means", ""),
            "source_target_object": row.get("source_target_object", ""),
            "target_publication_number": row.get("target_publication_number", ""),
            "target_title": row.get("target_title", ""),
            "target_problem_context": row.get("target_problem_context", ""),
            "target_solution_context": row.get("target_solution_context", ""),
            "problem_similarity": row.get("problem_similarity", ""),
            "solution_similarity": row.get("solution_similarity", ""),
            "heterogeneous_score": row.get("heterogeneous_score_a", ""),
            "why_candidate": why_candidate(row),
            "possible_connection": possible_connection(row),
            "concern": "類似度は発明主題レベルのスクリーニング指標であり、技術導入可能性を直接示すものではない。",
            "human_label": "",
            "human_note": "",
        })
    pd.DataFrame(rows).to_csv(output_dir / "manual_review_candidates.csv", index=False, encoding="utf-8")


def make_figures(output_dir: Path, summary: pd.DataFrame, ranking: pd.DataFrame, cache_dir: Path, specs: dict[str, DatasetSpec]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    x = np.arange(len(summary))
    width = 0.35
    plt.figure(figsize=(8, 4.5))
    plt.bar(x - width / 2, summary["publication_records"], width, label="Publication")
    plt.bar(x + width / 2, summary["family_records"], width, label="Family")
    plt.xticks(x, summary["dataset_key"])
    plt.ylabel("Records")
    plt.title("Dataset Size")
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_dir / "dataset_size_bar.png", dpi=180)
    plt.close()

    sample = ranking.head(5000)
    plt.figure(figsize=(6, 5))
    colors = np.where(pd.to_numeric(sample.get("is_kao", 0), errors="coerce").fillna(0).astype(int) == 1, "#d62728", "#4c78a8")
    plt.scatter(sample["problem_similarity"], sample["solution_similarity"], s=12, c=colors, alpha=0.55)
    plt.xlabel("Problem similarity")
    plt.ylabel("Solution similarity")
    plt.title("Problem vs Solution Similarity")
    plt.tight_layout()
    plt.savefig(fig_dir / "problem_solution_scatter.png", dpi=180)
    plt.close()

    heat = sample.copy()
    heat["target_cluster"] = heat["target_object"].fillna("").replace("", "unknown").str.split(";").str[0].str.strip()
    heat["source_cluster"] = heat["source_technical_means"].fillna("").replace("", "unknown").str.split(";").str[0].str.strip()
    pivot = pd.crosstab(heat["target_cluster"], heat["source_cluster"]).iloc[:12, :12]
    plt.figure(figsize=(9, 6))
    plt.imshow(pivot.values, aspect="auto", cmap="Blues")
    plt.xticks(range(len(pivot.columns)), pivot.columns, rotation=45, ha="right", fontsize=8)
    plt.yticks(range(len(pivot.index)), pivot.index, fontsize=8)
    plt.colorbar(label="Top candidate count")
    plt.title("S0 Target Object x Source Technical Means")
    plt.tight_layout()
    plt.savefig(fig_dir / "top_candidates_heatmap.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4.5))
    for key in ["C1", "S1_core", "S0"]:
        spec = specs[key]
        meta = load_meta(cache_dir, spec.dataset_id)
        counts = pd.to_numeric(meta["filing_year"], errors="coerce").dropna().astype(int).value_counts().sort_index()
        plt.plot(counts.index, counts.values, marker="o", label=key)
    plt.xlabel("Filing year")
    plt.ylabel("Publication count")
    plt.title("Filing Year Trend")
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_dir / "filing_year_trend.png", dpi=180)
    plt.close()

    plt.figure(figsize=(10, 3.2))
    plt.axis("off")
    boxes = [
        ("S0 problems", 0.06),
        ("C0/C1 similar problems", 0.30),
        ("Heterogeneous\nsolution candidates", 0.56),
        ("Expert review", 0.82),
    ]
    for label, x0 in boxes:
        plt.text(x0, 0.55, label, ha="center", va="center", fontsize=11,
                 bbox=dict(boxstyle="round,pad=0.35", fc="#eef3f8", ec="#456"))
    for x0, x1 in [(0.15, 0.23), (0.41, 0.49), (0.68, 0.75)]:
        plt.annotate("", xy=(x1, 0.55), xytext=(x0, 0.55), arrowprops=dict(arrowstyle="->", lw=1.8))
    plt.title("Heterogeneous Solution Screening Framework")
    plt.tight_layout()
    plt.savefig(fig_dir / "framework_heterogeneous_solution.png", dpi=180)
    plt.close()


def write_report(output_dir: Path, summary: pd.DataFrame, vector_summary: pd.DataFrame, ranking: pd.DataFrame) -> None:
    top = ranking.head(10)[[
        "rank", "source_publication_number", "source_title", "problem_similarity",
        "solution_similarity", "heterogeneous_score_a", "source_technical_means"
    ]]
    lines = [
        "# Heterogeneous Analysis Report",
        "",
        "## 1. 目的",
        "洗浄・除去・リンス系技術から、半導体洗浄分野の課題文脈に近い発明主題レベルの専門家確認候補を抽出した。",
        "",
        "## 2. 使用データ",
        df_to_markdown(summary),
        "",
        "## 3. 前処理結果",
        "publication_number単位とfamily_id_simple単位の表を分け、Title/Abstract/Claimsの取得率、Kao判定、IPC/CPC正規化を確認した。",
        "",
        "## 4. 文脈抽出カバレッジ",
        "Title, Abstract, Claimsからproblem_context, solution_context, effect_context, target_object, technical_meansをルールベースで抽出した。LLM抽出済み列への差し替えが可能な中間CSV構成にしている。",
        "",
        "## 5. ベクトル化結果",
        df_to_markdown(vector_summary.head(20)),
        "",
        "## 6. Problem Similarity結果",
        "`problem_similarity_topk.csv` に、S0の課題文脈に近いC0/C1側の近傍候補を保存した。",
        "",
        "## 7. Heterogeneous Solution Candidate結果",
        "heterogeneous_score_a, heterogeneous_score_b, heterogeneous_score_cを比較用に出力した。A案は解決手段類似度が低いほど新規性を高く置き、B案は中程度の異質性を評価し、C案はproblem_similarityを主スコアとして保持する。",
        "",
        df_to_markdown(top),
        "",
        "## 8. S1_core Known Positive確認",
        "`s1_known_positive_summary.csv` と `s1_no_leakage_check.csv` に、既知接続事例であるS1_coreの位置づけと、候補探索時にS1をsource側へ混入しない確認結果を保存した。",
        "",
        "## 9. 代表候補例",
        "`manual_review_candidates.csv` を人手確認用の一次候補リストとして出力した。",
        "",
        "## 10. 限界",
        "本分析は技術導入可能性や事業化可能性を証明するものではない。類似度は発明主題レベルのスクリーニング指標であり、材料適合性、プロセス条件、権利範囲、事業適合性は専門家確認が必要である。",
        "",
        "## 11. 次に人手確認すべき項目",
        "- source_technical_means が半導体洗浄課題に対して比較可能な発明主題か",
        "- target_problem_context と source_problem_context の近さが実質的か",
        "- solution_similarity が低すぎて無関係候補になっていないか",
        "- S1_core近傍候補との関係がデータリークなしに説明できるか",
        "",
    ]
    (output_dir / "heterogeneous_analysis_report.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run heterogeneous cleaning-to-semiconductor patent analysis.")
    parser.add_argument("--config", default="config/heterogeneous_exports2.yaml")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-vectorization", action="store_true")
    parser.add_argument("--skip-figures", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pipeline_dir = Path(__file__).parent.parent
    config_path = resolve_pipeline_path(pipeline_dir, args.config)
    cfg = load_config(config_path)
    specs = dataset_specs(cfg, pipeline_dir)
    output_dir = resolve_pipeline_path(pipeline_dir, cfg["paths"]["output_dir"])
    cache_dir = resolve_pipeline_path(pipeline_dir, cfg["paths"]["cache_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    chunksize = int(cfg["analysis"]["chunksize"])
    summary = write_dataset_summary(specs, output_dir, chunksize)
    print(f"saved dataset summary: {output_dir / 'dataset_summary.csv'}")

    build_contexts(specs, cache_dir, chunksize, args.overwrite)

    if args.skip_vectorization:
        vector_summary = pd.read_csv(output_dir / "vectorization_summary.csv")
    else:
        vector_summary = vectorize_contexts(
            specs=specs,
            cache_dir=cache_dir,
            output_dir=output_dir,
            model_name=cfg["embedding"]["model_name"],
            batch_size=int(cfg["embedding"]["batch_size"]),
            device=str(cfg["embedding"].get("device", "auto")),
            chunksize=chunksize,
            normalize=bool(cfg["embedding"].get("normalize", True)),
            overwrite=args.overwrite,
        )

    ranking = build_similarity_and_rankings(specs, cfg, cache_dir, output_dir)
    known_positive_checks(specs, cfg, cache_dir, output_dir, ranking)
    build_manual_review(output_dir, ranking, int(cfg["analysis"]["manual_review_limit"]))

    if not args.skip_figures:
        make_figures(output_dir, summary, ranking, cache_dir, specs)
    write_report(output_dir, summary, vector_summary, ranking)
    print(f"saved report: {output_dir / 'heterogeneous_analysis_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
