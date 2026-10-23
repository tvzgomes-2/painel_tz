# -*- coding: utf-8 -*-
"""
build_camadas.py — gera scripts/camadas_tz.json a partir da aba "2 Parcial" de
`Tipologias TZ - consolidado.xlsx` (cofre), que é o arquivo canônico da régua.

Por que existe: até out/2026 o camadas_tz.json era montado de CSVs soltos e de uma
nota do cofre, na numeração ANTERIOR das camadas. A régua foi renumerada em
13/09/2026 e propagada à planilha em 20/09, e os rótulos passaram a significar
coisas diferentes — o painel dizia "2a = Temporal (dias)" enquanto a régua atual
chama 2a de grupo social e temporal-dias de 2c. Ou seja: os mesmos códigos,
sentidos trocados. Este script passa a ler a planilha da régua direto.

Numeração vigente (Regras de classificacao das reguas, cofre):
  2a  grupo social (residual)          2b  espacial / periférico
  2c  temporal, dias da semana         2d  temporal, eventos
  2e  finalidade (escola, tratamento, prova — passe livre estudantil)
A aba eleitoral fica FORA por decisão do autor (07/10/2026): não conta em camada.

Uso:  python3 scripts/build_camadas.py        (da raiz do repositório)
"""
import json
import os
import re
import unicodedata
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
DADOS = os.path.join(VAULT, '03 - Dados', '_data')
OUT = os.path.join(BASE_DIR, 'camadas_tz.json')

# o congelamento mais recente é a fonte preferida (tem manifesto sha256);
# cai para a cópia viva se não houver congelamento.
cands = sorted(
    (d for d in os.listdir(DADOS) if d.startswith('congelamento-')),
    reverse=True)
TIP = None
for d in cands:
    p = os.path.join(DADOS, d, 'Tipologias TZ - consolidado.xlsx')
    if os.path.exists(p):
        TIP = p
        print(f"fonte: {d}/Tipologias TZ - consolidado.xlsx")
        break
if TIP is None:
    raise SystemExit("ERRO: Tipologias TZ - consolidado.xlsx não encontrado em nenhum congelamento.")

LABELS = {
    '2a': 'Grupo social',
    '2b': 'Espacial (periférica)',
    '2c': 'Temporal (dias)',
    '2d': 'Temporal (eventos)',
    '2e': 'Finalidade (estudo, saúde)',
}

# ---- resolução da chave: código IBGE, não "Município|UF" ----
# Até 23/10/2026 o arquivo era chaveado por "Município|UF" e o painel reconciliava
# com normKey() (acento e caixa). Isso escondia um caso: a planilha da régua grafa
# "Embu das Artes" (nome oficial desde 2011) e a base do painel grafa "Embu"
# (3515004). Normalizar acento não resolve nomes diferentes — a entrada 2c do
# município ficou órfã, invisível no mapa, no card e na barra da régua, de v0.11
# até aqui. Agora a chave é o código IBGE, como já fazem modal_por_municipio.json,
# grupos_por_municipio.json e legislacao_tz.json, e quem não resolve GRITA.
BASE_JSON = os.path.join(BASE_DIR, '..', 'build', 'municipios_dados.json')

# Nomes que a planilha da régua e a base do painel grafam de formas diferentes.
# Chave: nome normalizado|UF como aparece na PLANILHA. Valor: código IBGE.
ALIAS = {
    'EMBU DAS ARTES|SP': 3515004,   # base do painel ainda usa o nome antigo, "Embu"
}

def chave_nome(nome, uf):
    s = unicodedata.normalize('NFD', str(nome))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r"[^A-Za-z0-9 ]", ' ', s)
    s = re.sub(r'\s+', ' ', s).strip().upper()
    return f"{s}|{str(uf).strip().upper()}"

if not os.path.exists(BASE_JSON):
    raise SystemExit(
        "ERRO: ../build/municipios_dados.json não encontrado. Rode build_data.py antes:\n"
        "      a chave do camadas_tz.json agora é o código IBGE, resolvido contra a base.")
with open(BASE_JSON, encoding='utf-8') as f:
    _base = json.load(f)
NOME2COD = {}
COD2NOME = {}
for _r in _base:
    _cod = int(_r['id'])
    COD2NOME[_cod] = f"{_r['nome']}/{_r['uf']}"
    NOME2COD[chave_nome(_r['nome'], _r['uf'])] = _cod

nao_resolvidos = []

def resolver_cod(nome, uf, cod_planilha=None):
    """Devolve o código IBGE do município, ou None (registrando o caso)."""
    if cod_planilha is not None:
        try:
            c = int(float(cod_planilha))
            if c in COD2NOME:
                return c
        except (TypeError, ValueError):
            pass
    k = chave_nome(nome, uf)
    if k in NOME2COD:
        return NOME2COD[k]
    if k in ALIAS and ALIAS[k] in COD2NOME:
        return ALIAS[k]
    nao_resolvidos.append(f"{nome}/{uf}")
    return None


def txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = re.sub(r'\s+', ' ', str(v)).strip()
    return s or None

def trecho(valor, sub):
    """Campos da planilha usam '[2b] ... ‖ [2c] ...' quando o município tem vários
    subtipos. Devolve só o pedaço do subtipo pedido, ou o campo inteiro se não
    houver marcação."""
    s = txt(valor)
    if not s:
        return None
    if '[' not in s:
        return s
    for parte in s.split('‖'):
        m = re.match(r'\s*\[([0-9a-z+ ]+)\]\s*(.*)', parte.strip())
        if m and sub in [x.strip() for x in m.group(1).split('+')]:
            return txt(m.group(2))
    return None

df = pd.read_excel(TIP, sheet_name='2 Parcial')
cam = {}
n_linhas = 0
provisorios = 0

for _, r in df.iterrows():
    mun, uf = txt(r.get('Município')), txt(r.get('UF'))
    subs = txt(r.get('Subtipo'))
    if not (mun and uf and subs):
        continue
    cod = resolver_cod(mun, uf, r.get('Código IBGE'))
    if cod is None:
        continue
    chave = str(cod)
    for sub in [s.strip() for s in subs.split('+')]:
        if sub not in LABELS:
            print(f"  [aviso] subtipo fora da régua, ignorado: {sub!r} ({chave})")
            continue
        detalhe = ' · '.join(filter(None, [
            trecho(r.get('Programa'), sub),
            trecho(r.get('Grupo'), sub),
            trecho(r.get('Escopo'), sub),
            trecho(r.get('Dias'), sub),
        ]))
        flag = None
        for campo in ('Escopo', 'Programa', 'Situação/Status'):
            v = trecho(r.get(campo), sub) or ''
            if 'PROVIS' in v.upper():
                flag = 'classificação provisória, a confirmar'
                provisorios += 1
                break
        entrada = {'camada': sub}
        if detalhe:
            entrada['detalhe'] = detalhe[:400]
        if flag:
            entrada['flag'] = flag
        cam.setdefault(chave, []).append(entrada)
        n_linhas += 1

# ---- complemento a partir da base-mestre ----
# Os dois arquivos canônicos do cofre divergem em alguns casos: a base-mestre
# classifica o município como "2 Parcial" nas colunas de régua, mas ele não aparece
# na aba "2 Parcial" da planilha da régua (em 22/10/2026: Guapimirim/RJ, que a
# planilha da régua lista em "1 Universal" sem subtipo, enquanto a base-mestre diz
# 2b e o log da linha diz "em verificação"). Sem complemento o município ficaria
# marcado como parcial no painel e sem camada nenhuma — parcial de quê, não se sabe.
# Entra com o subtipo da base-mestre e flag de divergência; não se resolve aqui.
MESTRE = os.path.join(DADOS, 'casos por fonte', 'Municípios TZ - consolidado.xlsx')
complementados = []
if os.path.exists(MESTRE):
    mt = pd.read_excel(MESTRE, sheet_name='consolidado')
    for _, r in mt.iterrows():
        aba, sub = txt(r.get('Régua — aba')), txt(r.get('Régua — subtipo'))
        mun, uf = txt(r.get('Município')), txt(r.get('UF'))
        if not (mun and uf and aba == '2 Parcial' and sub in LABELS):
            continue
        cod = resolver_cod(mun, uf, r.get('Código IBGE') or r.get('cod_ibge'))
        if cod is None:
            continue
        chave = str(cod)
        if chave in cam:
            continue
        cam[chave] = [{'camada': sub,
                       'detalhe': txt(r.get('Status no log')) or None,
                       'flag': 'divergência entre base-mestre e planilha da régua — a confirmar'}]
        cam[chave] = [{k: v for k, v in e.items() if v} for e in cam[chave]]
        complementados.append(f"{chave} ({sub})")
if complementados:
    print("  complementados da base-mestre (ausentes da planilha da régua):")
    for c in complementados:
        print("   ", c)

cam = {k: cam[k] for k in sorted(cam, key=int)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(cam, f, ensure_ascii=False, indent=2)
    f.write('\n')

from collections import Counter
c = Counter(e['camada'] for v in cam.values() for e in v)
n_entradas = sum(len(v) for v in cam.values())
print(f"camadas_tz.json: {len(cam)} municípios, {n_entradas} entradas de camada")
for k in sorted(LABELS):
    print(f"   {k} {LABELS[k]:28} {c.get(k, 0)}")
print(f"   com flag de provisório: {provisorios}")
print(f"   municípios com 2+ camadas: {sum(1 for v in cam.values() if len(v) > 1)}")
if nao_resolvidos:
    print("  [ERRO] municípios que não casaram com a base do painel "
          "(entrariam como chave órfã e sumiriam da tela):")
    for n in sorted(set(nao_resolvidos)):
        print("   ", n)
    raise SystemExit("camadas_tz.json NÃO foi considerado válido: resolva os nomes acima "
                     "(acrescente ao ALIAS ou corrija a planilha) e rode de novo.")
print("   todos os municípios resolvidos por código IBGE")
