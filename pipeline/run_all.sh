#!/bin/bash
# run_all.sh — 全パイプラインスクリプトを順番に実行する
# エラー発生時は即停止し、ログをoutputs/logs/に保存する

set -e  # エラー時即停止
set -u  # 未定義変数参照時にエラー

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="config/config.yaml"
LOG_DIR="outputs/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/run_all_${TIMESTAMP}.log"
WITH_EMBEDDINGS=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-embeddings)
            WITH_EMBEDDINGS=1
            shift
            ;;
        *)
            echo "ERROR: unknown option: $1"
            echo "Usage: bash run_all.sh [--with-embeddings]"
            exit 1
            ;;
    esac
done

# ログディレクトリの作成
mkdir -p "${SCRIPT_DIR}/${LOG_DIR}"

# ---------------------------------------------------------------------------
# ログ関数
# ---------------------------------------------------------------------------
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "${msg}"
    echo "${msg}" >> "${SCRIPT_DIR}/${LOG_FILE}"
}

log_separator() {
    local sep="================================================================"
    echo "${sep}"
    echo "${sep}" >> "${SCRIPT_DIR}/${LOG_FILE}"
}

# ---------------------------------------------------------------------------
# カレントディレクトリをパイプラインのルートに設定
# ---------------------------------------------------------------------------
cd "${SCRIPT_DIR}"

log "=== パイプライン実行開始 ==="
log "作業ディレクトリ: ${SCRIPT_DIR}"
log "設定ファイル: ${CONFIG}"
log "ログファイル: ${LOG_FILE}"
log "with_embeddings: ${WITH_EMBEDDINGS}"
log_separator

# ---------------------------------------------------------------------------
# Python の確認
# ---------------------------------------------------------------------------
if [ -x "${SCRIPT_DIR}/../.venv/bin/python" ]; then
    PYTHON="${SCRIPT_DIR}/../.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    log "ERROR: Python が見つかりません。インストールしてください。"
    exit 1
fi
log "Python: $(${PYTHON} --version)"
log_separator

SAMPLE_ARGS=()
if [ "${SAMPLE_N:-}" != "" ]; then
    SAMPLE_ARGS=(--sample "${SAMPLE_N}")
    log "サンプル実行: ${SAMPLE_N}件"
    log_separator
fi

CONTEXT_MODE="${CONTEXT_MODE:-heuristic}"
LLM_RESULTS_DIR="${LLM_RESULTS_DIR:-outputs/llm_results}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-sentence-transformers/all-MiniLM-L6-v2}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-32}"
TOP_K="${TOP_K:-10}"

# ---------------------------------------------------------------------------
# 00: 列チェック
# ---------------------------------------------------------------------------
log "[STEP 00] 列構造の確認"
${PYTHON} src/00_check_columns.py --config "${CONFIG}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 00] 完了"
log_separator

# ---------------------------------------------------------------------------
# 01: データ前処理
# ---------------------------------------------------------------------------
log "[STEP 01] データ前処理"
${PYTHON} src/01_preprocess_patents.py --config "${CONFIG}" "${SAMPLE_ARGS[@]}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 01] 完了"
log_separator

# ---------------------------------------------------------------------------
# 02: 技術手法語の抽出
# ---------------------------------------------------------------------------
log "[STEP 02] 技術手法語の抽出"
${PYTHON} src/02_extract_method_terms.py --config "${CONFIG}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 02] 完了"
log_separator

# ---------------------------------------------------------------------------
# 03: 課題・解決手段文脈の抽出
# ---------------------------------------------------------------------------
log "[STEP 03] 課題・解決手段文脈の抽出"
${PYTHON} src/03_extract_problem_solution_contexts.py --config "${CONFIG}" --mode "${CONTEXT_MODE}" --llm-results-dir "${LLM_RESULTS_DIR}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 03] 完了"
log_separator

if [ "${WITH_EMBEDDINGS}" -eq 1 ]; then
    # -----------------------------------------------------------------------
    # 04: 既存埋め込み計算（互換用）
    # -----------------------------------------------------------------------
    log "[STEP 04] 既存埋め込み計算（互換用）"
    if ${PYTHON} src/04_embed_patents.py --config "${CONFIG}" --domain both --type all 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"; then
        log "[STEP 04] 完了"
    else
        log "[STEP 04] 警告: 既存埋め込み計算に失敗しました。後続の新ベクトル化に進みます。"
    fi
    log_separator

    # -----------------------------------------------------------------------
    # 05: 既存ドメイン間類似度（互換用）
    # -----------------------------------------------------------------------
    log "[STEP 05] 既存ドメイン間類似度の計算（互換用）"
    ${PYTHON} src/05_compute_domain_similarity.py --config "${CONFIG}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
    log "[STEP 05] 完了"
    log_separator
else
    log "[STEP 04-05] 埋め込み系ステップをスキップ（--with-embeddings 指定時のみ実行）"
    log_separator
fi

# ---------------------------------------------------------------------------
# 06: Method Gap
# ---------------------------------------------------------------------------
log "[STEP 06] Method Gap の計算"
${PYTHON} src/06_compute_method_gap.py --config "${CONFIG}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 06] 完了"
log_separator

# ---------------------------------------------------------------------------
# 07: GapScoreランキング
# ---------------------------------------------------------------------------
log "[STEP 07] GapScoreランキングの生成"
${PYTHON} src/07_rank_candidates.py --config "${CONFIG}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 07] 完了"
log_separator

# ---------------------------------------------------------------------------
# 08: 後ろ向き評価
# ---------------------------------------------------------------------------
log "[STEP 08] 後ろ向き評価"
${PYTHON} src/08_temporal_evaluation.py --config "${CONFIG}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 08] 完了"
log_separator

# ---------------------------------------------------------------------------
# 09: ベースライン比較
# ---------------------------------------------------------------------------
log "[STEP 09] ベースライン比較"
${PYTHON} src/09_baseline_comparison.py --config "${CONFIG}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 09] 完了"
log_separator

if [ "${WITH_EMBEDDINGS}" -eq 1 ]; then
    # -----------------------------------------------------------------------
    # 10V: 卒論用 文脈ベクトル化
    # -----------------------------------------------------------------------
    log "[STEP 10V] 卒論用 文脈ベクトル化"
    ${PYTHON} src/10_vectorize_contexts.py \
        --input-dir data/processed \
        --output-dir data/processed/embeddings \
        --model "${EMBEDDING_MODEL}" \
        --batch-size "${EMBEDDING_BATCH_SIZE}" \
        --overwrite 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
    log "[STEP 10V] 完了"
    log_separator

    # -----------------------------------------------------------------------
    # 11V: A0/B0 Top-k類似度
    # -----------------------------------------------------------------------
    log "[STEP 11V] A0/B0 Top-k類似度"
    ${PYTHON} src/11_compute_similarity.py \
        --embedding-dir data/processed/embeddings \
        --output-dir data/processed/similarity \
        --top-k "${TOP_K}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
    log "[STEP 11V] 完了"
    log_separator

    # -----------------------------------------------------------------------
    # 12V: technical_means GapScoreランキング
    # -----------------------------------------------------------------------
    log "[STEP 12V] technical_means GapScoreランキング"
    ${PYTHON} src/12_rank_method_gaps.py \
        --input-dir data/processed \
        --similarity-dir data/processed/similarity \
        --output-dir data/processed/ranking 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
    log "[STEP 12V] 完了"
    log_separator

    # -----------------------------------------------------------------------
    # 13V: ベクトル・ランキング品質レポート
    # -----------------------------------------------------------------------
    log "[STEP 13V] ベクトル・ランキング品質レポート"
    ${PYTHON} src/13_make_vector_ranking_report.py \
        --input-dir data/processed \
        --output-dir data/processed/reports 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
    log "[STEP 13V] 完了"
    log_separator
else
    log "[STEP 10V-13V] 卒論用ベクトル・ランキング系をスキップ（--with-embeddings 指定時のみ実行）"
    log_separator
fi

# ---------------------------------------------------------------------------
# 10: 論文用図表の生成
# ---------------------------------------------------------------------------
log "[STEP 10] 論文用図表の生成"
${PYTHON} src/10_export_for_thesis.py --config "${CONFIG}" 2>&1 | tee -a "${SCRIPT_DIR}/${LOG_FILE}"
log "[STEP 10] 完了"
log_separator

# ---------------------------------------------------------------------------
# 完了メッセージ
# ---------------------------------------------------------------------------
log "=== パイプライン全工程完了 ==="
log ""
log "出力ディレクトリ:"
log "  figures:   outputs/figures/"
log "  tables:    outputs/tables/"
log "  rankings:  outputs/rankings/"
log "  logs:      outputs/logs/"
log ""
log "ログファイル: ${LOG_FILE}"
