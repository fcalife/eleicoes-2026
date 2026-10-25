#!/usr/bin/env bash
# Rerun the TSE pipeline and refresh the site's data (docs/data). Commit and push yourself.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python}"

if [ ! -f data/t1_secoes.json ]; then  # one-time: 1st-round per-section votes (~160 MB zip, ~1 GB csv)
  mkdir -p data/t1csv
  curl -fsSL -o data/t1csv/votacao_secao_2026_BR.zip https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip
  unzip -o -q data/t1csv/votacao_secao_2026_BR.zip -d data/t1csv
  "$PY" -I pipeline/reduce_t1.py data/t1csv/votacao_secao_2026_BR.csv data/t1_secoes.json
fi

"$PY" -I pipeline/test_bu.py
"$PY" -I pipeline/fetch_t2.py data
"$PY" -I pipeline/analyze.py data
mkdir -p docs/data
cp data/dash/*.json docs/data/
echo "docs/data atualizado. Agora: git add docs && git commit && git push"
