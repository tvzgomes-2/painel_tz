#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figuras_cap3_cap5_r08.py — 01/10/2026. Figuras novas da revisão r08 da tese.

Cap. 3, seção 3.5: Gráfico 9 (regime de prestação por porte, MUNIC 2020) e
Gráfico 10 (CNPJs ativos por CNAE de transporte de passageiros, Receita Federal).
Cap. 5 (retrato congelado de 01/10/2026): Figura 8 (políticas vigentes por ano),
Mapa 2 (camada 1 por período de implantação, com as encerradas) e Figura 9 (taxa
de adoção por porte, com denominador). Lê só arquivos do cofre; grava SVG+PNG em
_attachments/. Paleta do Design System de Figuras (hex fixos, fundo branco).
"""
import json, os
import pandas as pd, numpy as np, geopandas as gpd, matplotlib as mpl
mpl.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
V = os.path.expanduser('~/mnt/doutorado'); D = f'{V}/03 - Dados/_data'; A = f'{V}/_attachments'
RET = f'{D}/casos por fonte/retratos/2026-10-01'
R = json.load(open(f'{RET}/retrato_cap5.json'))
ROSA, AZUL, TINTA, FRACA, GRADE, EIXO = '#FF2D6B', '#1A54C7', '#0E0E10', '#5D5D64', '#DBDBE4', '#C3C3CC'
ROSA3, AZUL3, VERDE = '#FFA8B3', '#A4C5FF', '#326F00'
mpl.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Poppins', 'Segoe UI', 'Calibri', 'DejaVu Sans'], 'font.size': 8,
 'axes.edgecolor': EIXO, 'axes.labelcolor': TINTA, 'xtick.color': FRACA, 'ytick.color': FRACA, 'axes.spines.top': False, 'axes.spines.right': False,
 'axes.grid': True, 'grid.color': GRADE, 'grid.linewidth': 0.5, 'legend.frameon': False, 'figure.facecolor': 'white', 'axes.facecolor': 'white', 'svg.fonttype': 'none'})
cm = 1 / 2.54
def br(x, d=0): return f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
def save(fig, nome):
    fig.savefig(f'{A}/{nome}.svg'); fig.savefig(f'{A}/{nome}.png', dpi=250); plt.close(fig); print('ok', nome)

# ---------- Gráfico 9 — regime de prestação por porte (MUNIC 2020)
f = pd.read_csv(f'{D}/Analises_Cap3/munic2020_regime_por_faixa.csv').set_index('recorte')
fx = ['até 20 mil', '20 a 100 mil', 'acima de 100 mil']
fig, ax = plt.subplots(figsize=(16 * cm, 7.2 * cm), layout='constrained')
x = np.arange(len(fx)); w = 0.26
series = [('concessao', 'Concessão', AZUL), ('prestacao_direta', 'Prestação direta pela prefeitura', ROSA), ('isencao_toda_populacao', 'Isenção para toda a população', VERDE)]
for i, (c, lab, co) in enumerate(series):
    v = (f.loc[fx, c] / f.loc[fx, 'municipios_com_onibus'] * 100).values
    b = ax.bar(x + (i - 1) * w, v, w * 0.92, color=co, label=lab, zorder=3)
    for xi, vi, n in zip(x + (i - 1) * w, v, f.loc[fx, c].values):
        ax.annotate(f'{br(vi)}%\n({br(n)})', (xi, vi), xytext=(0, 2), textcoords='offset points', ha='center', va='bottom', fontsize=6.5, color=TINTA)
ax.set_xticks(x, [f'{a}\n{br(n)} com ônibus' for a, n in zip(fx, f.loc[fx, 'municipios_com_onibus'])])
ax.set_ylabel('% dos municípios com ônibus intramunicipal'); ax.set_ylim(0, 112); ax.set_yticks(range(0, 101, 20)); ax.grid(axis='x', visible=False)
ax.legend(loc='upper left', fontsize=7, ncol=1)
save(fig, 'cap3-analise-X-munic2020-regime-porte')

# ---------- Gráfico 10 — CNPJs ativos por CNAE
c = pd.read_csv(f'{D}/Analises_Cap3/contagem_cnae_transporte_mesclado.csv')
lab = {'nucleo': 'Urbano municipal e metropolitano\n4921-3/01 e /02 (núcleo)', 'intermun': 'Intermunicipal e interestadual\n4922-1', 'fretamento': 'Fretamento\n4929-9/01 e /02',
       'excursao_outros': 'Excursões e outros\n4929-9/03, /04 e /99', 'escolar': 'Transporte escolar\n4924-8/00', 'saude_remocao': 'Remoção de pacientes\n8622-4/00', 'saude_urgencia': 'Atendimento móvel de urgência\n8621-6/01 e /02'}
c = c.set_index('grupo').loc[['fretamento', 'escolar', 'excursao_outros', 'nucleo', 'saude_urgencia', 'saude_remocao', 'intermun']]
fig, ax = plt.subplots(figsize=(16 * cm, 9.6 * cm), layout='constrained')
y = np.arange(len(c))[::-1]
ax.barh(y, c['cnpj_base_ativos_qualquer'] / 1000, 0.62, color=AZUL3, label='CNPJs-base ativos com a CNAE (principal ou secundária)', zorder=3)
ax.barh(y, c['cnpj_base_ativos_principal'] / 1000, 0.62, color=AZUL, label='… com a CNAE como principal', zorder=3)
both = c['cnpj_base_ativos_tambem_nucleo'].fillna(0)
ax.scatter(both / 1000, y, marker='|', s=120, color=ROSA, zorder=4, label='… que também têm CNAE do núcleo (4921-3)')
for yi, (g, r) in zip(y, c.iterrows()):
    t = f"{br(r.cnpj_base_ativos_qualquer)}  (principal: {br(r.cnpj_base_ativos_principal)}"
    t += f"; com núcleo: {br(r.cnpj_base_ativos_tambem_nucleo)})" if g != 'nucleo' else ')'
    ax.annotate(t, (r.cnpj_base_ativos_qualquer / 1000, yi), xytext=(4, 0), textcoords='offset points', va='center', fontsize=6.5, color=TINTA)
ax.set_yticks(y, [lab[g] for g in c.index], fontsize=7); ax.set_xlim(0, 420); ax.set_xlabel('mil CNPJs-base ativos'); ax.grid(axis='y', visible=False)
ax.legend(loc='upper center', bbox_to_anchor=(0.45, -0.16), ncol=2, fontsize=6.5)
save(fig, 'cap3-analise-XI-cnae-transporte-passageiros')

# ---------- Figura 8 (Cap. 5) — políticas vigentes por ano e inícios por ano
vig = pd.Series(R['vigentes_por_ano']).astype(int); vig.index = vig.index.astype(int)
ini = pd.Series(R['inicio_por_ano_escopo']).astype(int); ini.index = ini.index.astype(int)
fig, ax = plt.subplots(figsize=(16 * cm, 7.0 * cm), layout='constrained')
yrs = range(1990, 2027)
ax.bar(list(yrs), [ini.get(y, 0) for y in yrs], 0.7, color=ROSA3, label='Políticas iniciadas no ano', zorder=3)
ax.plot(list(yrs), [vig[y] for y in yrs], color=AZUL, lw=1.6, label='Políticas vigentes no fim do ano', zorder=4)
for yv in (2013, 2020):
    ax.axvline(yv - 0.5, color=FRACA, lw=0.6, ls=(0, (2, 2)), zorder=2)
ax.annotate('Junho de 2013', (2012.6, 140), ha='right', fontsize=6.5, color=FRACA)
ax.annotate('Pandemia', (2019.6, 140), ha='right', fontsize=6.5, color=FRACA)
for yv in (2012, 2019, 2022, 2026):
    ax.annotate(br(vig[yv]), (yv, vig[yv]), xytext=(0, 4), textcoords='offset points', ha='center', fontsize=6.5, color=AZUL)
ax.set_xlim(1989.5, 2026.5); ax.set_ylim(0, 175); ax.set_ylabel('nº de políticas municipais'); ax.legend(loc='upper left', fontsize=7)
ax.grid(axis='x', visible=False)
save(fig, 'cap5-politicas-vigentes-por-ano-2026-10-01')

# ---------- Mapa 2 (Cap. 5) — camada 1 por período de implantação + encerradas
m = pd.read_excel(f'{RET}/Municípios TZ - consolidado.xlsx')
pts = pd.read_csv(f'{D}/espacial/pontos_representativos_municipios_2022.csv')
m['cod'] = pd.to_numeric(m['Código IBGE'], errors='coerce'); m = m.merge(pts, left_on='cod', right_on='CD_MUN', how='left')
c1 = m[(m['Situação'] == 'Ativa') & (m['Régua — aba'] == '1 Universal')].copy(); enc = m[m['Situação'] == 'Encerrada'].copy()
ano = pd.to_numeric(c1['Ano início'], errors='coerce')
per = pd.cut(ano, [0, 2012, 2019, 2022, 2026], labels=['até 2012', '2013–2019', '2020–2022', '2023–2026'])
c1['per'] = per.cat.add_categories('sem ano apurado').fillna('sem ano apurado')
uf = gpd.read_file(f'{D}/espacial/BR_UF_2022_simplificado.geojson')
fig, ax = plt.subplots(figsize=(16 * cm, 15 * cm), layout='constrained')
uf.plot(ax=ax, color='#F2F1F0', edgecolor='white', lw=0.6)
cols = {'até 2012': '#0F398D', '2013–2019': '#79A8FF', '2020–2022': '#FF778F', '2023–2026': '#AF0042', 'sem ano apurado': '#787880'}
pop = pd.to_numeric(c1['População (2022)'], errors='coerce').fillna(5000)
sz = lambda p: 4 + 140 * np.sqrt(p / 360000)
for k, co in cols.items():
    s = c1[c1['per'] == k]
    ax.scatter(s.lon, s.lat, s=sz(pd.to_numeric(s['População (2022)'], errors='coerce').fillna(5000)), color=co, alpha=0.85, edgecolor='white', lw=0.3, zorder=3, label=f'{k} ({len(s)})')
ax.scatter(enc.lon, enc.lat, s=sz(pd.to_numeric(enc['População (2022)'], errors='coerce').fillna(5000)), facecolor='none', edgecolor=TINTA, lw=0.7, zorder=4, label=f'encerradas ({len(enc)})')
ax.set_axis_off(); ax.set_xlim(-74.5, -34); ax.set_ylim(-34.2, 5.5)
l1 = ax.legend(loc='lower left', fontsize=7, title='Início da política (camada 1)', title_fontsize=7, alignment='left')
ax.add_artist(l1)
hs = [ax.scatter([], [], s=sz(p), color='#C3C3CC', edgecolor='white') for p in (10000, 50000, 300000)]
ax.legend(hs, ['10 mil hab.', '50 mil hab.', '300 mil hab.'], loc='lower right', fontsize=7, title='População (2022)', title_fontsize=7, labelspacing=1.2)
ax.grid(False)
save(fig, 'cap5-mapa-camada1-periodo-2026-10-01')

# ---------- Figura 9 (Cap. 5) — taxa de adoção por porte
dp = R['denominador_por_porte']; labs = list(dp.keys())
fig, ax = plt.subplots(figsize=(16 * cm, 7.2 * cm), layout='constrained')
x = np.arange(len(labs)); w = 0.38
t_all = [dp[k]['tz_ativas'] / dp[k]['municipios'] * 100 for k in labs]
t_idx = [dp[k]['tz_entre_idx5'] / dp[k]['indice_ge5'] * 100 for k in labs]
b1 = ax.bar(x - w / 2, t_all, w * 0.92, color=AZUL3, label='entre todos os municípios da faixa', zorder=3)
b2 = ax.bar(x + w / 2, t_idx, w * 0.92, color=AZUL, label='entre os municípios com indício de sistema de ônibus (índice ≥ 5)', zorder=3)
for xi, v, k in zip(x - w / 2, t_all, labs):
    ax.annotate(f"{br(v,1)}%\n{dp[k]['tz_ativas']}/{br(dp[k]['municipios'])}", (xi, v), xytext=(0, 2), textcoords='offset points', ha='center', va='bottom', fontsize=6, color=TINTA)
for xi, v, k in zip(x + w / 2, t_idx, labs):
    ax.annotate(f"{br(v,1)}%\n{dp[k]['tz_entre_idx5']}/{br(dp[k]['indice_ge5'])}", (xi, v), xytext=(0, 2), textcoords='offset points', ha='center', va='bottom', fontsize=6, color=TINTA)
ax.set_xticks(x, [k.replace('acima de ', '> ').replace('até ', '≤ ') for k in labs]); ax.set_xlabel('população (Censo 2022)')
ax.set_ylabel('% com Tarifa Zero universal (camada 1)'); ax.set_ylim(0, 20); ax.grid(axis='x', visible=False); ax.legend(loc='upper left', fontsize=7)
save(fig, 'cap5-adocao-por-porte-denominador-2026-10-01')
