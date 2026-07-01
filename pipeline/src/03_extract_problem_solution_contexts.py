"""
Script: 03_extract_problem_solution_contexts.py
Purpose: Title, Abstract, Claimsから課題文脈と解決手段文脈を分離する。

This step is LLM-ready:
  - heuristic: local deterministic extraction for reproducible pipeline runs.
  - prepare_llm: export JSONL requests using the thesis prompt.
  - merge_llm: merge previously generated LLM JSONL results into processed CSVs.

Input:
  - data/processed/A0_with_methods.csv
  - data/processed/B0_with_methods.csv
Output:
  - data/processed/A0_contexts.csv
  - data/processed/B0_contexts.csv
  - outputs/llm_requests/{domain}_problem_solution_requests.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


CONTEXT_FIELDS = [
    "problem_context",
    "solution_context",
    "technical_means",
    "target_object",
    "effect_context",
    "application_field",
    "problem_evidence",
    "solution_evidence",
    "extraction_confidence",
    "extraction_method",
]

PROBLEM_PATTERNS = [
    r"problem", r"issue", r"difficulty", r"challenge", r"drawback",
    r"disadvantage", r"need", r"required", r"limitation", r"failure",
    r"inaccur", r"noise", r"artifact", r"false positive", r"false negative",
    r"low contrast", r"irregular", r"課題", r"問題", r"困難", r"必要",
    r"従来", r"改善", r"誤検出", r"検出漏れ", r"精度", r"残渣",
    r"缺陷", r"问题", r"困难", r"提高", r"改善", r"不足",
]

SOLUTION_PATTERNS = [
    r"method", r"system", r"apparatus", r"model", r"network", r"algorithm",
    r"comprises", r"includes", r"configured to", r"using", r"based on",
    r"applying", r"training", r"segmentation", r"detection", r"classif",
    r"predict", r"encoder", r"decoder", r"architecture", r"layer",
    r"feature", r"output", r"generate", r"propos", r"解決手段", r"手段",
    r"方法", r"装置", r"システム", r"構成", r"モデル", r"処理",
    r"生成", r"学習", r"検出", r"分割", r"分類", r"本发明", r"包括",
]

EFFECT_PATTERNS = [
    r"effect", r"advantage", r"improve", r"reduce", r"enhance", r"faster",
    r"accur", r"efficient", r"robust", r"効果", r"向上", r"低減",
    r"削減", r"高速", r"高精度", r"改善", r"提高", r"降低",
]

METHOD_PATTERNS = [
    "U-Net", "UNet", "U Net", "nnU-Net", "U-Net++", "UNet++",
    "YOLO", "GAN", "CycleGAN", "Transformer", "Attention",
    "Autoencoder", "Auto-encoder", "CNN", "Domain Adaptation",
    "ResNet", "VGG", "EfficientNet", "ViT", "BERT",
    "encoder-decoder", "skip connection", "random forest", "support vector machine",
    "SVM", "k-means", "principal component analysis", "PCA",
]

TECHNICAL_MEANS_RULES = [
    ("画像セグメンテーション", [r"segmentation", r"segment", r"mask", r"領域分割", r"セグメンテーション", r"分割", r"分割マスク"]),
    ("欠陥検出", [r"defect detection", r"detect(?:ing|ion)? defects?", r"欠陥検出", r"異常検出", r"缺陷检测"]),
    ("故障検出", [r"fault detection", r"failure detection", r"detecci[oó]n de fallas", r"故障検出"]),
    ("非破壊検査", [r"non-destructive test", r"nondestructive test", r"dye penetration", r"非破壊検査", r"浸透探傷"]),
    ("物体検出", [r"object detection", r"detect(?:ing|ion)? objects?", r"物体検出", r"対象検出"]),
    ("画像分類", [r"classification", r"classifier", r"classif(?:y|ying)", r"分類器", r"画像分類"]),
    ("特徴抽出", [r"feature extraction", r"extract(?:ing)? features?", r"特徴抽出", r"特徴量"]),
    ("画像前処理", [r"preprocess", r"pre-processing", r"filtering", r"denois", r"補正", r"前処理", r"フィルタ"]),
    ("画像生成・再構成", [r"image generation", r"reconstruct", r"reconstruction", r"生成", r"再構成"]),
    ("畳み込みニューラルネットワーク", [r"convolutional neural network", r"\bCNN\b", r"畳み込みニューラル"]),
    ("エンコーダ・デコーダ構造", [r"encoder[- ]decoder", r"encoder", r"decoder", r"エンコーダ", r"デコーダ"]),
    ("注意機構", [r"attention", r"注意機構"]),
    ("深層学習モデル", [r"deep learning", r"neural network", r"ニューラルネット", r"深層学習"]),
    ("機械学習モデル", [r"machine learning", r"learning model", r"学習モデル", r"機械学習"]),
    ("教師あり学習", [r"supervised learning", r"teacher", r"教師あり"]),
    ("教師なし学習", [r"unsupervised learning", r"教師なし"]),
    ("転移学習", [r"transfer learning", r"domain adaptation", r"転移学習", r"ドメイン適応"]),
    ("撮像装置", [r"imaging apparatus", r"camera", r"X-ray", r"x ray", r"撮像装置", r"カメラ", r"画像取得"]),
    ("検査装置", [r"inspection apparatus", r"inspection system", r"検査装置", r"検査システム"]),
    ("画像処理システム", [r"image processing system", r"image processing apparatus", r"画像処理装置", r"画像処理システム"]),
    ("信号処理", [r"signal processing", r"信号処理"]),
    ("洗浄方法", [r"cleaning method", r"cleaning process", r"洗浄方法", r"洗浄処理"]),
    ("洗浄剤組成物", [r"cleaning composition", r"detergent composition", r"洗浄剤", r"組成物"]),
    ("基板処理方法", [r"substrate processing", r"wafer processing", r"基板処理", r"ウェハ処理"]),
]

TARGET_KEYWORDS = [
    ("医療画像", [r"medical image", r"biomedical", r"MRI", r"\bCT\b", r"tumou?r", r"lesion", r"病変", r"腫瘍", r"医学影像", r"医疗影像"]),
    ("製造物表面・欠陥", [r"defect", r"surface", r"steel", r"product", r"workpiece", r"wafer", r"substrate", r"欠陥", r"表面", r"検査", r"缺陷", r"表面"]),
    ("半導体・基板", [r"semiconductor", r"wafer", r"substrate", r"基板", r"半導体", r"晶圆"]),
]

MEDICAL_FIELD_RE = re.compile(
    r"medical|biomedical|clinical|patient|diagnos|MRI|\bCT\b|tumou?r|lesion|organ|"
    r"医療|医学|患者|診断|腫瘍|病変|臓器|医疗|医学影像",
    re.IGNORECASE,
)
MANUFACTURING_FIELD_RE = re.compile(
    r"defect|surface|inspection|manufactur|steel|metal|workpiece|product|"
    r"欠陥|表面|検査|製造|鋼材|金属|ワーク|缺陷|表面检测",
    re.IGNORECASE,
)
SEMICONDUCTOR_FIELD_RE = re.compile(
    r"semiconductor|wafer|substrate|基板|半導体|ウェハ|晶圆",
    re.IGNORECASE,
)


def compile_any(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)


PROBLEM_RE = compile_any(PROBLEM_PATTERNS)
SOLUTION_RE = compile_any(SOLUTION_PATTERNS)
EFFECT_RE = compile_any(EFFECT_PATTERNS)
METHOD_RE = [
    (m, re.compile(r"(?<![A-Za-z0-9])" + re.escape(m) + r"(?![A-Za-z0-9])", re.IGNORECASE))
    for m in METHOD_PATTERNS
]


def clean_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def join_nonempty(parts: list[str], sep: str = " ") -> str:
    return sep.join(p for p in (clean_value(x) for x in parts) if p)


def split_sentences(text: str) -> list[str]:
    text = clean_value(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+|(?<=。)|(?<=！)|(?<=？)|\n+", text)
    return [p.strip(" |") for p in parts if len(p.strip()) > 8]


def first_matches(sentences: list[str], pattern: re.Pattern, limit: int) -> list[str]:
    out = []
    for sentence in sentences:
        if pattern.search(sentence) and sentence not in out:
            out.append(sentence)
        if len(out) >= limit:
            break
    return out


def extract_marked_context(abstract: str) -> tuple[str, str, str]:
    """Extract Japanese patent-style marked sections when available."""
    text = clean_value(abstract)
    if not text:
        return "", "", ""

    problem = ""
    solution = ""
    effect = ""

    marker_patterns = {
        "problem": [
            r"【課題】(?P<x>.*?)(?=【解決手段】|【手段】|【効果】|$)",
            r"PROBLEM TO BE SOLVED[:：]?(?P<x>.*?)(?=SOLUTION[:：]?|MEANS|EFFECT|$)",
        ],
        "solution": [
            r"【解決手段】(?P<x>.*?)(?=【課題】|【効果】|$)",
            r"【手段】(?P<x>.*?)(?=【課題】|【効果】|$)",
            r"SOLUTION[:：]?(?P<x>.*?)(?=PROBLEM TO BE SOLVED|EFFECT|$)",
            r"MEANS FOR SOLVING THE PROBLEM[:：]?(?P<x>.*?)(?=EFFECT|$)",
        ],
        "effect": [
            r"【効果】(?P<x>.*?)(?=【課題】|【解決手段】|$)",
            r"EFFECT[:：]?(?P<x>.*?)(?=PROBLEM TO BE SOLVED|SOLUTION|$)",
        ],
    }
    for key, patterns in marker_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = clean_value(match.group("x"))
                if key == "problem":
                    problem = value
                elif key == "solution":
                    solution = value
                else:
                    effect = value
                break
    return problem, solution, effect


def detect_methods(text: str) -> str:
    found = []
    for name, pattern in METHOD_RE:
        if pattern.search(text) and name not in found:
            found.append(name)
    for label, patterns in TECHNICAL_MEANS_RULES:
        if label not in found and any(re.search(p, text, flags=re.IGNORECASE) for p in patterns):
            found.append(label)
        if len(found) >= 5:
            break
    return "; ".join(found[:5])


def fallback_technical_means(solution_context: str, claims: str, title: str) -> str:
    means = detect_methods(join_nonempty([solution_context, claims, title]))
    if means:
        return means

    source = solution_context or claims or title
    source = clean_value(source)
    if not source:
        return ""

    fallback_rules = [
        ("検出方法", [r"detection method", r"method for detecting", r"detecci[oó]n", r"検出方法"]),
        ("分析方法", [r"analysis method", r"method for analy", r"an[aá]lisis", r"分析方法"]),
        ("画像処理方法", [r"image processing method", r"画像処理方法"]),
        ("制御方法", [r"control method", r"制御方法"]),
        ("処理システム", [r"processing system", r"処理システム"]),
    ]
    for label, patterns in fallback_rules:
        if any(re.search(p, source, flags=re.IGNORECASE) for p in patterns):
            return label
    return ""


def detect_target(text: str) -> str:
    hits = []
    for label, patterns in TARGET_KEYWORDS:
        if any(re.search(p, text, flags=re.IGNORECASE) for p in patterns):
            hits.append(label)
    return "; ".join(hits)


def detect_application_field(domain: str, text: str) -> str:
    if SEMICONDUCTOR_FIELD_RE.search(text):
        return "半導体・基板処理"
    if MEDICAL_FIELD_RE.search(text):
        return "医療画像解析"
    if MANUFACTURING_FIELD_RE.search(text):
        return "製造欠陥検出"
    return "医療画像解析" if domain == "A0" else "製造欠陥検出"


def domain_noise_assessment(row: pd.Series, domain: str) -> dict[str, object]:
    text = join_nonempty([
        row.get("title", ""),
        row.get("abstract", ""),
        row.get("problem_context", ""),
        row.get("solution_context", ""),
        row.get("target_object", ""),
        row.get("application_field", ""),
    ])
    application_field = clean_value(row.get("application_field", ""))
    reasons = []

    if domain == "B0":
        if application_field == "医療画像解析" or (
            MEDICAL_FIELD_RE.search(text)
            and not (MANUFACTURING_FIELD_RE.search(text) or SEMICONDUCTOR_FIELD_RE.search(text))
        ):
            reasons.append("B0内の医療画像解析候補")
    elif domain == "A0":
        if application_field in {"製造欠陥検出", "半導体・基板処理"}:
            reasons.append(f"A0内の分野外候補: {application_field}")

    flag = int(bool(reasons))
    return {
        "domain_noise_flag": flag,
        "domain_noise_reason": "; ".join(reasons),
        "analysis_include": int(not flag),
    }


def heuristic_extract(row: pd.Series, domain: str) -> dict[str, str]:
    title = clean_value(row.get("title", ""))
    abstract = clean_value(row.get("abstract", ""))
    claims = clean_value(row.get("claims", ""))
    title_abstract = join_nonempty([title, abstract])
    full = join_nonempty([title, abstract, claims])

    marked_problem, marked_solution, marked_effect = extract_marked_context(abstract)

    abstract_sents = split_sentences(abstract)
    claim_sents = split_sentences(claims)

    problem_candidates = []
    if marked_problem:
        problem_candidates.append(marked_problem)
    problem_candidates += first_matches(abstract_sents, PROBLEM_RE, 2)
    if not problem_candidates and abstract_sents:
        problem_candidates.append(abstract_sents[0])

    solution_candidates = []
    if marked_solution:
        solution_candidates.append(marked_solution)
    solution_candidates += first_matches(abstract_sents, SOLUTION_RE, 2)
    solution_candidates += first_matches(claim_sents, SOLUTION_RE, 2)
    if not solution_candidates and claim_sents:
        solution_candidates.append(claim_sents[0])
    if not solution_candidates and len(abstract_sents) > 1:
        solution_candidates.append(abstract_sents[1])

    effect_candidates = []
    if marked_effect:
        effect_candidates.append(marked_effect)
    effect_candidates += first_matches(abstract_sents, EFFECT_RE, 1)

    problem_context = " ".join(problem_candidates[:3])
    solution_context = " ".join(solution_candidates[:3])
    effect_context = " ".join(effect_candidates[:1])

    confidence = "medium"
    if marked_problem and marked_solution:
        confidence = "high"
    elif not problem_context or not solution_context:
        confidence = "low"

    technical_means = fallback_technical_means(solution_context, claims, title)

    return {
        "problem_context": problem_context,
        "solution_context": solution_context,
        "technical_means": technical_means,
        "target_object": detect_target(title_abstract),
        "effect_context": effect_context,
        "application_field": detect_application_field(domain, title_abstract),
        "problem_evidence": marked_problem or (problem_candidates[0] if problem_candidates else ""),
        "solution_evidence": marked_solution or (solution_candidates[0] if solution_candidates else ""),
        "extraction_confidence": confidence,
        "extraction_method": "heuristic",
    }


def load_prompt(prompt_path: Path) -> str:
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "Extract problem_context and solution_context from Title, Abstract, and Claims. "
        "Return JSON only."
    )


def write_llm_requests(df: pd.DataFrame, domain: str, out_path: Path, prompt_text: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fp:
        for _, row in df.iterrows():
            pub = clean_value(row.get("publication_number", ""))
            payload = {
                "title": clean_value(row.get("title", "")),
                "abstract": clean_value(row.get("abstract", "")),
                "claims": clean_value(row.get("claims", "")),
            }
            line = {
                "custom_id": f"{domain}:{pub}",
                "publication_number": pub,
                "domain": domain,
                "messages": [
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            }
            fp.write(json.dumps(line, ensure_ascii=False) + "\n")


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def extract_response_payload(line: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    custom_id = line.get("custom_id") or line.get("id") or ""
    pub = line.get("publication_number") or ""
    if isinstance(custom_id, str) and ":" in custom_id and not pub:
        pub = custom_id.split(":", 1)[1]

    if all(field in line for field in ["problem_context", "solution_context"]):
        return str(pub), line

    try:
        body = line["response"]["body"]
        content = body["choices"][0]["message"]["content"]
        return str(pub), parse_json_object(content)
    except Exception:
        return None


def load_llm_results(results_dir: Path, domain: str, logger: logging.Logger) -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    if not results_dir.exists():
        logger.warning(f"LLM結果ディレクトリが存在しません: {results_dir}")
        return merged

    for path in sorted(results_dir.glob(f"{domain}*.jsonl")):
        logger.info(f"[{domain}] LLM結果読み込み: {path}")
        with path.open(encoding="utf-8") as fp:
            for line in fp:
                if not line.strip():
                    continue
                try:
                    parsed = json.loads(line)
                    payload = extract_response_payload(parsed)
                    if not payload:
                        continue
                    pub, values = payload
                    if not pub:
                        continue
                    values = dict(values)
                    if "extraction_confidence" not in values and "confidence" in values:
                        values["extraction_confidence"] = values["confidence"]
                    merged[pub] = {
                        field: "; ".join(values.get(field, [])) if isinstance(values.get(field), list)
                        else clean_value(values.get(field, ""))
                        for field in CONTEXT_FIELDS
                        if field not in {"extraction_method"}
                    }
                    merged[pub]["extraction_method"] = "llm"
                except Exception as exc:
                    logger.warning(f"LLM結果行の解析に失敗: {path}: {exc}")
    return merged


def apply_contexts(df: pd.DataFrame, contexts: list[dict[str, str]]) -> pd.DataFrame:
    ctx_df = pd.DataFrame(contexts, index=df.index)
    for field in CONTEXT_FIELDS:
        df[field] = ctx_df.get(field, "")
    return df


def apply_domain_qc(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    qc_df = pd.DataFrame([domain_noise_assessment(row, domain) for _, row in df.iterrows()], index=df.index)
    for col in ["domain_noise_flag", "domain_noise_reason", "analysis_include"]:
        df[col] = qc_df[col]
    return df


def main():
    parser = argparse.ArgumentParser(description="課題・解決手段文脈の抽出")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument(
        "--mode",
        choices=["heuristic", "prepare_llm", "merge_llm"],
        default="heuristic",
        help="heuristic: local extraction; prepare_llm: write JSONL requests; merge_llm: merge JSONL results.",
    )
    parser.add_argument("--llm-results-dir", default="outputs/llm_results")
    parser.add_argument("--prompt", default="prompts/problem_solution_extraction_prompt.md")
    parser.add_argument("--processed-dir", default=None, help="入出力processedディレクトリ（configより優先）")
    parser.add_argument(
        "--write-contexts",
        action="store_true",
        help="prepare_llmでもヒューリスティック文脈CSVを保存する。通常は保存しない。",
    )
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
    log_file = log_dir / f"03_extract_problem_solution_contexts_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("=== 03_extract_problem_solution_contexts.py 開始 ===")
    logger.info(f"mode={args.mode}")

    processed_dir = Path(args.processed_dir) if args.processed_dir else Path(cfg["data"]["processed_dir"])
    if not processed_dir.is_absolute():
        processed_dir = script_dir / processed_dir
    requests_dir = script_dir / cfg["data"]["output_dir"] / "llm_requests"
    prompt_path = Path(args.prompt)
    if not prompt_path.is_absolute():
        prompt_path = script_dir / prompt_path
    prompt_text = load_prompt(prompt_path)

    for domain in ["A0", "B0"]:
        in_path = processed_dir / f"{domain}_with_methods.csv"
        if not in_path.exists():
            logger.error(f"[{domain}] 入力ファイルが存在しません: {in_path}")
            logger.error("先に 02_extract_method_terms.py を実行してください。")
            continue

        df = pd.read_csv(in_path)
        logger.info(f"[{domain}] 読み込み: {len(df)}行")

        if args.sample and args.sample < len(df):
            df = df.sample(n=args.sample, random_state=42).reset_index(drop=True)
            logger.info(f"[{domain}] サンプリング: {len(df)}行")

        if args.mode == "prepare_llm":
            req_out = requests_dir / f"{domain}_problem_solution_requests.jsonl"
            write_llm_requests(df, domain, req_out, prompt_text)
            logger.info(f"[{domain}] LLMリクエスト保存: {req_out}")
            if not args.write_contexts:
                continue

        contexts: list[dict[str, str]] = []

        if args.mode == "merge_llm":
            results_dir = Path(args.llm_results_dir)
            if not results_dir.is_absolute():
                results_dir = script_dir / results_dir
            llm_by_pub = load_llm_results(results_dir, domain, logger)
            logger.info(f"[{domain}] LLM結果件数: {len(llm_by_pub)}")
            for _, row in df.iterrows():
                pub = clean_value(row.get("publication_number", ""))
                ctx = llm_by_pub.get(pub)
                if not ctx:
                    ctx = heuristic_extract(row, domain)
                    ctx["extraction_method"] = "heuristic_fallback"
                contexts.append(ctx)
        else:
            for i, row in df.iterrows():
                contexts.append(heuristic_extract(row, domain))
                if (i + 1) % 5000 == 0:
                    logger.info(f"[{domain}] {i+1}/{len(df)} 処理完了")

        df = apply_contexts(df, contexts)
        df = apply_domain_qc(df, domain)

        prob_nonempty = (df["problem_context"].fillna("") != "").sum()
        sol_nonempty = (df["solution_context"].fillna("") != "").sum()
        means_nonempty = (df["technical_means"].fillna("") != "").sum()
        logger.info(f"[{domain}] problem_context 非空: {prob_nonempty}/{len(df)}")
        logger.info(f"[{domain}] solution_context 非空: {sol_nonempty}/{len(df)}")
        logger.info(f"[{domain}] technical_means 非空: {means_nonempty}/{len(df)}")
        logger.info(f"[{domain}] application_field: {df['application_field'].value_counts().to_dict()}")
        logger.info(f"[{domain}] domain_noise_flag: {df['domain_noise_flag'].value_counts().to_dict()}")
        logger.info(f"[{domain}] extraction_method: {df['extraction_method'].value_counts().to_dict()}")

        out_path = processed_dir / f"{domain}_contexts.csv"
        df.to_csv(out_path, index=False, encoding="utf-8")
        logger.info(f"[{domain}] 保存: {out_path}")

    logger.info("=== 03_extract_problem_solution_contexts.py 完了 ===")


if __name__ == "__main__":
    main()
