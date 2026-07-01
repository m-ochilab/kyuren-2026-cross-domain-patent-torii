#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

echo "== Smoke test: repository =="
echo "root: ${ROOT_DIR}"
echo "python: $(${PYTHON} --version)"

echo
echo "== Python syntax check =="
cd "${ROOT_DIR}"
PY_FILES="$(find pipeline/src pipeline/scripts scripts legacy_tools thesis/figures -name '*.py' -type f 2>/dev/null | sort)"
if [ -n "${PY_FILES}" ]; then
  echo "${PY_FILES}" | xargs "${PYTHON}" -m py_compile
else
  echo "No Python files found for syntax check"
fi

echo
echo "== Pipeline sample run =="
cd "${ROOT_DIR}/pipeline"
SAMPLE_N="${SAMPLE_N:-20}" bash run_all.sh

echo
echo "== Thesis LaTeX build =="
cd "${ROOT_DIR}/thesis"
if command -v tectonic >/dev/null 2>&1; then
  tectonic main.tex
else
  echo "tectonic not found; skipping thesis PDF build"
fi

echo
echo "== Research plan LaTeX availability check =="
cd "${ROOT_DIR}/research_plan_latex"
if command -v lualatex >/dev/null 2>&1; then
  lualatex -interaction=nonstopmode main.tex
else
  echo "lualatex not found; research_plan_latex uses ltjsreport/luatexja and needs a LuaLaTeX-capable TeX Live environment"
fi

echo
echo "Smoke test completed."
