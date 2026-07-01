#!/usr/bin/env bash
set -euo pipefail

if command -v latexmk >/dev/null 2>&1; then
  latexmk -lualatex main.tex
elif command -v lualatex >/dev/null 2>&1; then
  lualatex -interaction=nonstopmode main.tex
  lualatex -interaction=nonstopmode main.tex
else
  echo "ERROR: lualatex or latexmk is required for my_bthesis.cls (ltjsreport/luatexja)." >&2
  exit 1
fi
