# -*- coding: utf-8 -*-
"""
Gera os dois crosswalks novos do painel (Fase 11, Bloco 3):
  scripts/modal_por_municipio.json   <- sidra_censo2022/censo2022_matriz_modal_por_municipio.csv
  scripts/grupos_por_municipio.json  <- Cruzamento GE x TZ (ago-2026)/municipio_x_grupo.csv

Chave dos dois: codigo IBGE do municipio (string), que e exatamente a coluna `id`
do MUNI_COL do painel. Escolha deliberada de nao usar "Municipio|UF" (padrao dos
crosswalks antigos): o codigo IBGE nao sofre do problema de grafia que ja obrigou
uma chave duplicada em camadas_tz.json (caso "Embu" x "Embu das Artes").
"""
# Fonte: cofre da tese (fora do git). Rode a partir da raiz do repositorio:
#   python3 scripts/build_modal_e_grupos.py
# Depois, para embutir no painel: python3 scripts/remontar_de_painel.py

import csv, json, collections
from pathlib import Path

VAULT = Path.home() / "mnt" / "doutorado" / "03 - Dados" / "_data"
OUT = Path.home() / "mnt" / "painel TZ" / "scripts"

# ---------------- 1. matriz modal ----------------
# 5 baldes, os mesmos do grafico nacional TZ x nao-TZ ja existente (MODAL_COMPARACAO),
# para o grafico do municipio ser lido na mesma gramatica:
#   onibus = Onibus + BRT | automovel = Automovel | motocicleta = Motocicleta
#   ativo  = A pe + Bicicleta | outros = o resto (mototaxi, taxi, van, trem/metro,
#            embarcacoes, pau de arara, Outros)
BUCKET = {
    "Ônibus": "onibus",
    "BRT ou ônibus de trânsito rápido": "onibus",
    "Automóvel": "automovel",
    "Motocicleta": "motocicleta",
    "A pé": "ativo",
    "Bicicleta": "ativo",
}
src = VAULT / "sidra_censo2022" / "censo2022_matriz_modal_por_municipio.csv"
acc = collections.defaultdict(lambda: collections.defaultdict(float))
bruto = collections.defaultdict(float)
for r in csv.DictReader(open(src, encoding="utf-8")):
    cod = r["codigo_municipio"].strip()
    try:
        v = float(r["percentual"])
    except (TypeError, ValueError):
        continue
    acc[cod][BUCKET.get(r["meio_transporte"].strip(), "outros")] += v
    bruto[cod] += v

modal = {}
baixa_cobertura = 0
for cod, b in acc.items():
    tot = bruto[cod]
    if tot <= 0:
        continue
    # normaliza para 100 (a soma bruta do Censo varia: mediana 98,75%, por
    # arredondamento e celulas suprimidas). `t` guarda a soma bruta para o painel
    # poder sinalizar cobertura baixa em vez de fingir precisao que nao tem.
    row = {k: round(100.0 * b.get(k, 0.0) / tot, 2) for k in
           ("onibus", "automovel", "motocicleta", "ativo", "outros")}
    row["t"] = round(tot, 1)
    if tot < 95:
        baixa_cobertura += 1
    modal[cod] = row

with open(OUT / "modal_por_municipio.json", "w", encoding="utf-8") as f:
    json.dump(modal, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
print(f"modal_por_municipio.json: {len(modal)} municipios "
      f"({baixa_cobertura} com soma bruta < 95%, sinalizados via campo 't')")

# ---------------- 2. grupos economicos por municipio ----------------
# Exposicao minima, decidida pelo autor em 26/08/2026: SO o nome do grupo.
# Nao entram no painel publico: CNPJ, capital social, porte, nem qualquer
# narrativa de caso (cartel, operacao policial, falencia, captura regulatoria)
# — esse material fica no cofre.
#
# O id_grupo (GE-xxx) E carregado, mas por necessidade metodologica, nao como
# exposicao: 20 nomes da base sao HOMONIMOS (sobrenomes usados por grupos
# distintos — "Santos" sao 7 grupos diferentes, "Lima" 3, "Gomes" 3). Contar
# alcance por nome fundiria esses grupos num so e inflaria o alcance deles.
# Entao: a contagem do grafico agregado e por id, e o nome so ganha o sufixo
# do id na tela quando ele for ambiguo. Os 12 maiores grupos nao sao homonimos
# (conferido), logo o topo do grafico nao muda — a correcao pega a cauda.
src2 = VAULT / "Cruzamento GE x TZ (ago-2026)" / "municipio_x_grupo.csv"
linhas = [r for r in csv.DictReader(open(src2, encoding="utf-8"))]

nome_de = {}
munis_de = collections.defaultdict(set)
for r in linhas:
    gid = (r.get("id_grupo") or "").strip()
    nome = (r.get("nome_grupo") or "").strip()
    cod = (r.get("cod_ibge") or "").strip()
    if not (gid and nome and cod):
        continue
    nome_de[gid] = nome
    munis_de[gid].add(cod)

# nomes ambiguos = mesmo nome em 2+ ids
ids_por_nome = collections.defaultdict(set)
for gid, nome in nome_de.items():
    ids_por_nome[nome].add(gid)
ambiguos = {n for n, ids in ids_por_nome.items() if len(ids) > 1}

def rotulo(gid):
    nome = nome_de[gid]
    return f"{nome} ({gid})" if nome in ambiguos else nome

por_muni = collections.defaultdict(list)
for gid, cods in munis_de.items():
    for cod in cods:
        por_muni[cod].append(gid)

# valor por municipio: lista de [rotulo, id] ordenada por alcance desc, depois nome
grupos_out = {}
for cod, gids in por_muni.items():
    gids = sorted(set(gids), key=lambda g: (-len(munis_de[g]), nome_de[g]))
    grupos_out[cod] = [[rotulo(g), g] for g in gids]

with open(OUT / "grupos_por_municipio.json", "w", encoding="utf-8") as f:
    json.dump(grupos_out, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

n_pares = sum(len(v) for v in grupos_out.values())
print(f"grupos_por_municipio.json: {len(grupos_out)} municipios, {n_pares} pares, "
      f"{len(nome_de)} grupos (por id), {len(ids_por_nome)} nomes distintos, "
      f"{len(ambiguos)} nomes ambiguos desambiguados com sufixo do id")
print(f"  municipios com 2+ grupos: {sum(1 for v in grupos_out.values() if len(v) > 1)}")
print("  top 5 por alcance:", [rotulo(g) for g in sorted(munis_de, key=lambda g: -len(munis_de[g]))[:5]])

for p_ in ("modal_por_municipio.json", "grupos_por_municipio.json"):
    print(f"  {p_}: {(OUT / p_).stat().st_size / 1024:.0f} KB")
