# -*- coding: utf-8 -*-
"""figuras_r18.py — figuras novas e refeitas da revisão r18 (02/10/2026) da tese.

Análise I (Gráficos 1 e 2): meio de transporte para o trabalho por rendimento, sexo e cor, e por porte e região,
  a partir dos agregados dos microdados da amostra do Censo 2022 (agregar_modo_perfil_censo2022.py).
Análise II (Gráfico 3): taxa de motorização 2013 e 2025 por faixa de população e por região (Base Municipal v3).
Análise VII (Gráfico novo, fusão do antigo Gráfico 5 com o IPKe): passageiros equivalentes por veículo por dia e IPKe,
  nove sistemas da NTU, transcritos dos rótulos das Figuras 3 e 12 do Anuário NTU 2025-2026 (p. 18 e 31).
Análise X (Gráfico novo): subsídio público em % do custeio, por região (NTU, Anuário 2024-2025, 2025).
Figura 5 (refeita): o Círculo Vicioso — lógica da escassez.
Mapas 3 e 4: a régua descritiva no território (planilha de tipologias, retrato de 01/10/2026).

Paleta: Design System de Figuras (_meta/Design System de Figuras.md). Fundo branco, sem título embutido (a legenda
ABNT vem no documento). Uso: BASE=<pasta do cofre> python figuras_r18.py  (sem BASE, usa as cópias locais).
"""
import os, re, json, unicodedata
import numpy as np, pandas as pd, matplotlib as mpl
mpl.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle, Polygon
BASE = os.environ.get('BASE')
if BASE:
    D = f'{BASE}/03 - Dados/_data'; OUT = f'{BASE}/_attachments'
    MP = f'{D}/Censo2022_Microdados/agregados/modo_perfil/_consolidado/modo_perfil_brasil.csv'
    B3 = f'{D}/Base Municipal v3/base_municipal_v3.csv'; SUB = f'{D}/Base Municipal v3/serie_subsidio_ntu.csv'
    TIP = f'{D}/casos por fonte/retratos/2026-10-01/Tipologias TZ - consolidado.xlsx'
    PTS = f'{D}/espacial/pontos_representativos_municipios_2022.csv'; UFG = f'{D}/espacial/BR_UF_2022_simplificado.geojson'
else:
    U = '/mnt/user-data/uploads/doutorado/03 - Dados/_data'; OUT = 'fig'
    MP = f'{U}/Censo2022_Microdados/agregados/modo_perfil/_consolidado/modo_perfil_brasil.csv'
    B3 = f'{U}/Base Municipal v3/_extratos/2026-10-02/b3sub_r18.csv'; SUB = f'{U}/Base Municipal v3/serie_subsidio_ntu.csv'
    TIP = f'{U}/casos por fonte/retratos/2026-10-01/Tipologias TZ - consolidado.xlsx'
    PTS = f'{U}/espacial/pontos_representativos_municipios_2022.csv'; UFG = f'{U}/espacial/BR_UF_2022_simplificado.geojson'
os.makedirs(OUT, exist_ok=True)
ROSA, AZUL, VERDE, AMAR, CINZA = '#FF2D6B', '#1A54C7', '#326F00', '#BAAD00', '#787880'
TINTA, FRACA, GRADE, EIXO = '#0E0E10', '#5D5D64', '#DBDBE4', '#C3C3CC'
mpl.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Poppins', 'Segoe UI', 'Calibri', 'DejaVu Sans'], 'font.size': 8,
    'axes.edgecolor': EIXO, 'axes.labelcolor': TINTA, 'xtick.color': FRACA, 'ytick.color': FRACA, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRADE, 'grid.linewidth': 0.5, 'legend.frameon': False,
    'figure.facecolor': 'white', 'axes.facecolor': 'white', 'svg.fonttype': 'none'})
cm = 1 / 2.54
def br(v, d=0): return f'{v:.{d}f}'.replace('.', ',')
def salvar(fig, nome):
    fig.savefig(f'{OUT}/{nome}.svg'); fig.savefig(f'{OUT}/{nome}.png', dpi=300); plt.close(fig)

# ---------------------------------------------------------------- dados municipais
b = pd.read_csv(B3, low_memory=False)
b['reg'] = b.cod_ibge.astype(str).str[0].map({'1': 'Norte', '2': 'Nordeste', '3': 'Sudeste', '4': 'Sul', '5': 'Centro-Oeste'})
FX = ['Inferior a 20 mil', 'Entre 20 e 100 mil', 'Entre 100 e 250 mil', 'Entre 250 e 500 mil', 'Acima de 500 mil']
FXR = ['< 20 mil', '20–100 mil', '100–250 mil', '250–500 mil', '> 500 mil']
RG = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']

# ---------------------------------------------------------------- Análise I
a = pd.read_csv(MP); a = a[a.modo != 99]
GRP = {1: 'ativo', 2: 'ativo', 3: 'moto', 4: 'moto', 5: 'auto', 8: 'tpc', 9: 'tpc', 10: 'tpc'}
a['g'] = a.modo.map(GRP).fillna('outros')
a = a.merge(b[['cod_ibge', 'reg', 'faixa_pop_2022']], left_on='cod', right_on='cod_ibge', how='left')
SEG = [('auto', 'Automóvel', AZUL), ('moto', 'Motocicleta e mototáxi', VERDE), ('tpc', 'Ônibus, BRT, trem e metrô', ROSA),
       ('ativo', 'A pé e bicicleta', AMAR), ('outros', 'Outros (van, táxi e aplicativo, demais)', CINZA)]
def share(df, k):
    t = df.pivot_table(index=k, columns='g', values='w', aggfunc='sum', fill_value=0)
    return t.div(t.sum(axis=1), axis=0) * 100
def barras(ax, t, labels, tit=None):
    y = np.arange(len(t)); left = np.zeros(len(t))
    for k, lab, c in SEG:
        v = t[k].values; ax.barh(y, v, left=left, color=c, height=0.72, label=lab, edgecolor='white', linewidth=0.4)
        for yy, l, vv in zip(y, left, v):
            if vv >= 6: ax.text(l + vv / 2, yy, br(vv), ha='center', va='center', fontsize=6.5, color='white' if c != AMAR else TINTA)
        left += v
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.grid(False); ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0); ax.set_xticks([0, 25, 50, 75, 100], ['0', '25', '50', '75', '100%'])
    if tit: ax.set_title(tit, loc='left', fontsize=8, color=TINTA)
RENDA = ['ate_0.5', '0.5_1', '1_2', '2_3', '3_5', '5_10', 'mais_10']
RENDAL = ['Até ½ SM', 'Mais de ½ a 1', 'Mais de 1 a 2', 'Mais de 2 a 3', 'Mais de 3 a 5', 'Mais de 5 a 10', 'Mais de 10 SM']
tr = share(a, 'renda').loc[RENDA]
ts = share(a, 'sexo').loc[[1, 2]]; tc = share(a, 'cor').loc[[1, 2, 4, 3, 5]]
tsc = pd.concat([ts, tc])
fig, (a1, a2) = plt.subplots(2, 1, figsize=(16 * cm, 11.5 * cm), gridspec_kw={'height_ratios': [7, 7]}); fig.set_layout_engine('constrained')
barras(a1, tr, RENDAL, 'Por rendimento de todos os trabalhos, em salários mínimos (SM de 2022: R$ 1.212)')
barras(a2, tsc, ['Homens', 'Mulheres', 'Branca', 'Preta', 'Parda', 'Amarela', 'Indígena'], 'Por sexo e por cor ou raça')
h, l = a1.get_legend_handles_labels(); fig.legend(h, l, loc='outside lower center', ncol=3, fontsize=7)
salvar(fig, 'cap2-analise-I-modo-por-renda-sexo-cor')
# Gráfico 2: porte e região, todos x até 2 SM
lo = a[a.renda.isin(['ate_0.5', '0.5_1', '1_2'])]
def duplo(k, ordem, rot):
    t1 = share(a, k).loc[ordem]; t2 = share(lo, k).loc[ordem]; rows = []; labs = []
    for o, r_ in zip(ordem, rot):
        rows += [t1.loc[o], t2.loc[o]]; labs += [f'{r_} · todos', 'até 2 SM']
    return pd.DataFrame(rows), labs
fig, (a1, a2) = plt.subplots(1, 2, figsize=(16 * cm, 9 * cm), sharex=True); fig.set_layout_engine('constrained')
t, l_ = duplo('faixa_pop_2022', FX, FXR); barras(a1, t, l_, 'Por faixa de população do município')
t, l_ = duplo('reg', RG, RG); barras(a2, t, l_, 'Por região')
for ax in (a1, a2):
    for yl in ax.get_yticklabels():
        if yl.get_text() == 'até 2 SM': yl.set_color(FRACA)
h, l = a1.get_legend_handles_labels(); fig.legend(h, l, loc='outside lower center', ncol=3, fontsize=7)
salvar(fig, 'cap2-analise-I-modo-por-porte-regiao')

# ---------------------------------------------------------------- Análise II
b['pop_2023'] = (b.pop_2022 + b.pop_2024) / 2
def taxa(x, y, v): return x[f'frota_{v}_{y}'].sum() / x[f'pop_{y}'].sum() * 1000
rows = [('Brasil', b)] + [(r_, b[b.faixa_pop_2022 == f]) for f, r_ in zip(FX, FXR)] + [(r_, b[b.reg == r_]) for r_ in RG]
fig, axs = plt.subplots(1, 2, figsize=(16 * cm, 8.5 * cm), sharey=True); fig.set_layout_engine('constrained')
y = np.array([0, 1.4, 2.4, 3.4, 4.4, 5.4, 6.8, 7.8, 8.8, 9.8, 10.8])
for ax, v, c, tit in [(axs[0], 'auto', AZUL, 'Automóveis por mil habitantes'), (axs[1], 'moto', VERDE, 'Motocicletas por mil habitantes')]:
    for yy, (lab, x) in zip(y, rows):
        v0, v1 = taxa(x, 2013, v), taxa(x, 2025, v)
        ax.plot([v0, v1], [yy, yy], color=c, lw=2, alpha=0.35, solid_capstyle='round')
        ax.scatter([v0], [yy], s=22, color='white', edgecolor=c, zorder=3, lw=1.2); ax.scatter([v1], [yy], s=26, color=c, zorder=3)
        ax.text(v1 + 8, yy, f'{br(v1)} (+{br((v1 / v0 - 1) * 100)}%)', va='center', fontsize=6.5, color=TINTA)
    ax.set_title(tit, loc='left', fontsize=8, color=TINTA); ax.grid(axis='y', visible=False); ax.set_xlim(0, 560 if v == 'auto' else 230)
axs[0].set_yticks(y, [r[0] for r in rows]); axs[0].invert_yaxis(); axs[0].tick_params(axis='y', length=0)
for ax in axs: ax.axhline(0.7, color=EIXO, lw=0.5); ax.axhline(6.1, color=EIXO, lw=0.5)
from matplotlib.lines import Line2D
fig.legend([Line2D([], [], marker='o', ls='', mfc='white', mec=FRACA), Line2D([], [], marker='o', ls='', color=FRACA)], ['2013', '2025'],
           loc='outside lower center', ncol=2, fontsize=7)
salvar(fig, 'cap2-analise-II-motorizacao-porte-regiao')

# ---------------------------------------------------------------- Análise VII (NTU, rótulos transcritos)
IPK = {1993: (2.52, 2.45), 1994: (2.41, 2.43), 1995: (2.59, 2.37), 1996: (2.30, 2.16), 1997: (2.10, 2.07), 1998: (2.01, 1.89),
       1999: (1.72, 1.77), 2000: (1.69, 1.69), 2001: (1.62, 1.63), 2002: (1.64, 1.67), 2003: (1.59, 1.66), 2004: (1.56, 1.57),
       2005: (1.60, 1.58), 2006: (1.70, 1.63), 2007: (1.65, 1.67), 2008: (1.65, 1.65), 2009: (1.56, 1.60), 2010: (1.64, 1.66),
       2011: (1.59, 1.63), 2012: (1.63, 1.65), 2013: (1.68, 1.70), 2014: (1.66, 1.68), 2015: (1.62, 1.60), 2016: (1.56, 1.46),
       2017: (1.45, 1.51), 2018: (1.57, 1.56), 2019: (1.49, 1.50), 2020: (0.97, 1.26), 2021: (1.57, 1.34), 2022: (1.60, 1.61),
       2023: (1.53, 1.56), 2024: (1.49, 1.44), 2025: (1.53, 1.43)}
PVD = {1995: (None, 631), 1996: (581, 569), 1997: (555, 568), 1998: (505, 506), 1999: (446, 451), 2000: (422, 435), 2001: (400, 438),
       2002: (440, 447), 2003: (391, 428), 2004: (393, 407), 2005: (402, 409), 2006: (411, 421), 2007: (395, 439), 2008: (415, 439),
       2009: (392, 411), 2010: (389, 412), 2011: (398, 408), 2012: (383, 406), 2013: (389, 407), 2014: (370, 401), 2015: (348, 365),
       2016: (341, 339), 2017: (313, 347), 2018: (329, 352), 2019: (328, 343), 2020: (108, 226), 2021: (260, 243), 2022: (272, 306),
       2023: (274, 295), 2024: (291, 298), 2025: (281, 283)}
rows = [(y, 'IPKe', ab, ou) for y, (ab, ou) in IPK.items()] + [(y, 'pass_veic_dia', ab, ou) for y, (ab, ou) in PVD.items()]
ntu = pd.DataFrame(rows, columns=['ano', 'indicador', 'abril', 'outubro'])
ntu['media'] = ntu[['abril', 'outubro']].mean(axis=1)
ntu.to_csv(f'{OUT}/../ntu_ipke_passveic_1993_2025.csv' if not BASE else f'{D}/Analises_Cap3/ntu_ipke_passveic_1993_2025.csv', index=False)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(16 * cm, 7.2 * cm)); fig.set_layout_engine('constrained')
for ax, ind, tit, ylim, fmt in [(a1, 'pass_veic_dia', 'Passageiros equivalentes por veículo por dia', (0, 700), 0),
                                (a2, 'IPKe', 'Passageiros equivalentes por quilômetro (IPKe)', (0, 2.8), 2)]:
    x = ntu[ntu.indicador == ind]
    ax.fill_between(x.ano, x.abril, x.outubro, color=GRADE, lw=0, label='Intervalo abril–outubro')
    ax.plot(x.ano, x.media, color=ROSA, lw=1.8, label='Média de abril e outubro')
    for yr in ([1996, 2019, 2020, 2025] if ind != 'IPKe' else [1993, 2019, 2020, 2025]):
        v = float(x.loc[x.ano == yr, 'media'].iloc[0]); ax.scatter([yr], [v], s=14, color=ROSA, zorder=3)
        ax.annotate(br(v, fmt), (yr, v), textcoords='offset points', xytext=(9 if yr in (1993, 1996) else 0, 6 if yr != 2020 else -11), ha='left' if yr in (1993, 1996) else 'center', fontsize=6.5, color=TINTA)
    ax.set_ylim(*ylim); ax.set_title(tit, loc='left', fontsize=8, color=TINTA); ax.set_xlim(1992, 2026)
    ax.grid(axis='x', visible=False); ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: br(v, 1 if fmt else 0)))
h, l = a1.get_legend_handles_labels(); fig.legend(h, l, loc='outside lower center', ncol=2, fontsize=7)
salvar(fig, 'cap3-analise-VII-demanda-produtividade-ntu')

# ---------------------------------------------------------------- Análise X (subsídio por região)
s = pd.read_csv(SUB); s = s[(s.ano == 2025) & ~((s.cidade_ntu == 'Curitiba') & (s.escopo == 'RM'))]
s = s.merge(b[['cod_ibge', 'reg', 'faixa_pop_2022', 'pop_2022']], on='cod_ibge', how='left')
fig, ax = plt.subplots(figsize=(16 * cm, 7.5 * cm)); fig.set_layout_engine('constrained')
ordem = ['Centro-Oeste', 'Norte', 'Sudeste', 'Sul', 'Nordeste']
rng = np.random.default_rng(7)
for i, r_ in enumerate(ordem):
    x = s[s.reg == r_].sort_values('pct_subsidio'); jit = rng.uniform(-0.18, 0.18, len(x))
    cap = x.cidade_ntu.isin(['Brasília', 'Goiânia', 'Manaus', 'São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Curitiba', 'Porto Alegre',
                              'Salvador', 'Recife', 'Fortaleza', 'Natal', 'Teresina', 'Cuiabá', 'Campo Grande', 'Florianópolis', 'Vitória',
                              'Macapá', 'Palmas', 'Boa Vista'])
    ax.scatter(x.pct_subsidio[~cap], i + jit[~cap.values], s=16, color='white', edgecolor=AZUL, lw=0.9, zorder=3)
    ax.scatter(x.pct_subsidio[cap], i + jit[cap.values], s=20, color=AZUL, zorder=3)
    med = x.pct_subsidio.median(); ax.plot([med, med], [i - 0.32, i + 0.32], color=ROSA, lw=2, zorder=4)
    ax.text(101, i, f'n = {len(x)} · mediana {br(med)}%', va='center', fontsize=6.5, color=TINTA)
    OFF = {'Brasília': (6, 9), 'Goiânia': (-6, 9), 'Araucária': (-10, 9), 'Toledo': (10, -12), 'Manaus': (0, 9), 'São Paulo': (0, 9),
           'Campina Grande': (-4, 9), 'Natal': (2, -12), 'Salvador': (14, 9), 'Linhares': (0, 9)}
    for _, rr in x[x.cidade_ntu.isin(list(OFF))].iterrows():
        dx, dy = OFF[rr.cidade_ntu]
        ax.annotate(rr.cidade_ntu, (rr.pct_subsidio, i), textcoords='offset points', xytext=(dx, dy), ha='center', fontsize=5.8, color=FRACA)
ax.axvline(s.pct_subsidio.mean(), color=FRACA, lw=0.8, ls='--'); ax.text(s.pct_subsidio.mean() + 1, -0.62, f'média geral {br(s.pct_subsidio.mean())}%', fontsize=6.5, color=FRACA)
ax.set_yticks(range(len(ordem)), ordem); ax.invert_yaxis(); ax.set_xlim(-2, 100); ax.set_ylim(len(ordem) - 0.5, -0.9)
ax.set_xlabel('Subsídio público, em % do custeio do sistema (2025)'); ax.grid(axis='y', visible=False); ax.tick_params(axis='y', length=0)
fig.legend([Line2D([], [], marker='o', ls='', color=AZUL), Line2D([], [], marker='o', ls='', mfc='white', mec=AZUL), Line2D([], [], color=ROSA, lw=2)],
           ['Capital', 'Demais municípios', 'Mediana da região'], loc='outside lower center', ncol=3, fontsize=7)
salvar(fig, 'cap3-analise-X-subsidio-por-regiao')
s.to_csv(f'{OUT}/../subsidio_ntu_2025_regiao.csv' if not BASE else f'{D}/Analises_Cap3/subsidio_ntu_2025_regiao.csv', index=False)

# ---------------------------------------------------------------- Figura 5 (Círculo Vicioso)
fig, ax = plt.subplots(figsize=(16 * cm, 12 * cm)); ax.set_xlim(-2.3, 2.3); ax.set_ylim(-1.7, 1.72); ax.set_aspect('equal'); ax.axis('off')
R = 0.92; ang = [90, 0, -90, 180]
NOS = [('Aumento\nda tarifa', 'recompõe a receita;\nafasta mais usuários,\nsobretudo os mais pobres', ROSA, 'white'),
       ('Pressão por corte\nde custos', 'equilíbrio econômico-financeiro\ndo contrato, com receita\nque depende do passageiro', '#E9E9EE', TINTA),
       ('Piora do serviço', 'frota envelhecida,\nmenor frequência,\nintervalos mais longos', '#E9E9EE', TINTA),
       ('Queda da demanda', 'migração de quem pode\npagar para o automóvel\ne a motocicleta', '#E9E9EE', TINTA)]
pos = [(1.45 * np.cos(np.radians(t)), 1.12 * np.sin(np.radians(t))) for t in ang]
for (tit, sub, fc, tc), (x, y) in zip(NOS, pos):
    ax.add_patch(Circle((x, y), 0.56, fc=fc, ec='none', zorder=2))
    ax.text(x, y + 0.17, tit, ha='center', va='center', fontsize=8.5, fontweight='bold', color=tc, zorder=3)
    ax.text(x, y - 0.17, sub, ha='center', va='center', fontsize=6.2, color=tc, zorder=3, linespacing=1.15)
for i in range(4):
    (x0, y0), (x1, y1) = pos[i], pos[(i + 1) % 4]
    v = np.array([x1 - x0, y1 - y0]); u = v / np.linalg.norm(v)
    p0 = np.array([x0, y0]) + u * 0.6; p1 = np.array([x1, y1]) - u * 0.6
    ax.add_patch(FancyArrowPatch(p0, p1, connectionstyle='arc3,rad=-0.28', arrowstyle='-|>', mutation_scale=13, lw=1.6,
                                 color=TINTA if i else ROSA, zorder=1))
ax.text(0, 0, 'Lógica da escassez\na tarifa como fonte\n(quase) única de custeio', ha='center', va='center', fontsize=7.5, color=FRACA, style='italic')
xq, yq = pos[3]
ax.add_patch(FancyArrowPatch((xq - 0.55, yq - 1.05), (xq - 0.2, yq - 0.58), arrowstyle='-|>', mutation_scale=12, lw=1.4, color=AZUL, ls='--'))
ax.text(xq - 0.85, yq - 1.12, 'Choque externo: a hegemonia do\nautomóvel e da motocicleta (Capítulo 2)', ha='left', va='top', fontsize=6.5, color=AZUL)
fig.subplots_adjust(0, 0, 1, 1); salvar(fig, 'cap3-figura-circulo-vicioso-escassez')

# ---------------------------------------------------------------- Mapas da régua
def norm(t): return re.sub(r'[^A-Z]', '', unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode().upper())
pts = pd.read_csv(PTS); pts['k'] = pts.NM_MUN.map(norm) + '|' + pts.SIGLA_UF
pts = pts.merge(b[['cod_ibge', 'pop_2022']], left_on='CD_MUN', right_on='cod_ibge', how='left')
u1 = pd.read_excel(TIP, sheet_name='1 Universal'); u1['k'] = u1['Município'].map(norm) + '|' + u1.UF.str.strip()
u2 = pd.read_excel(TIP, sheet_name='2 Parcial'); u2['k'] = u2['Município'].map(norm) + '|' + u2.UF.str.strip()
u3 = pd.read_excel(TIP, sheet_name='3 Encerradas'); u3['k'] = u3['Município'].map(norm) + '|' + u3.UF.str.strip()
P = pts.set_index('k')
miss = {n: sorted(set(x.k) - set(P.index)) for n, x in [('u1', u1), ('u2', u2), ('u3', u3)]}
print('sem ponto', {k: v for k, v in miss.items() if v})
gj = json.load(open(UFG, encoding='utf-8'))
def base_map(ax):
    for f in gj['features']:
        g = f['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys:
            ax.add_patch(Polygon(np.array(poly[0]), closed=True, fc='#F4F4F7', ec='#C3C3CC', lw=0.35, zorder=0))
    ax.set_xlim(-74.5, -34); ax.set_ylim(-34.2, 5.8); ax.set_aspect('equal'); ax.axis('off')
def size(pop): return np.clip(np.sqrt(pop.fillna(5000) / 1000) * 3.2, 4, 90)
fig, ax = plt.subplots(figsize=(16 * cm, 14 * cm)); fig.set_layout_engine('constrained'); base_map(ax)
CL = [('1a', 'Universal sem portão (1a)', ROSA), ('1b', 'Universal com cadastro aberto (1b)', AZUL), ('1c', 'Universal com portão de residência (1c)', VERDE),
      ('1d', 'Universal com prazo declarado (1d)', AMAR)]
u1['Subtipo'] = u1['Subtipo'].fillna('em verificação')
x = u1[u1.Subtipo == 'em verificação'].merge(P, left_on='k', right_index=True)
ax.scatter(x.lon, x.lat, s=size(x.pop_2022), fc='white', ec=FRACA, lw=0.7, zorder=2, label=f'Universal, subtipo em verificação ({len(x)})')
for k, lab, c in CL:
    x = u1[u1.Subtipo == k].merge(P, left_on='k', right_index=True)
    ax.scatter(x.lon, x.lat, s=size(x.pop_2022), color=c, alpha=0.9, ec='white', lw=0.4, zorder=3, label=f'{lab} ({len(x)})')
x = u3.merge(P, left_on='k', right_index=True)
ax.scatter(x.lon, x.lat, s=size(x.pop_2022), marker='X', color=TINTA, lw=0, zorder=4, label=f'Encerrada (camada 3) ({len(x)})')
ax.legend(loc='lower right', bbox_to_anchor=(1.02, 0.0), fontsize=7, markerscale=0.9, handletextpad=0.4)
salvar(fig, 'cap5-mapa-regua-camada1-subtipos')
fig, axs = plt.subplots(2, 2, figsize=(16 * cm, 15 * cm)); fig.set_layout_engine('constrained')
C2 = [('2a', 'Grupo social (2a)', ROSA), ('2b', 'Espaço ou linha (2b)', AZUL), ('2c', 'Dias da semana (2c)', VERDE), ('2d', 'Eventos e eleições (2d)', AMAR)]
for ax, (k, lab, c) in zip(axs.flat, C2):
    base_map(ax); x = u2[u2.Subtipo.astype(str).str.contains(k, regex=False)].drop_duplicates('k')  # A.1.15.merge(P, left_on='k', right_index=True)
    ax.scatter(x.lon, x.lat, s=size(x.pop_2022) * 0.8, color=c, alpha=0.85, ec='white', lw=0.3, zorder=3)
    ax.set_title(f'{lab}: {len(x)} municípios', loc='left', fontsize=8, color=TINTA)
salvar(fig, 'cap5-mapa-regua-camada2-subtipos')
print('ok')
