#!/usr/bin/env bash
# montar_html.sh — remonta painel.html (página "Painel Brasil") a partir de head.html + dados + logic.js.
#
# painel.html não é editado diretamente (tem ~4 MB de JSON embutido). O fluxo é:
#   1. editar head.html (estrutura/CSS/controles) e/ou logic.js (lógica) aqui em scripts/
#   2. rodar build_data.py e build_stats.py (gera ../build/municipios_dados.json e stats.json)
#   3. rodar este script para colar tudo de volta em ../painel.html
#
# CORRECAO 06/09/2026: este script estava sem os blocos data-modal, data-grupos e
# data-legislacao, que o painel.html publicado usa desde as Fases 11/8.4 — rodá-lo como
# estava produziria um painel quebrado (sem modal split, sem grupos econômicos, sem
# legislação). Corrigido abaixo. O remontar_de_painel.py continua sendo o caminho usual.
#
# painel.html é uma das páginas do site (hub em ../index.html). Não confundir os dois.
#
# Pré-requisito: ../build/geo.topojson (geometria simplificada com camadas de
# municípios + UFs — ver preparar_geometria.sh) e ../build/municipios_dados_col.json (versão colunar
# de municipios_dados.json, mais compacta — gerar com:
#   python3 -c "import json; d=json.load(open('../build/municipios_dados.json'));
#   cols=list(d[0].keys()); json.dump({'cols':cols,'data':[[r[c] for c in cols] for r in d]},
#   open('../build/municipios_dados_col.json','w'), ensure_ascii=False)"
# Também requer scripts/casos_por_fonte.json (crosswalk estudo/fonte → município, Fase 8 —
# ver build_crosswalk.py e ROADMAP.md §3), scripts/casos_por_noticia.json (crosswalk notícia de
# imprensa → município, gerado a partir de 03 - Dados/_data/casos por fonte/reportagens_por_municipio.csv
# no cofre — ver Consolidação de referências, 27/07/2026) e scripts/camadas_tz.json (crosswalk
# camada 2a/3/4 da régua descritiva → município, gerado a partir de 03 - Dados/_data/Base Municipal v3/
# camada2a_temporal_dias_analise.csv + 03 - Dados/_data/casos por fonte/tz_bairros_perifericos.csv +
# nota "Tipologias de Tarifa Zero (4 camadas)" do cofre — 29/07/2026, exclui de propósito a camada
# 2b/eleitoral, ver ROADMAP.md).

set -e
cd "$(dirname "$0")"
BUILD=../build
OUT=../painel.html

{
  cat head.html
  cat "$BUILD/geo.topojson"
  printf '</script>\n<script id="data-stats" type="application/json">\n'
  cat "$BUILD/stats.json"
  printf '</script>\n<script id="data-muni" type="application/json">\n'
  cat "$BUILD/municipios_dados_col.json"
  printf '</script>\n<script id="data-fontes" type="application/json">\n'
  cat casos_por_fonte.json
  printf '</script>\n<script id="data-noticias" type="application/json">\n'
  cat casos_por_noticia.json
  printf '</script>\n<script id="data-camadas" type="application/json">\n'
  cat camadas_tz.json
  printf '</script>\n<script id="data-modal" type="application/json">\n'
  cat modal_por_municipio.json
  printf '</script>\n<script id="data-grupos" type="application/json">\n'
  cat grupos_por_municipio.json
  printf '</script>\n<script id="data-legislacao" type="application/json">\n'
  cat legislacao_tz.json
  printf '</script>\n<script>\n'
  cat logic.js
  printf '</script>\n</body>\n</html>\n'
} > "$OUT"

echo "gerado: $OUT ($(wc -c < "$OUT") bytes)"
