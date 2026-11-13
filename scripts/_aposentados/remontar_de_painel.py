# -*- coding: utf-8 -*-
"""
remontar_de_painel.py — remonta painel.html a partir das fontes legíveis
(head.html + logic.js + os crosswalks de scripts/), reaproveitando os blocos de
dados PESADOS que já estão embutidos no painel.html atual (geo.topojson, stats,
base municipal colunar).

Por que existe, se já há montar_html.sh: o montar_html.sh precisa da pasta
../build/ (geo.topojson, stats.json, municipios_dados_col.json), que fica fora do
git e não está presente em toda máquina. Sem ela, toda rodada de ajuste vinha
sendo replicada À MÃO em head.html e painel.html — o CHANGELOG registra essa
ressalva desde 26/07/2026, e ela é a origem de qualquer divergência entre fonte e
publicado. Este script fecha essa brecha: extrai do painel.html os 3 blocos que só
o build gera, e remonta o arquivo com o head/logic/crosswalks atuais.

Uso:  python3 scripts/remontar_de_painel.py
Quando a pasta build/ existir, prefira o montar_html.sh (fluxo canônico).
"""
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
PAINEL = REPO / "painel.html"

BUILD = REPO / "build"

# Ajuste 06/09/2026: quando a pasta build/ existe, os blocos pesados vêm DELA em vez de
# serem herdados do painel.html — é o que permite regerar a base municipal (ex.: colunas
# novas do CadÚnico) sem depender do montar_html.sh, que exige a build inteira.
DO_BUILD = {
    "topo-data": "geo.topojson",
    "data-stats": "stats.json",
    "data-muni": "municipios_dados_col.json",
}

# blocos de dados: (id, arquivo em scripts/ ou None se vem do build/ ou do painel atual)
BLOCOS = [
    ("topo-data", None),                              # geo.topojson (build)
    ("data-stats", None),                             # stats.json (build)
    ("data-muni", None),                              # municipios_dados_col.json (build)
    ("data-fontes", "casos_por_fonte.json"),
    ("data-noticias", "casos_por_noticia.json"),
    ("data-camadas", "camadas_tz.json"),
    ("data-modal", "modal_por_municipio.json"),       # Fase 11 / 11.9
    ("data-grupos", "grupos_por_municipio.json"),     # Fase 11 / 11.10-11.11
    ("data-legislacao", "legislacao_tz.json"),        # item 8.4
]

atual = PAINEL.read_text(encoding="utf-8")

def extrai(bloco_id, texto):
    """Conteúdo de <script id="..."> ... </script>, sem as tags."""
    m = re.search(
        r'<script id="%s"[^>]*>(.*?)</script>' % re.escape(bloco_id),
        texto, re.S)
    return m.group(1).strip("\n") if m else None

herdados = {}
for bid, arq in BLOCOS:
    if arq is None:
        do_build = BUILD / DO_BUILD[bid] if bid in DO_BUILD else None
        if do_build is not None and do_build.exists():
            c = do_build.read_text(encoding="utf-8").strip()
            herdados[bid] = c
            print(f"  do build/: {bid} <- {do_build.name} ({len(c)/1024:.0f} KB)")
            continue
        c = extrai(bid, atual)
        if c is None:
            sys.exit(f"ERRO: bloco '{bid}' não encontrado no painel.html atual — "
                     f"não dá para remontar sem ele. Use montar_html.sh com a pasta build/.")
        herdados[bid] = c
        print(f"  herdado do painel.html: {bid} ({len(c)/1024:.0f} KB)")

head = (SCRIPTS / "head.html").read_text(encoding="utf-8")
logic = (SCRIPTS / "logic.js").read_text(encoding="utf-8")

# head.html termina abrindo <script id="topo-data" ...>
ABRE_TOPO = '<script id="topo-data" type="application/json">'
if not head.rstrip().endswith(ABRE_TOPO):
    sys.exit("ERRO: head.html não termina abrindo o bloco topo-data — estrutura mudou, revisar.")

partes = [head.rstrip()[: -len(ABRE_TOPO)].rstrip("\n")]

for bid, arq in BLOCOS:
    if arq is None:
        conteudo = herdados[bid]
    else:
        p = SCRIPTS / arq
        if not p.exists():
            sys.exit(f"ERRO: {arq} não existe em scripts/ — gerar antes (ver prep dos crosswalks).")
        conteudo = p.read_text(encoding="utf-8").strip()
        json.loads(conteudo)  # falha aqui em vez de gerar um painel quebrado
    partes.append(f'\n<script id="{bid}" type="application/json">\n{conteudo}\n</script>')

partes.append("\n<script>\n" + logic.rstrip("\n") + "\n</script>\n</body>\n</html>\n")
novo = "".join(partes)

# ---- validação antes de gravar ----
for bid, _ in BLOCOS:
    c = extrai(bid, novo)
    if c is None:
        sys.exit(f"ERRO: bloco '{bid}' ausente no arquivo remontado — abortado.")
    try:
        json.loads(c)
    except json.JSONDecodeError as e:
        sys.exit(f"ERRO: bloco '{bid}' não é JSON válido no remontado ({e}) — abortado.")

for marca in ('<div id="grupos">', '<div id="regiaoUf">', 'id="dispersao"',
              'id="muniSearch"', 'id="clearAll"', "</body>", "</html>"):
    if marca not in novo:
        sys.exit(f"ERRO: marca esperada ausente no remontado: {marca} — abortado.")

bak = PAINEL.with_suffix(".html.bak")
shutil.copy2(PAINEL, bak)
PAINEL.write_text(novo, encoding="utf-8")
print(f"\npainel.html remontado: {len(novo)/1024/1024:.2f} MB "
      f"(antes {len(atual)/1024/1024:.2f} MB) — backup em {bak.name}")
