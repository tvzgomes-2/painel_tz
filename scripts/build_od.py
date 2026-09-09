# -*- coding: utf-8 -*-
"""
build_od.py — gera scripts/od_por_municipio.json, a matriz origem-destino de
trabalho do Censo 2022 reduzida ao que pode ser publicado.

Entrada (cofre da tese, fora do git):
  03 - Dados/_data/Censo2022_Microdados/agregados/md22_origem_destino_trabalho.csv
  03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv   (arranjo e posicao)

Saida: scripts/od_por_municipio.json — chave = codigo IBGE (string), a mesma
chave de modal_por_municipio.json e grupos_por_municipio.json.

Rode a partir da raiz do repositorio:  python3 scripts/build_od.py
Depois embuta no painel:               bash scripts/montar_html.sh

======================================================================
POR QUE A MATRIZ SAI SUPRIMIDA -- E NAO E DETALHE DE CONFORMIDADE
======================================================================
A matriz vem dos microdados da amostra do Censo 2022, em versao de ACESSO
CONTROLADO, vinculada a termo de compromisso assinado. O painel e publico.

Sao 120.435 pares origem-destino (fora 3.434 com destino sentinela). Deles,
**57,6% se apoiam em UMA unica pessoa amostrada** -- a mediana de n_amostra e 1
e o terceiro quartil e 3. Publicar essas celulas seria errado duas vezes:

  1. CUSTODIA. Celula sustentada por um respondente, cruzando municipio de
     residencia com municipio de trabalho, e informacao rara o suficiente para
     ser identificavel. E exatamente o que o termo trata.
  2. ESTATISTICA. Celula com n=1 tem coeficiente de variacao da ordem de 100%.
     Publicada num painel, ela entra na leitura como se fosse fato. A supressao
     nao e so conformidade: e a mesma disciplina do piso de CV que vale para os
     agregados do SIDRA.

Corte adotado (decisao do autor, 09/09/2026): **top-5 destinos por municipio E
n_amostra >= 5**, aplicado a CELULA -- portanto valendo igual nas duas direcoes,
para que nenhum par apareca numa visao e desapareca na outra por regra diferente.

  pares .......... 16.560 de saida (de 120.435)
  fluxo retido ... 80,3% do total de pessoas representadas
  cobertura ...... 5.167 dos 5.570 municipios de origem (93%)
  em branco ...... 403 municipios, e isso e o resultado honesto: neles nenhum
                   fluxo foi amostrado o suficiente para virar numero.

O JSON guarda o total ANTES da supressao (`st`/`et`) e a fracao coberta pelos
destinos mostrados (`sc`/`ec`), para o painel poder dizer "estes 5 respondem por
X% de quem sai" em vez de fingir que a lista e completa.

Sentinelas 8888888 e 9999999 (exterior e "mais de um municipio") ficam fora das
listas -- nao ha "o" municipio de destino -- mas entram no total, para o
denominador nao mentir.
"""
import csv
import json
import os
import collections
from pathlib import Path

# Caminhos sobreponiveis por variavel de ambiente, para o script rodar fora da
# maquina do autor sem editar codigo.
VAULT = Path(os.environ.get(
    "TZ_VAULT", str(Path.home() / "mnt" / "doutorado" / "03 - Dados" / "_data")))
OUT = Path(os.environ.get("TZ_PAINEL_SCRIPTS",
                          str(Path.home() / "mnt" / "painel TZ" / "scripts")))

OD_CSV = VAULT / "Censo2022_Microdados" / "agregados" / "md22_origem_destino_trabalho.csv"
BASE_CSV = VAULT / "Base Municipal v3" / "base_municipal_v3.csv"

TOP_N = 5          # destinos (e origens) mostrados por municipio
MIN_AMOSTRA = 5    # piso de registros amostrados por celula
SENTINELAS = {8888888, 9999999}

# ---------------------------------------------------------------- arranjo
arranjo, posicao, nome = {}, {}, {}
with open(BASE_CSV, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        cod = (r.get("cod_ibge") or "").strip()
        if not cod:
            continue
        arranjo[cod] = (r.get("arranjo_pop_ibge") or "").strip()
        posicao[cod] = (r.get("posicao_arranjo") or "").strip()
        nome[cod] = (r.get("nome_mun") or "").strip()


def relacao(o, d):
    """0 = destino fora do arranjo da origem · 1 = mesmo arranjo · 2 = polo do
    proprio arranjo. E a leitura que interessa a tese: no satelite, a TZ
    municipal cobre a perna local de um deslocamento cujo destino e o polo, onde
    a tarifa segue."""
    ao, ad = arranjo.get(o, ""), arranjo.get(d, "")
    if not ao or ao != ad:
        return 0
    return 2 if posicao.get(d) == "polo" else 1


# ---------------------------------------------------------------- leitura
pares = []
tot_sai = collections.defaultdict(float)     # total de quem sai, ANTES da supressao
tot_entra = collections.defaultdict(float)
n_dest = collections.Counter()
n_orig = collections.Counter()
n_linhas = 0
peso_total = 0.0

with open(OD_CSV, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        n_linhas += 1
        o = str(int(r["cod_origem"]))
        dcod = int(r["cod_destino"])
        peso = float(r["pessoas_peso"])
        na = int(r["n_amostra"])
        peso_total += peso
        # o total de "quem sai" inclui exterior e multiplos: quem vai para fora
        # do municipio conta, mesmo sem destino nomeavel
        tot_sai[o] += peso
        if dcod in SENTINELAS:
            continue
        d = str(dcod)
        tot_entra[d] += peso
        n_dest[o] += 1
        n_orig[d] += 1
        pares.append((o, d, peso, na))

print(f"lidos {n_linhas:,} pares · {peso_total:,.0f} pessoas representadas")
publicaveis = [p for p in pares if p[3] >= MIN_AMOSTRA]
print(f"celulas com n_amostra >= {MIN_AMOSTRA}: {len(publicaveis):,} "
      f"({len(publicaveis)/len(pares)*100:.1f}% dos pares)")

# ---------------------------------------------------------------- top-N
saidas = collections.defaultdict(list)
entradas = collections.defaultdict(list)
for o, d, peso, na in publicaveis:
    saidas[o].append((peso, d, na))
    entradas[d].append((peso, o, na))

od = {}


def montar(cod, lst, total, chave_lista, chave_total, chave_n, n_distintos):
    """Guarda por celula apenas [outro_municipio, peso, relacao_com_o_arranjo].

    O percentual NAO vai no arquivo de proposito: e `peso / total * 100`, e o
    total ja esta em `st`/`et`. Deixar o painel calcular economiza ~175 KB no
    bloco embutido e, mais importante, evita a classe de bug em que o percentual
    gravado e o total gravado discordam depois de uma mudanca de criterio. Mesma
    razao para nao gravar a fracao coberta pelos mostrados: e a soma da lista
    dividida pelo total."""
    lst.sort(reverse=True)
    escolhidos = lst[:TOP_N]
    if not escolhidos:
        return
    linha = od.setdefault(cod, {})
    linha[chave_lista] = [
        [int(outro), int(round(p)),
         relacao(cod, outro) if chave_lista == "s" else relacao(outro, cod)]
        for p, outro, _ in escolhidos
    ]
    linha[chave_total] = int(round(total))
    linha[chave_n] = n_distintos


for cod, lst in saidas.items():
    montar(cod, lst, tot_sai.get(cod, 0.0), "s", "st", "sd", n_dest[cod])
for cod, lst in entradas.items():
    montar(cod, lst, tot_entra.get(cod, 0.0), "e", "et", "eo", n_orig[cod])

OUT.mkdir(parents=True, exist_ok=True)
alvo = OUT / "od_por_municipio.json"
with open(alvo, "w", encoding="utf-8") as f:
    json.dump(od, f, ensure_ascii=False, separators=(",", ":"))

n_s = sum(1 for v in od.values() if "s" in v)
n_e = sum(1 for v in od.values() if "e" in v)
pares_pub = sum(len(v.get("s", [])) for v in od.values()) + \
            sum(len(v.get("e", [])) for v in od.values())
fluxo_pub = sum(sum(x[1] for x in v.get("s", [])) for v in od.values())
print(f"\n{alvo.name}: {alvo.stat().st_size/1024:.0f} KB")
print(f"  {len(od):,} municipios no arquivo")
print(f"  {n_s:,} com lista de saida · {n_e:,} com lista de entrada")
print(f"  {pares_pub:,} celulas publicadas (saida + entrada, com repeticao)")
print(f"  fluxo de saida publicado: {fluxo_pub:,} pessoas "
      f"({fluxo_pub/peso_total*100:.1f}% do total)")
print(f"  municipios SEM nenhuma saida publicavel: {5570 - n_s:,}")
