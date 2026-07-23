#!/usr/bin/env bash
# montar_html.sh — remonta index.html a partir de head.html + dados + logic.js.
#
# index.html não é editado diretamente (tem ~4 MB de JSON embutido). O fluxo é:
#   1. editar head.html (estrutura/CSS/controles) e/ou logic.js (lógica) aqui em scripts/
#   2. rodar build_data.py e build_stats.py (gera ../build/municipios_dados.json e stats.json)
#   3. rodar este script para colar tudo de volta em ../index.html
#
# Pré-requisito: ../build/municipios.topojson (geometria simplificada — ver
# preparar_geometria.sh) e ../build/municipios_dados_col.json (versão colunar
# de municipios_dados.json, mais compacta — gerar com:
#   python3 -c "import json; d=json.load(open('../build/municipios_dados.json'));
#   cols=list(d[0].keys()); json.dump({'cols':cols,'data':[[r[c] for c in cols] for r in d]},
#   open('../build/municipios_dados_col.json','w'), ensure_ascii=False)"

set -e
cd "$(dirname "$0")"
BUILD=../build
OUT=../index.html

{
  cat head.html
  cat "$BUILD/municipios.topojson"
  printf '</script>\n<script id="data-stats" type="application/json">\n'
  cat "$BUILD/stats.json"
  printf '</script>\n<script id="data-muni" type="application/json">\n'
  cat "$BUILD/municipios_dados_col.json"
  printf '</script>\n<script>\n'
  cat logic.js
  printf '</script>\n</body>\n</html>\n'
} > "$OUT"

echo "gerado: $OUT ($(wc -c < "$OUT") bytes)"
