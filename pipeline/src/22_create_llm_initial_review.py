from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[2]
IN_DIR = BASE / "pipeline/outputs/manual_review_evaluation"
BLIND_PATH = IN_DIR / "manual_review_blind.csv"
RUBRIC_PATH = IN_DIR / "manual_review_rubric.md"

OUT_INITIAL_CSV = IN_DIR / "llm_initial_review.csv"
OUT_INITIAL_XLSX = IN_DIR / "llm_initial_review.xlsx"
OUT_WITH_LLM_CSV = IN_DIR / "manual_review_with_llm_suggestions.csv"
OUT_WITH_LLM_XLSX = IN_DIR / "manual_review_with_llm_suggestions.xlsx"
OUT_LOG = IN_DIR / "llm_initial_review_log.md"
OUT_METHOD_NOTE = IN_DIR / "llm_assisted_review_method_note.md"

LLM_MODEL_NAME = "Codex (GPT-5)"
LLM_TEMPERATURE = "not exposed in this environment"

LLM_COLUMNS = [
    "llm_problem_extraction_score",
    "llm_solution_extraction_score",
    "llm_technical_means_score",
    "llm_target_object_score",
    "llm_problem_similarity_score",
    "llm_solution_relevance_score",
    "llm_candidate_score",
    "llm_representative_flag",
    "llm_final_label",
    "llm_reviewer_comment_short",
    "llm_reviewer_comment_detail",
    "llm_confidence",
]

HUMAN_COLUMNS = [
    "human_problem_extraction_score",
    "human_solution_extraction_score",
    "human_technical_means_score",
    "human_target_object_score",
    "human_problem_similarity_score",
    "human_solution_relevance_score",
    "human_candidate_score",
    "human_representative_flag",
    "human_final_label",
    "human_reviewer_comment",
    "human_modified_flag",
]

FORBIDDEN_EVAL_COLUMNS = {
    "rank",
    "score",
    "gap_score",
    "similarity_score",
    "method_source",
    "proposed_or_baseline",
}


def text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def haystack(row: pd.Series, cols: list[str] | None = None) -> str:
    if cols is None:
        cols = [
            "title",
            "abstract",
            "claims",
            "problem_context",
            "solution_context",
            "technical_means",
            "target_object",
            "method_name",
        ]
    return " ".join(text(row.get(col, "")) for col in cols).lower()


def contains_any(s: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, s, flags=re.IGNORECASE) for pattern in patterns)


def count_any(s: str, patterns: list[str]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, s, flags=re.IGNORECASE))


DIRECT_DEFECT_PATTERNS = [
    r"defect",
    r"anomal",
    r"abnormal",
    r"surface",
    r"inspection",
    r"quality inspection",
    r"visual inspection",
    r"machine vision",
    r"fault",
    r"瑕疵",
    r"缺陷",
    r"异常",
    r"異常",
    r"表面",
    r"検査",
    r"检测",
    r"质检",
    r"巡检",
    r"良否",
    r"外観",
]

MANUFACTURING_OBJECT_PATTERNS = [
    r"\bindustrial\b",
    r"\bmanufactur",
    r"\bmanufacturing product\b",
    r"\bindustrial product\b",
    r"\bworkpiece\b",
    r"\bpcb\b",
    r"\bboard\b",
    r"\bphotovoltaic\b",
    r"\btrain\b",
    r"\bchassis\b",
    r"\bcable\b",
    r"\bbridge\b",
    r"\bpin\b",
    r"\btransmission line\b",
    r"\bship wall\b",
    r"\bbelt\b",
    r"\bsilicone\b",
    r"\btoy\b",
    r"\bled\b",
    r"\bbonding wire\b",
    r"工業",
    r"工业",
    r"製造",
    r"产品",
    r"工件",
    r"部品",
    r"零件",
    r"基板",
    r"电路板",
    r"光伏",
    r"列车",
    r"底盘",
    r"电缆",
    r"桥",
    r"销钉",
    r"船舶",
    r"皮带",
    r"封装",
]

MEDICAL_PATTERNS = [
    r"medical",
    r"disease",
    r"patient",
    r"heart",
    r"lung",
    r"cardio",
    r"blood vessel",
    r"coronary",
    r"diabetic",
    r"foot",
    r"pathological",
    r"survival",
    r"x-ray",
    r"musculoskeletal",
    r"health",
    r"病理",
    r"疾病",
    r"心肺",
    r"血管",
    r"冠状",
    r"糖尿",
    r"健康",
    r"骨",
]

IMAGE_AI_PATTERNS = [
    r"image",
    r"画像",
    r"图像",
    r"visual",
    r"camera",
    r"撮像",
    r"segmentation",
    r"分割",
    r"detection",
    r"検出",
    r"检测",
    r"classification",
    r"分类",
    r"feature",
    r"特徴",
    r"特征",
    r"reconstruction",
    r"重构",
    r"生成",
]

SPECIFIC_METHOD_PATTERNS = [
    r"u-?net",
    r"\bunet\b",
    r"\byolo",
    r"\bgan\b",
    r"cyclegan",
    r"transformer",
    r"resnet",
    r"autoencoder",
    r"domain adaptation",
    r"\bcnn\b",
    r"\bsvm\b",
    r"\bpca\b",
    r"k-means",
    r"random forest",
    r"vgg",
    r"\bvit\b",
    r"encoder-decoder",
    r"principal component analysis",
    r"attention",
    r"注意",
]

GENERAL_METHOD_PATTERNS = [
    r"画像処理",
    r"画像分類",
    r"画像前処理",
    r"画像生成",
    r"画像セグメンテーション",
    r"深層学習モデル",
    r"機械学習モデル",
    r"検出方法",
    r"撮像装置",
    r"検査装置",
    r"特徴抽出",
    r"image processing",
    r"deep learning",
    r"machine learning",
    r"detection method",
]

WEAK_TOPIC_PATTERNS = [
    r"survival prediction",
    r"height prediction",
    r"human pose",
    r"visual focus",
    r"regional health big data",
    r"non-rigid registration",
    r"noise removal",
    r"super-resolution",
    r"repeat alarm",
    r"coal mining",
    r"生存预测",
    r"身高预测",
    r"人体位姿",
    r"视觉焦点",
    r"健康大数据",
    r"非刚性配准",
    r"噪声",
    r"超分辨率",
    r"重复报警",
    r"煤矿",
]


def problem_extraction_score(row: pd.Series) -> int:
    pc = text(row.get("problem_context", ""))
    full = haystack(row, ["problem_context", "title", "abstract", "claims"])
    if len(pc) < 20:
        return 0
    if contains_any(pc.lower(), DIRECT_DEFECT_PATTERNS + [r"accuracy", r"precision", r"efficien", r"improve", r"提高", r"准确", r"効率", r"課題", r"目的"]):
        return 2
    if contains_any(full, DIRECT_DEFECT_PATTERNS + IMAGE_AI_PATTERNS):
        return 1
    return 1


def solution_extraction_score(row: pd.Series) -> int:
    sc = text(row.get("solution_context", ""))
    if len(sc) < 30:
        return 0
    if contains_any(sc.lower(), IMAGE_AI_PATTERNS + SPECIFIC_METHOD_PATTERNS + [r"step", r"module", r"model", r"network", r"步骤", r"模块", r"模型"]):
        return 2
    return 1


def technical_means_score(row: pd.Series) -> int:
    tm = text(row.get("technical_means", ""))
    method = text(row.get("method_name", ""))
    combined = f"{tm} {method}".lower()
    if not tm and not method:
        return 0
    specific = contains_any(combined, SPECIFIC_METHOD_PATTERNS)
    generic = contains_any(combined, GENERAL_METHOD_PATTERNS)
    if specific:
        return 2
    if generic:
        return 1
    if len(tm) < 8:
        return 1
    return 1


def target_object_score(row: pd.Series) -> int:
    target = text(row.get("target_object", ""))
    full = haystack(row)
    if target and target.lower() not in {"nan", "none"}:
        if contains_any((target + " " + full).lower(), MANUFACTURING_OBJECT_PATTERNS + DIRECT_DEFECT_PATTERNS):
            return 2
        return 1
    if contains_any(full, MANUFACTURING_OBJECT_PATTERNS):
        return 1
    return 0


def problem_similarity_score(row: pd.Series) -> int:
    full = haystack(row, ["title", "abstract", "claims", "problem_context", "solution_context"])
    target_text = haystack(row, ["target_object"])
    direct = contains_any(full, DIRECT_DEFECT_PATTERNS)
    manufacturing = contains_any(full + " " + target_text, MANUFACTURING_OBJECT_PATTERNS)
    medical = contains_any(full, MEDICAL_PATTERNS)
    weak = contains_any(full, WEAK_TOPIC_PATTERNS)
    image_ai = contains_any(full, IMAGE_AI_PATTERNS)
    if medical and not manufacturing:
        return 1 if direct and image_ai and not weak else 0
    if direct and manufacturing:
        return 2
    if direct and image_ai and not weak:
        return 1 if medical else 2
    if image_ai and not weak:
        return 1
    return 0


def solution_relevance_score(row: pd.Series) -> int:
    full = haystack(row, ["title", "abstract", "claims", "problem_context", "solution_context", "technical_means", "method_name"])
    target_text = haystack(row, ["target_object"])
    direct = contains_any(full, DIRECT_DEFECT_PATTERNS)
    manufacturing = contains_any(full + " " + target_text, MANUFACTURING_OBJECT_PATTERNS)
    medical = contains_any(full, MEDICAL_PATTERNS)
    weak = contains_any(full, WEAK_TOPIC_PATTERNS)
    image_ai = contains_any(full, IMAGE_AI_PATTERNS)
    specific = contains_any(full, SPECIFIC_METHOD_PATTERNS)
    if medical and not manufacturing:
        return 1 if direct and image_ai and specific and not weak else 0
    if direct and manufacturing and (specific or image_ai) and not weak:
        return 2
    if direct and image_ai and specific:
        return 1
    if image_ai and specific and not weak:
        return 1
    if weak:
        return 0
    return 1 if image_ai else 0


def candidate_score(row: pd.Series, scores: dict[str, int]) -> int:
    full = haystack(row, ["title", "abstract", "claims", "problem_context", "solution_context", "technical_means", "method_name"])
    target_text = haystack(row, ["target_object"])
    direct = contains_any(full, DIRECT_DEFECT_PATTERNS)
    manufacturing = contains_any(full + " " + target_text, MANUFACTURING_OBJECT_PATTERNS)
    medical = contains_any(full, MEDICAL_PATTERNS)
    weak = contains_any(full, WEAK_TOPIC_PATTERNS)
    if medical and not manufacturing:
        return 1 if scores["llm_problem_similarity_score"] >= 1 and scores["llm_solution_relevance_score"] >= 1 else 0
    if (
        scores["llm_problem_similarity_score"] == 2
        and scores["llm_solution_relevance_score"] == 2
        and scores["llm_solution_extraction_score"] >= 1
        and scores["llm_technical_means_score"] >= 1
        and direct
        and manufacturing
        and not weak
    ):
        return 3
    if scores["llm_problem_similarity_score"] >= 1 and scores["llm_solution_relevance_score"] >= 1:
        if medical or weak:
            return 1
        return 2
    if scores["llm_problem_similarity_score"] == 0 and scores["llm_solution_relevance_score"] == 0:
        return 0
    return 1


def final_label(score: int) -> str:
    return {3: "◎", 2: "○", 1: "△", 0: "×"}.get(score, "△")


def confidence(row: pd.Series, scores: dict[str, int]) -> str:
    available_text = len(haystack(row, ["title", "abstract", "claims", "problem_context", "solution_context"]))
    if available_text < 120 or scores["llm_problem_extraction_score"] == 0 or scores["llm_solution_extraction_score"] == 0:
        return "low"
    if scores["llm_candidate_score"] in {0, 3} and scores["llm_problem_similarity_score"] != 1:
        return "high"
    return "medium"


def short_comment(row: pd.Series, scores: dict[str, int]) -> str:
    full = haystack(row)
    method = text(row.get("method_name", "")) or text(row.get("technical_means", ""))
    if scores["llm_candidate_score"] == 3:
        return "製造物や設備の欠陥・異常検出を画像処理で扱っており、専門家確認候補として強い。"
    if contains_any(full, MEDICAL_PATTERNS):
        return "画像中の異常検出・分割とは近いが、医療・健康用途が主題で製造欠陥検出とは対象がずれる。"
    if contains_any(full, WEAK_TOPIC_PATTERNS):
        return "画像処理や異常検出の要素はあるが、主題が製造欠陥検出から離れており代表例としては弱い。"
    if scores["llm_technical_means_score"] <= 1:
        return "課題との接点はあるが、技術手段が一般語寄りで具体的な候補としては慎重な確認が必要である。"
    if re.search(r"u-?net|unet", f"{method} {full}", flags=re.IGNORECASE):
        return "U-Net系の手法は確認できるが、対象・課題との対応を人手で確認する必要がある。"
    if scores["llm_candidate_score"] == 0:
        return "本文情報または課題対応が不足しており、製造欠陥検出候補としては弱い。"
    return "画像検査・異常検出への接点はあるが、対象や解決手段の対応は追加確認が必要である。"


def detail_comment(row: pd.Series, scores: dict[str, int]) -> str:
    problem_part = (
        "課題文脈は欠陥・異常検出の目的を比較的よく表している。"
        if scores["llm_problem_extraction_score"] == 2
        else "課題文脈は一部使えるが、目的や問題点の明確さに不足がある。"
        if scores["llm_problem_extraction_score"] == 1
        else "課題文脈は空欄または本文の問題点としては不十分である。"
    )
    solution_part = (
        "解決手段文脈は処理手順やモデル構成を読み取れる。"
        if scores["llm_solution_extraction_score"] == 2
        else "解決手段文脈は一部読めるが、構成や方法の説明が限定的である。"
        if scores["llm_solution_extraction_score"] == 1
        else "解決手段文脈が不足しており、方法の確認が難しい。"
    )
    tech_part = (
        "技術手段は具体的なモデル・アルゴリズム名を含む。"
        if scores["llm_technical_means_score"] == 2
        else "技術手段は関連するが一般語・抽象語が中心である。"
        if scores["llm_technical_means_score"] == 1
        else "技術手段名として使える情報が不足している。"
    )
    relevance_part = (
        "製造欠陥検出・画像検査への対応が明確で、代表特許候補として説明しやすい。"
        if scores["llm_candidate_score"] == 3
        else "画像中の異常・対象領域検出という水準では参考になるが、対象や用途のずれを人手で確認する必要がある。"
        if scores["llm_candidate_score"] == 2
        else "関連要素はあるものの、製造欠陥検出の代表例としては弱い。"
        if scores["llm_candidate_score"] == 1
        else "製造欠陥検出・画像検査への参考候補としては現時点で読み取りにくい。"
    )
    return f"{problem_part}{solution_part}{tech_part}{relevance_part}"


def evaluate_row(row: pd.Series) -> dict[str, Any]:
    scores = {
        "llm_problem_extraction_score": problem_extraction_score(row),
        "llm_solution_extraction_score": solution_extraction_score(row),
        "llm_technical_means_score": technical_means_score(row),
        "llm_target_object_score": target_object_score(row),
        "llm_problem_similarity_score": problem_similarity_score(row),
        "llm_solution_relevance_score": solution_relevance_score(row),
    }
    scores["llm_candidate_score"] = candidate_score(row, scores)
    scores["llm_representative_flag"] = int(
        scores["llm_candidate_score"] == 3
        or (
            scores["llm_candidate_score"] == 2
            and scores["llm_problem_similarity_score"] == 2
            and scores["llm_solution_relevance_score"] == 2
        )
    )
    scores["llm_final_label"] = final_label(scores["llm_candidate_score"])
    scores["llm_reviewer_comment_short"] = short_comment(row, scores)
    scores["llm_reviewer_comment_detail"] = detail_comment(row, scores)
    scores["llm_confidence"] = confidence(row, scores)
    return scores


def write_excel(df: pd.DataFrame, path: Path, sheet_name: str) -> None:
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)


def write_log(blind: pd.DataFrame, reviewed: pd.DataFrame, rubric_text: str) -> None:
    confidence_counts = reviewed["llm_confidence"].value_counts().reindex(["high", "medium", "low"], fill_value=0)
    score_counts = reviewed["llm_candidate_score"].value_counts().sort_index()
    label_counts = reviewed["llm_final_label"].value_counts().reindex(["◎", "○", "△", "×"], fill_value=0)
    unet_mask = reviewed[
        ["title", "technical_means", "method_name", "candidate_type", "problem_context", "solution_context"]
    ].fillna("").astype(str).agg(" ".join, axis=1).str.contains(r"u-?net|unet|u net", case=False, regex=True)
    unet_count = int(unet_mask.sum())
    unet_mean = reviewed.loc[unet_mask, "llm_candidate_score"].mean() if unet_count else ""

    lines = [
        "# LLM Initial Review Log",
        "",
        "## 使用した入力ファイル",
        "",
        f"- `{BLIND_PATH.relative_to(BASE)}`",
        f"- `{RUBRIC_PATH.relative_to(BASE)}`",
        "- `manual_review_key.csv`, `manual_review_summary.csv`, `manual_review_summary.md` はLLM評価時に使用していません。",
        "",
        "## 評価設定",
        "",
        f"- 評価対象件数: {len(reviewed)}",
        f"- 使用したLLMモデル名: {LLM_MODEL_NAME}",
        f"- 利用日: {datetime.now().strftime('%Y-%m-%d')}",
        f"- temperature: {LLM_TEMPERATURE}",
        "",
        "## 評価基準の概要",
        "",
        "- 文脈抽出評価: problem_context / solution_context / technical_means / target_object が本文内容を評価に使える形で表しているかを0-2で仮評価。",
        "- 候補評価: 製造欠陥検出・画像検査・異常検出への課題類似性、解決手段の参考可能性、代表例としての説明しやすさを仮評価。",
        "- `llm_candidate_score`: 3=◎, 2=○, 1=△, 0=×。",
        "",
        "## 重要な注意",
        "",
        "- LLM評価は最終評価ではなく、人間確認前の仮評価です。",
        "- 最終的な `candidate_score` と `final_label` は、人間が本文とrubricを確認して決定します。",
        "- rank / score / source 情報を見ず、blindファイルの本文・文脈情報のみで評価しました。",
        "",
        "## 欠損値や本文不足の扱い",
        "",
        "- 欠損値は空欄として扱いました。",
        "- problem_context または solution_context が不足する場合は、抽出評価を低めにし、判断根拠が弱い場合は `llm_confidence = low` としました。",
        "- 一般語中心の技術手段は `llm_technical_means_score` を1以下に抑える方針で仮評価しました。",
        "",
        "## confidence 件数",
        "",
    ]
    for label, count in confidence_counts.items():
        lines.append(f"- {label}: {int(count)}")
    lines.extend(["", "## llm_candidate_score 件数", ""])
    for score, count in score_counts.items():
        lines.append(f"- {int(score)}: {int(count)}")
    lines.extend(["", "## llm_final_label 件数", ""])
    for label, count in label_counts.items():
        lines.append(f"- {label}: {int(count)}")
    lines.extend(
        [
            "",
            "## U-Net関連候補",
            "",
            f"- 件数: {unet_count}",
            f"- llm_candidate_score平均: {unet_mean:.3f}" if unet_count else "- llm_candidate_score平均: N/A",
            "",
            "## 出力ファイル",
            "",
            f"- `{OUT_INITIAL_CSV.relative_to(BASE)}`",
            f"- `{OUT_INITIAL_XLSX.relative_to(BASE)}`",
            f"- `{OUT_WITH_LLM_CSV.relative_to(BASE)}`",
            f"- `{OUT_WITH_LLM_XLSX.relative_to(BASE)}`",
            f"- `{OUT_METHOD_NOTE.relative_to(BASE)}`",
            "",
            "## rubric 参照概要",
            "",
            rubric_text[:1200].strip(),
        ]
    )
    OUT_LOG.write_text("\n".join(lines), encoding="utf-8")


def write_method_note() -> None:
    note = """# LLM支援付き人手評価の方法メモ

本研究では、提案手法により抽出されたクロスドメイン技術候補について、LLM支援付き人手評価を実施する。LLMは各候補のTitle、Abstract、Claims、problem_context、solution_context、technical_means、target_object、effect_context、application_field等を入力として、事前に定義したrubricに基づく初期評価案を作成する。

LLMによる評価は最終判定ではなく、人間の評価作業を補助するための仮評価である。最終的なcandidate_scoreおよびfinal_labelは、著者が特許本文、抽出文脈、技術手段、対象分野との対応を確認したうえで決定・修正する。

評価基準は、課題文脈抽出、解決手段文脈抽出、技術手段名、対象物の妥当性に加え、参照分野と対象分野の課題類似性、解決手段の参考可能性、卒論本文で代表例として説明できるかを含む。これにより、単にランキング上位であるかではなく、人が読んでも専門家確認候補として妥当かを確認できる形式に整理する。

LLM評価の限界として、特許文書の機械翻訳・抽出誤差、請求項の長文構造、分野固有語の解釈、対象分野の専門的妥当性判断には不確実性が残る。そのため、LLMのスコアやコメントは評価者の注意喚起・一次整理として用い、最終的な研究結果には人間による確認後の評価値を用いる。
"""
    OUT_METHOD_NOTE.write_text(note, encoding="utf-8")


def main() -> None:
    blind = pd.read_csv(BLIND_PATH, encoding="utf-8-sig")
    rubric_text = RUBRIC_PATH.read_text(encoding="utf-8")

    leaked = sorted(FORBIDDEN_EVAL_COLUMNS & set(blind.columns))
    if leaked:
        raise ValueError(f"Bias-prone columns are present in manual_review_blind.csv: {leaked}")

    eval_rows = [evaluate_row(row) for _, row in blind.iterrows()]
    eval_df = pd.DataFrame(eval_rows)
    reviewed = pd.concat([blind.copy(), eval_df], axis=1)

    with_llm = reviewed.copy()
    for col in HUMAN_COLUMNS:
        with_llm[col] = ""

    reviewed.to_csv(OUT_INITIAL_CSV, index=False, encoding="utf-8-sig")
    with_llm.to_csv(OUT_WITH_LLM_CSV, index=False, encoding="utf-8-sig")
    write_excel(reviewed, OUT_INITIAL_XLSX, "llm_initial_review")
    write_excel(with_llm, OUT_WITH_LLM_XLSX, "manual_review_with_llm")
    write_log(blind, reviewed, rubric_text)
    write_method_note()

    print(f"Created LLM initial review rows: {len(reviewed)}")
    print(reviewed["llm_candidate_score"].value_counts().sort_index().to_string())
    print(reviewed["llm_confidence"].value_counts().to_string())


if __name__ == "__main__":
    main()
