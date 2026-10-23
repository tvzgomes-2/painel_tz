# -*- coding: utf-8 -*-
"""
build_rede_ge.py — gera scripts/rede_ge.json, a base da página "Rede de empresas".

Fonte: ARS do cofre (`03 - Dados/_data/CNPJ/ARS - métricas de rede (out-2026)/`)
e a rede de sócios (`CNPJ/ARS - Sócios/rede_socios.csv`).

⚠️ FRONTEIRA DE EXPOSIÇÃO (decisão do autor, 22/10/2026): a saída contém APENAS
empresa e grupo. A rede de sócios é lida aqui só para CALCULAR as ligações entre
grupos (dois grupos ficam ligados quando compartilham sócio) — nenhum nome de
pessoa física, CPF ou aresta pessoa-a-pessoa entra no JSON publicado. O arquivo
de origem tem ~11.590 pessoas nomeadas com CPF parcial; nada disso sai daqui.

Duas espécies de ligação, exibidas de forma distinta na página:
  - socio   : os dois grupos têm sócio em comum (peso = nº de sócios compartilhados)
  - fusao   : os dois grupos caem no MESMO cluster da ARS, ou seja a análise
              societária os trata como um bloco de controle só — achado mais forte
              que o anterior, e é o que responde à pergunta sobre Barata/Comporte.

Layout: calculado AQUI (Fruchterman-Reingold), não no navegador — ROADMAP 9.4.
O rascunho de julho recalculava o layout a cada carregamento, e era a causa dos
"alguns segundos" de espera.

Uso:  python3 scripts/build_rede_ge.py       (da raiz do repositório)
"""
import collections
import csv
import json
import math
import os
import random

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
ARS = os.path.join(VAULT, '03 - Dados', '_data', 'CNPJ', 'ARS - métricas de rede (out-2026)')
SOCIOS = os.path.join(VAULT, '03 - Dados', '_data', 'CNPJ', 'ARS - Sócios', 'rede_socios.csv')
OUT = os.path.join(BASE_DIR, 'rede_ge.json')
# Tabela mestre v5 (17/10/2026), a mesma do Capítulo 6 e do pacote 4 da tese: dela vêm a
# presença municipal (endereço dos estabelecimentos) e o "topo do capital".
V5 = os.path.join(VAULT, '01 - Projeto', 'Envio à orientadora — 24-11-2026', '02 Bases de dados (xlsx)',
                  '04 Grupos econômicos (Tabela mestre v5, 17-10-2026).xlsx')
BASE_JSON = os.path.join(BASE_DIR, '..', 'build', 'municipios_dados.json')

# ---------------- 1. nós: os 327 grupos ----------------
gr = pd.read_csv(os.path.join(ARS, 'ars_metricas_grupos.csv'))
emp = pd.read_csv(os.path.join(ARS, 'ars_metricas_empresas.csv'), dtype={'cnpj_basico': str})

def num(v, casas=None):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return round(f, casas) if casas is not None else (int(f) if f.is_integer() else f)

def txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None

nos = {}
for _, r in gr.iterrows():
    gid = txt(r['id_grupo'])
    if not gid:
        continue
    nos[gid] = {
        'id': gid,
        'nome': txt(r.get('nome_grupo')) or gid,
        'mercado': txt(r.get('nome_mercado_confirmado')),
        'capital': num(r.get('capital_social_total_reais'), 0),
        'n_emp': num(r.get('n_empresas')) or 0,
        'n_soc': num(r.get('n_socios')) or 0,
        'ponte': num(r.get('socios_ponte')),
        'artic': num(r.get('socios_articulacao')),
        'dens': num(r.get('densidade'), 3),
        'diam': num(r.get('diametro')),
        'central': txt(r.get('empresa_central')),
    }

# ---------------- 1b. o que vem da Tabela mestre v5 ----------------
# 23/10/2026 — EXPOSIÇÃO: por decisão do autor, o nome de mercado e o capital social de
# cada grupo FICAM na página (uma versão intermediária, do mesmo dia, os tinha retirado, e
# o autor mandou reverter). Continua valendo: nenhuma lista de sócios, nenhum CPF, nenhum
# CNPJ, nenhuma evidência de ligação que nomeie pessoa. Além do capital, a marca de
# pertencer aos 26 grupos que, juntos, detêm metade do capital (o "grande grupo" da tese).
v5g = pd.read_excel(V5, sheet_name='Resumo por grupo')
v5g = v5g[v5g['id_grupo'].astype(str).str.startswith('GE')].copy()
v5g = v5g.sort_values('capital_social_total_reais', ascending=False)
v5g['acum'] = v5g['capital_social_total_reais'].cumsum() / v5g['capital_social_total_reais'].sum()
n_topo = int((v5g['acum'] < 0.5).sum()) + 1
TOPO = set(v5g['id_grupo'].head(n_topo))
print(f"topo do capital: {n_topo} grupos detêm metade do capital declarado")

import unicodedata, re as _re
def chave(n, uf):
    s2 = unicodedata.normalize('NFD', str(n)); s2 = ''.join(c for c in s2 if unicodedata.category(c) != 'Mn')
    return _re.sub(r'\s+', ' ', _re.sub(r"[^A-Za-z0-9 ]", ' ', s2)).strip().upper() + '|' + str(uf).strip().upper()
base = json.load(open(BASE_JSON, encoding='utf-8'))
NOME2COD = {chave(r['nome'], r['uf']): str(r['id']) for r in base}
POP = {str(r['id']): (r.get('pop') or 0) for r in base}
NOME = {str(r['id']): f"{r['nome']}/{r['uf']}" for r in base}
# grafias que a Tabela mestre (nome oficial atual) e a base do painel escrevem diferente
ALIAS = {'EMBU DAS ARTES|SP': '3515004', 'MOGI MIRIM|SP': '3530805',
         'SANTA IZABEL DO PARA|PA': '1506500', 'POXOREU|MT': '5107008'}
v5e = pd.read_excel(V5, sheet_name='Empresas', usecols=['id_grupo', 'municipios_atuacao'])
presenca = collections.defaultdict(set)     # cod_ibge -> {GE}
sem_cod = collections.Counter()
for _, r in v5e.iterrows():
    gid, ms = txt(r.get('id_grupo')), txt(r.get('municipios_atuacao'))
    if not (gid and ms and gid in nos):
        continue
    for item in ms.split(';'):
        item = _re.sub(r'\s*\(.*?\)\s*$', '', item.strip())   # anotações de trabalho entre parênteses
        if '/' not in item:
            continue
        nm, uf = item.rsplit('/', 1)
        c = NOME2COD.get(chave(nm, uf)) or ALIAS.get(chave(nm, uf))
        if c: presenca[c].add(gid)
        else: sem_cod[item] += 1
mun_do_grupo = collections.defaultdict(set)
for c, gs in presenca.items():
    for g in gs: mun_do_grupo[g].add(c)
print(f"presença: {len(presenca)} municípios com estabelecimento de algum dos grupos "
      f"({sum(POP.get(c, 0) for c in presenca)/1e6:.1f} mi de habitantes); nomes sem código IBGE: {len(sem_cod)}")
if sem_cod: print("   ", sem_cod.most_common(8))

# homônimos (ROADMAP 11.15): sobrenomes usados por grupos distintos ganham o código no rótulo
cont_nome = collections.Counter(v['nome'] for v in nos.values())
for gid, v in nos.items():
    v['rot'] = f"{v['nome']} ({gid})" if cont_nome[v['nome']] > 1 else v['nome']
    v['topo'] = gid in TOPO
    v['n_mun'] = len(mun_do_grupo.get(gid, ()))
print(f"homônimos: {sum(1 for n in cont_nome.values() if n > 1)} nomes usados por mais de um grupo")

# ---------------- 2. arestas ----------------
cnpj2grupo = {}
cluster_de = {}
for _, r in emp.iterrows():
    gid, cnpj = txt(r.get('id_grupo')), txt(r.get('cnpj_basico'))
    if gid and cnpj:
        cnpj2grupo[cnpj.zfill(8)] = gid
    if gid and txt(r.get('cluster_id')):
        cluster_de.setdefault(txt(r['cluster_id']), set()).add(gid)

# 2a. sócio compartilhado — a rede de pessoas entra SÓ aqui, como insumo
socio2grupos = collections.defaultdict(set)
with open(SOCIOS, encoding='utf-8', errors='replace') as f:
    for row in csv.DictReader(f, delimiter=';'):
        src, tgt = row.get('Source', ''), row.get('Target', '')
        for lado, outro in ((src, tgt), (tgt, src)):
            if '_' not in lado:
                continue
            suf = lado.rsplit('_', 1)[1]
            if len(suf) == 14 and suf.isdigit():
                g = cnpj2grupo.get(suf[:8])
                if g:
                    socio2grupos[outro].add(g)

peso = collections.Counter()
for gs in socio2grupos.values():
    gs = sorted(gs)
    for a in range(len(gs)):
        for b in range(a + 1, len(gs)):
            peso[(gs[a], gs[b])] += 1

# 2b. fusão: mesmo cluster na ARS
fusao = set()
for gids in cluster_de.values():
    gids = sorted(g for g in gids if g in nos)
    for a in range(len(gids)):
        for b in range(a + 1, len(gids)):
            fusao.add((gids[a], gids[b]))

arestas = []
for (a, b), w in peso.items():
    if a in nos and b in nos:
        arestas.append({'a': a, 'b': b, 'w': w, 't': 'fusao' if (a, b) in fusao else 'socio'})
for (a, b) in fusao:
    if not any(e['a'] == a and e['b'] == b for e in arestas):
        arestas.append({'a': a, 'b': b, 'w': 1, 't': 'fusao'})

conectados = {g for e in arestas for g in (e['a'], e['b'])}
print(f"nós: {len(nos)} grupos | arestas: {len(arestas)} "
      f"({sum(1 for e in arestas if e['t']=='fusao')} de fusão, "
      f"{sum(1 for e in arestas if e['t']=='socio')} de sócio compartilhado)")
print(f"grupos com alguma ligação: {len(conectados)} | isolados: {len(nos)-len(conectados)}")

# ---------------- 3. layout, calculado aqui ----------------
# 23/10/2026: o layout de 22/10 rodava um Fruchterman-Reingold único sobre os 92 grupos
# ligados, que formam vários componentes desconexos; os componentes se afastavam até as
# bordas e o mapa ficava com aglomerados minúsculos num vazio. Agora cada componente é
# desenhado à parte e os componentes são empacotados em prateleiras, do maior ao menor —
# o procedimento padrão para redes desconexas.
random.seed(42)
adj = collections.defaultdict(list)
for e in arestas:
    adj[e['a']].append((e['b'], e['w']))
    adj[e['b']].append((e['a'], e['w']))

def componentes(nodes):
    vistos, comps = set(), []
    for g in sorted(nodes):
        if g in vistos: continue
        pilha, comp = [g], []
        vistos.add(g)
        while pilha:
            x = pilha.pop(); comp.append(x)
            for y, _ in adj[x]:
                if y not in vistos: vistos.add(y); pilha.append(y)
        comps.append(sorted(comp))
    return sorted(comps, key=len, reverse=True)

def fr(comp, iters=400):
    if len(comp) == 1: return {comp[0]: (0.0, 0.0)}
    if len(comp) == 2: return {comp[0]: (-0.5, 0.0), comp[1]: (0.5, 0.0)}
    pos = {g: [random.uniform(-1, 1), random.uniform(-1, 1)] for g in comp}
    k = math.sqrt(4.0 / len(comp)); temp = 0.2
    for _ in range(iters):
        d = {g: [0.0, 0.0] for g in comp}
        for a in range(len(comp)):
            for b in range(a + 1, len(comp)):
                g, h = comp[a], comp[b]
                dx, dy = pos[g][0] - pos[h][0], pos[g][1] - pos[h][1]
                d2 = dx * dx + dy * dy or 1e-6
                f = k * k / d2
                d[g][0] += dx * f; d[g][1] += dy * f; d[h][0] -= dx * f; d[h][1] -= dy * f
        for g in comp:
            for h, w in adj[g]:
                dx, dy = pos[g][0] - pos[h][0], pos[g][1] - pos[h][1]
                dist = math.hypot(dx, dy) or 1e-6
                f = dist * dist / k * (1 + 0.25 * math.log1p(w))
                d[g][0] -= dx / dist * f * 0.5; d[g][1] -= dy / dist * f * 0.5
        for g in comp:
            dx, dy = d[g]; dist = math.hypot(dx, dy) or 1e-6
            pos[g][0] += dx / dist * min(dist, temp); pos[g][1] += dy / dist * min(dist, temp)
        temp = max(temp * 0.985, 0.003)
    return {g: tuple(v) for g, v in pos.items()}

comps = componentes(conectados)
W, H, M = 1000, 640, 14
# lado de cada caixa proporcional à raiz do tamanho do componente
caixas = []
for comp in comps:
    lay = fr(comp)
    xs = [p[0] for p in lay.values()]; ys = [p[1] for p in lay.values()]
    lado = 46 + 70 * math.sqrt(len(comp))
    caixas.append((comp, lay, min(xs), max(xs), min(ys), max(ys), lado))
# empacotamento em prateleiras, com escala única para caber no quadro
def empacota(escala):
    x = y = alt = 0; pos = []
    for comp, lay, x0, x1, y0, y1, lado in caixas:
        l = lado * escala
        if x + l > W - 2 * M: x, y, alt = 0, y + alt, 0
        pos.append((x, y, l)); x += l; alt = max(alt, l)
    return pos, y + alt
escala = 1.0
while True:
    arranjo, altura = empacota(escala)
    if altura <= H - 2 * M or escala < 0.2: break
    escala *= 0.95
for (comp, lay, x0, x1, y0, y1, lado), (bx, by, l) in zip(caixas, arranjo):
    sx, sy = (x1 - x0) or 1, (y1 - y0) or 1
    pad = l * 0.14
    for g in comp:
        px, py = lay[g]
        nos[g]['x'] = round(M + bx + pad + (px - x0) / sx * (l - 2 * pad) if len(comp) > 1 else M + bx + l / 2, 1)
        nos[g]['y'] = round(M + by + pad + (py - y0) / sy * (l - 2 * pad) if len(comp) > 1 else M + by + l / 2, 1)
print(f"layout: {len(comps)} componentes, o maior com {len(comps[0]) if comps else 0} grupos; escala {escala:.2f}")

# ---------------- 4. agrupamentos: unidade de controle, família, linhagem, federação ----------------
# Seções 6.1 a 6.3 da tese. A escala de confiança gradua cada ligação entre grupos: A
# (controle comum demonstrado) e B (provável) FUNDEM grupos em unidades de controle —
# 316 unidades, a unidade principal do Capítulo 6; C (linhagem) e D (federação, mera
# articulação) são ATRIBUTOS, não fundem nada. Nenhuma evidência que nomeie pessoa sai daqui.
ub = pd.read_excel(V5, sheet_name='Unidades B')
unidades, ge2ub = [], {}
for _, r in ub.iterrows():
    uid = txt(r.get('unidade_B'))
    membros = [m.strip() for m in str(r.get('membros (GE)') or '').split(';') if m.strip().startswith('GE')]
    if not uid: continue
    for m in membros: ge2ub[m] = uid
    unidades.append({'id': uid, 'nome': txt(r.get('unidade_B_nome')), 'membros': membros,
        'grau': (txt(r.get('grau_fusao')) if txt(r.get('grau_fusao')) not in (None, '—') else None),
        'n_emp': num(r.get('n_empresas')), 'capital': num(r.get('capital_social_total_reais'), 0),
        'pct': num(r.get('pct_capital'), 2), 'acum': num(r.get('pct_acumulado'), 2),
        'n_mun': num(r.get('n_municipios_6cnaes')), 'n_mun_onibus': num(r.get('n_municipios_4921301')),
        'fc': txt(r.get('familia_controle')), 'lin': txt(r.get('linhagem')), 'fed': txt(r.get('federacao'))})
for gid, v in nos.items():
    v['ub'] = ge2ub.get(gid)
n_topo_ub = next(i + 1 for i, u in enumerate(unidades) if (u['acum'] or 0) >= 50)
print(f"unidades de controle: {len(unidades)} | com mais de um grupo: {sum(1 for u in unidades if len(u['membros']) > 1)} | topo: {n_topo_ub} unidades com metade do capital")

CAND = os.path.join(VAULT, '03 - Dados', 'Grupos econômicos — candidatos a família e federação (17-10-2026, v4).xlsx')
lin = pd.read_excel(CAND, sheet_name='Linhagens')
linhagens = [{'id': txt(r['LIN']), 'nome': txt(r['Nome']), 'tipo': txt(r['Tipo']), 'status': txt(r['Status']),
              'membros': [m.strip() for m in str(r['Membros (GE)']).split(';') if m.strip().startswith('GE')],
              'capital': round((num(r['Capital somado (R$ mi)']) or 0) * 1e6), 'n_emp': num(r['Nº de empresas'])}
             for _, r in lin.iterrows() if txt(r.get('LIN')) and str(r['LIN']).startswith('LIN')]
fcs = pd.read_excel(CAND, sheet_name='Famílias de controle')
familias = [{'id': txt(r['FC']), 'nome': txt(r['Nome']), 'grau': txt(r['Grau (v4)']),
             'membros': [m.strip() for m in str(r['Ramos (GE)']).split(';') if m.strip().startswith('GE')],
             'capital': round((num(r['Capital somado (R$ mi)']) or 0) * 1e6), 'n_emp': num(r['Nº de empresas'])}
            for _, r in fcs.iterrows() if txt(r.get('FC')) and str(r['FC']).startswith('FC')]
escala = [{'grau': txt(r['Grau']), 'nome': txt(r['Nome']), 'regra': txt(r['Regra operacional'])}
          for _, r in pd.read_excel(CAND, sheet_name='Escala').iterrows() if txt(r['Grau']) in ('A', 'B', 'C', 'D', 'E')]
for e in escala:   # a regra pode citar exemplo com nome de pessoa? confere e corta no primeiro exemplo
    e['regra'] = _re.split(r'\s*\((?:ex\.|exemplo)', e['regra'] or '')[0]
federacoes = collections.defaultdict(list)
for u in unidades:
    if u['fed']: federacoes[u['fed']].append(u['id'])
fed_out = []
for fid, us in sorted(federacoes.items()):
    us_sorted = sorted(us, key=lambda x: next(u['capital'] or 0 for u in unidades if u['id'] == x), reverse=True)
    cap = sum(next(u['capital'] or 0 for u in unidades if u['id'] == x) for x in us)
    fed_out.append({'id': fid, 'unidades': us_sorted, 'capital': round(cap)})
fed_out.sort(key=lambda f: f['capital'], reverse=True)

# o funil da Tabela 5: concentração em cada leitura da escala, calculada aqui e conferida com a tese
def leitura(blocos):
    # Gini sobre todas as unidades (inclusive as de capital zero), como na Tabela 5
    caps = sorted(blocos, reverse=True); tot = sum(caps); n = len(caps)
    ac, meia = 0, 0
    for i, c in enumerate(caps):
        ac += c
        if ac >= tot / 2: meia = i + 1; break
    cs = sorted(caps); gini = (2 * sum((i + 1) * c for i, c in enumerate(cs)) / (n * tot) - (n + 1) / n) if n else 0
    return {'n': n, 'meia': meia, 'gini': round(gini, 3), 'maior': round(100 * caps[0] / tot, 1)}
cap_ge = {g: (v.get('capital') or 0) for g, v in nos.items()}
cap_ub = {u['id']: (u['capital'] or 0) for u in unidades}
# C e D encadeiam unidades (união-busca): C junta as da mesma linhagem; D junta, além disso,
# as da mesma federação — e uma linhagem que toca duas federações as encadeia (por isso é teto).
def encadeia(chaves):
    pai = {u['id']: u['id'] for u in unidades}
    def raiz(x):
        while pai[x] != x: pai[x] = pai[pai[x]]; x = pai[x]
        return x
    for ch in chaves:
        g = collections.defaultdict(list)
        for u in unidades:
            if u[ch]: g[u[ch]].append(u['id'])
        for l in g.values():
            for x in l[1:]: pai[raiz(x)] = raiz(l[0])
    b = collections.defaultdict(float)
    for u in unidades: b[raiz(u['id'])] += cap_ub[u['id']]
    return list(b.values())
funil = [
    dict(rot='Grupos da rede (códigos GE)', grau='—', **leitura(list(cap_ge.values()))),
    dict(rot='Unidades de controle (A + B)', grau='A+B', **leitura(list(cap_ub.values()))),
    dict(rot='Com as linhagens familiares (+ C)', grau='+C', **leitura(encadeia(['lin']))),
    dict(rot='Com as federações (+ D) — só teto', grau='+D', **leitura(encadeia(['lin', 'fed']))),
]
for f_ in funil: print(f"   funil: {f_['rot']:40} unidades {f_['n']:4d} · metade do capital em {f_['meia']:3d} · Gini {f_['gini']} · maior {f_['maior']}%")

# ---------------- 4b. nomes publicáveis (revisão de exposição, 23/10/2026) ----------------
# O autor liberou o nome de mercado e o capital por grupo ("reverter os dois"). O campo de
# nome de mercado da v5, porém, acumula anotações de trabalho: nomes de sócios entre
# parênteses, notas de rodada, e narrativas (falência, venda, licitação perdida, "vínculo
# suspeito"). Publica-se só o nome comercial: sem parênteses, sem o que vem depois de
# travessão/barra vertical/ponto e vírgula; e, onde o próprio nome comercial é o nome
# completo de uma pessoa física, a forma curta que a tese usa (Quadro 18: "o Barata",
# "o Belarmino"). "Em recuperação judicial" sai da razão social: é situação processual,
# fica fora como as demais narrativas de conduta.
def limpa_nome(s):
    if not s: return None
    s = _re.split(r'\s+[—–|]\s+|\s*\|\s*|;\s*|\s+-\s+', str(s))[0]
    ant = None
    while ant != s: ant = s; s = _re.sub(r'\s*\([^()]*\)', '', s)
    s = _re.sub(r'\s*\([^)]*$', '', s).strip(' ,.')
    return None if not s or s.lower().startswith('não identificado') else s
NOME_PESSOA = {   # ajustes pontuais de nome (23/10/2026)
    # Decisão do autor (23/10, "1b"): quando o nome comercial é o nome do fundador ou
    # controlador, publica-se o nome completo — é a marca pela qual o grupo é conhecido.
    # Ficam aqui só a nota narrativa cortada e a desambiguação dos dois ramos Constantino.
    'GE-222': 'VIPA / VINCO / Paulicéia',
    'GE-037': 'Grupo Wagner Canhedo (Viplan)', 'GE-039': 'Grupo Sergio Tadeu Pereira (Sogil / Visate / Coleurb)',
    'UB-006': 'Grupo Constantino (Comporte)', 'UB-016': 'Grupo Constantino (ramo de Brasília)',
}
sem_rj = lambda t: None if t is None else _re.sub(r'\s*-?\s*EM RECUPERACAO JUDICIAL\s*', ' ', str(t), flags=_re.I).replace('  ', ' ').strip(' -')
for gid, v in nos.items():
    v['mercado'] = NOME_PESSOA[gid] if gid in NOME_PESSOA else limpa_nome(v.get('mercado'))
    for k in ('nome', 'rot', 'central'): v[k] = sem_rj(v.get(k))
    if v['mercado'] and v['mercado'].lower() == (v['rot'] or '').lower(): v['mercado'] = None
for u in unidades:
    if u['lin']: u['lin'] = u['lin'].split()[0]   # só o código; o nome da linhagem vem da lista
    if u['id'] in NOME_PESSOA: u['nome'] = NOME_PESSOA[u['id']]
    elif len(u['membros']) == 1 and u['membros'][0] in nos:
        g = nos[u['membros'][0]]; u['nome'] = g['mercado'] or g['rot']
    else: u['nome'] = limpa_nome(u['nome']) or ' + '.join(nos[m]['rot'] for m in u['membros'] if m in nos)
_cnt = collections.Counter(u['nome'] for u in unidades)
for u in unidades:
    if _cnt[u['nome']] > 1: u['nome'] = f"{u['nome']} ({u['id']})"
for l in linhagens: l['nome'] = limpa_nome(l['nome'])
# decisão do autor (23/10, "2b"): o tipo da LIN-11 apontava para uma pessoa ("aquisição em
# nome de herdeira"); vai ao site na forma neutra das demais linhagens
for l in linhagens:
    if l['id'] == 'LIN-11': l['tipo'] = 'partilha familiar'
_PESSOA_RE = r'\b(?:Sidnei|Jelson|Auristela|Cristiane|herdeira|Roberto Pereira|Nenê|Rodada|falência|faliu|suspeit\w*|cassou)\b'

# nomes municipais: partículas em minúscula ("Foz do Iguaçu", não "Foz Do Iguaçu")
_particulas = lambda t: _re.sub(r"(?<=\s)(Do|Da|De|Dos|Das|E|D')(?=\s|$)", lambda m: m.group(1).lower(), t)

# ---------------- 5. geografia: contornos das UFs e ponto de cada município com presença ----------------
# Para o mapa dos municípios do grupo selecionado (pedido do autor, 23/10/2026). Lê a mesma
# geometria do Painel Brasil e projeta de forma simples (equiretangular corrigida pela latitude
# média); o mapa é de localização, não de área.
GEO = os.path.join(BASE_DIR, '..', 'build', 'geo.topojson')
topo = json.load(open(GEO, encoding='utf-8'))
sc, tr = topo['transform']['scale'], topo['transform']['translate']
arcos = []
for a in topo['arcs']:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy; pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
    arcos.append(pts)
LAT0 = math.cos(math.radians(-15))
LON_MIN, LAT_MAX = -74.2, 5.6
def proj(lon, lat):
    return ((lon - LON_MIN) * LAT0 * 15.0, (LAT_MAX - lat) * 15.0)
def anel(idx_arcos):
    pts = []
    for i in idx_arcos:
        seg = arcos[i] if i >= 0 else list(reversed(arcos[~i]))
        pts.extend(seg if not pts else seg[1:])
    return pts
def poligonos(g):
    if g['type'] == 'Polygon': return [g['arcs']]
    if g['type'] == 'MultiPolygon': return g['arcs']
    return []
ufs_svg = []
for g in topo['objects']['ufs']['geometries']:
    d = []
    for pol in poligonos(g):
        for ring in pol[:1]:          # só o anel externo
            pts = [proj(*p) for p in anel(ring)]
            simp, ult = [], None
            for p in pts:
                if ult is None or abs(p[0] - ult[0]) + abs(p[1] - ult[1]) > 1.6:
                    simp.append(p); ult = p
            if len(simp) > 3:
                d.append('M' + 'L'.join(f'{x:.0f},{y:.0f}' for x, y in simp) + 'Z')
    ufs_svg.append(''.join(d))
pontos = {}
for g in topo['objects']['municipios_simpl']['geometries']:
    cod = str((g.get('properties') or {}).get('cod_ibge') or '')
    if cod not in presenca: continue
    pts = [p for pol in poligonos(g) for p in anel(pol[0])]
    if pts:
        lon = sum(p[0] for p in pts) / len(pts); lat = sum(p[1] for p in pts) / len(pts)
        x, y = proj(lon, lat); pontos[cod] = [round(x, 1), round(y, 1)]
print(f"geografia: {len(ufs_svg)} UFs, {len(pontos)} de {len(presenca)} municípios com ponto")

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({'nos': [nos[g] for g in sorted(nos)], 'arestas': arestas,
               'presenca': {c: sorted(presenca[c]) for c in sorted(presenca, key=int)},
               'mun': {c: _particulas(NOME[c]) for c in sorted(presenca, key=int)},
               'unidades': unidades, 'linhagens': linhagens, 'familias': familias, 'federacoes': fed_out,
               'escala': escala, 'funil': funil, 'n_topo_ub': n_topo_ub,
               'geo': {'ufs': ufs_svg, 'pontos': pontos},
               'resumo': {'n_grupos': len(nos), 'n_topo': n_topo, 'n_mun': len(presenca),
                          'pop_mun': sum(POP.get(c, 0) for c in presenca),
                          # empresas dos grupos pela Tabela mestre (1.040, como na tese); a soma de n_emp por grupo dá 1.039
                          'n_emp': int(v5e['id_grupo'].astype(str).str.startswith('GE').sum()),
                          'retrato': 'Tabela mestre v5, 17/10/2026; cadastro de CNPJ, recorte de maio de 2024'}},
              f, ensure_ascii=False, separators=(',', ':'))
# auditoria da fronteira de exposição: falha o build se algo escapou
_saida = open(OUT, encoding='utf-8').read()
# CPF: formato pontuado (000.000.000-00) e mascarado da Receita (***.000.000-**); números
# soltos de 11 dígitos só dentro de texto (capital é numérico e arredondado a reais).
assert not _re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}|\*{3}\.?\d{3}\.?\d{3}-?\*{2}', _saida), 'padrão de CPF na saída'
assert not _re.search(r'"[^"]*\b\d{11}\b[^"]*"', _saida), 'sequência de 11 dígitos em texto'
assert not _re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}', _saida), 'CNPJ na saída'
_hit = _re.search(_PESSOA_RE, _saida, flags=_re.I)
assert not _hit, f'nome de pessoa ou narrativa na saída: {_saida[max(0,_hit.start()-60):_hit.end()+20]!r}'
print(f"rede_ge.json: {os.path.getsize(OUT)/1024:.0f} KB — auditoria: sem CPF, sem CNPJ")
