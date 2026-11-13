# -*- coding: utf-8 -*-
"""figuras_padrao.py — figuras da tese do Cap. 2 em diante, no padrão único
do Design System de Figuras (02/10/2026, revisão r19).

O que é "o padrão" (vale para todas as figuras deste script):
  • largura 16 cm (mancha de texto A4, margens 3-2-3-2); altura por tipo;
  • fundo branco; nada de título, fonte ou nota dentro da imagem — a legenda
    ABNT (designativo + nº + título acima, Fonte abaixo) fica no documento;
  • Poppins; corpo 8 pt, eixos 7,5, título de painel 8,5 médio à esquerda,
    legenda 7,5 acima da área de plotagem, alinhada à esquerda, sem moldura;
    rótulos de valor 7; números no formato brasileiro (vírgula decimal);
  • grade só horizontal (ou só vertical em barras deitadas), cinza-claro;
  • cor com significado fixo em toda a tese:
      Tarifa Zero / transporte coletivo ........ rosa
      demais municípios ........................ grafite
      automóvel ................................ grafite-escuro
      motocicleta .............................. azul
      a pé e bicicleta ......................... verde
      outros modos ............................. cinza-claro
      empresas e delegação ao capital privado .. azul (escala)
      poder público (prestação direta) ......... grafite médio
  • amostra pequena (n < 15) = barra vazada, nunca cor mais fraca.

Os DADOS são os mesmos das versões r18 (mesmos arquivos e mesmas contas) —
este script padroniza a forma, não muda número. Exceções declaradas no
docstring de cada figura (valores transcritos de rótulo).

Uso (na raiz do cofre):  python "_meta/scripts/figuras_padrao.py" [nome ...]   (sem nome, gera todas)
Saída: _attachments/tese-*.svg + .png (300 dpi). Variáveis DADOS (raiz do cofre) e SAIDA mudam os caminhos.
Depende de estilo_figuras.py, tz.mplstyle e diagramas.py (mesma pasta) e de rede_bibliometrica.py.
Figuras que ficam de fora: Mapa 1 (índice de indício, figura do artigo Gomes e Zioni, 2026, sem
dado no cofre) e as do Cap. 1 e da Introdução (já no padrão, scripts próprios).
"""
import sys, os, re, json, unicodedata
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon
from matplotlib.lines import Line2D
import matplotlib.ticker as mticker

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from estilo_figuras import aplicar_estilo, salvar as _salvar, cor, NEUTROS

# raiz do cofre: o script mora em _meta/scripts/; DADOS e SAIDA sobrescrevem
U = Path(os.environ.get('DADOS', AQUI.parents[1]))
D = U / '03 - Dados' / '_data'
OUT = Path(os.environ.get('SAIDA', U / '_attachments'))
OUT.mkdir(parents=True, exist_ok=True)
CM = 1 / 2.54
L = 16.0

# ── cores com significado ─────────────────────────────────────────────────
TZ = cor('rosa', 500); TZ_TXT = cor('rosa', 600)
DEMAIS = cor('grafite', 700)
TINTA, TINTA2, FRACA = NEUTROS['tinta'], NEUTROS['tinta_secundaria'], NEUTROS['tinta_fraca']
GRADE, EIXO = NEUTROS['grade'], NEUTROS['eixo']
MODOS = [  # (chave, rótulo, cor de fundo, cor do texto sobre a barra)
    ('auto', 'Automóvel', cor('grafite', 800), '#FFFFFF'),
    ('moto', 'Motocicleta e mototáxi', cor('ambar', 500), TINTA),  # r79: âmbar (azul é âncora dos grupos econômicos)
    ('tpc', 'Ônibus, BRT, trem e metrô', cor('rosa', 500), '#FFFFFF'),
    ('ativo', 'A pé e bicicleta', cor('verde', 700), '#FFFFFF'),
    ('outros', 'Outros (van, táxi e aplicativo, demais)', cor('grafite', 300), TINTA),
]
COR_MODO = {k: c for k, _, c, _ in MODOS}

aplicar_estilo('tese')
mpl.rcParams.update({
    'font.size': 8, 'axes.labelsize': 7.5, 'axes.labelcolor': TINTA2,
    'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5, 'legend.fontsize': 7.5,
    'axes.titlesize': 8.5, 'axes.titleweight': 'medium', 'axes.titlelocation': 'left',
    'axes.titlepad': 6, 'axes.titlecolor': TINTA,
    'figure.constrained_layout.h_pad': 0.06, 'figure.constrained_layout.w_pad': 0.06,
})


def br(v, d=0):
    """Número no formato brasileiro."""
    s = f'{v:,.{d}f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_eixo(ax, eixo='y', d=0, suf=''):
    f = mticker.FuncFormatter(lambda v, _: br(v, d) + suf)
    (ax.yaxis if eixo == 'y' else ax.xaxis).set_major_formatter(f)


def figura(altura, ncols=1, nrows=1, **kw):
    fig, axs = plt.subplots(nrows, ncols, figsize=(L * CM, altura * CM), layout='constrained', **kw)
    return fig, axs


def legenda_topo(fig, handles, ncol=None, **kw):
    """Legenda do padrão: acima de tudo, alinhada à esquerda, sem moldura."""
    return fig.legend(handles=handles, loc='outside upper left', ncol=ncol or len(handles),
                      frameon=False, handlelength=1.2, columnspacing=1.4, handletextpad=0.5, **kw)


def barra_h(ax):
    """Barras deitadas: grade vertical só, sem tique no eixo das categorias."""
    ax.grid(axis='y', visible=False); ax.grid(axis='x', visible=True)
    ax.tick_params(axis='y', length=0)


def barra_v(ax):
    ax.grid(axis='x', visible=False); ax.tick_params(axis='x', length=0)


def salvar(fig, nome):
    _salvar(fig, OUT / f'{nome}.svg', png=True, auditar=False)
    print('  ok', nome)


def chapa(rotulo, c, **kw):
    return Patch(facecolor=c, edgecolor='none', label=rotulo, **kw)


def vazada(rotulo, c):
    return Patch(facecolor='#FFFFFF', edgecolor=c, linewidth=1.1, label=rotulo)


def linha(rotulo, c, **kw):
    return Line2D([], [], color=c, lw=1.8, label=rotulo, **kw)


FIG = {}
def figura_tese(f):
    FIG[f.__name__] = f
    return f


# ═════════════════════════════════════════════════════════════════════════
# CAPÍTULO 2
# ═════════════════════════════════════════════════════════════════════════
FX = ['Inferior a 20 mil', 'Entre 20 e 100 mil', 'Entre 100 e 250 mil', 'Entre 250 e 500 mil', 'Acima de 500 mil']
FXR = ['< 20 mil', '20–100 mil', '100–250 mil', '250–500 mil', '> 500 mil']
RG = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
_cache = {}


def base3():
    if 'b' not in _cache:
        b = pd.read_csv(D / 'Base Municipal v3' / '_extratos' / '2026-10-02' / 'b3sub_r18.csv', low_memory=False)
        b['reg'] = b.cod_ibge.astype(str).str[0].map({'1': 'Norte', '2': 'Nordeste', '3': 'Sudeste', '4': 'Sul', '5': 'Centro-Oeste'})
        _cache['b'] = b
    return _cache['b']


def censo_modo():
    if 'a' not in _cache:
        a = pd.read_csv(D / 'Censo2022_Microdados' / 'agregados' / 'modo_perfil' / '_consolidado' / 'modo_perfil_brasil.csv')
        a = a[a.modo != 99]
        GRP = {1: 'ativo', 2: 'ativo', 3: 'moto', 4: 'moto', 5: 'auto', 8: 'tpc', 9: 'tpc', 10: 'tpc'}
        a['g'] = a.modo.map(GRP).fillna('outros')
        b = base3()
        a = a.merge(b[['cod_ibge', 'reg', 'faixa_pop_2022']], left_on='cod', right_on='cod_ibge', how='left')
        _cache['a'] = a
    return _cache['a']


def share(df, k):
    t = df.pivot_table(index=k, columns='g', values='w', aggfunc='sum', fill_value=0)
    return t.div(t.sum(axis=1), axis=0) * 100


def barras_empilhadas(ax, t, labels, titulo=None, fracos=()):
    y = np.arange(len(t)); left = np.zeros(len(t))
    for k, lab, c, ct in MODOS:
        v = t[k].values
        ax.barh(y, v, left=left, color=c, height=0.74, edgecolor='white', linewidth=0.5)
        for yy, l0, vv in zip(y, left, v):
            if vv >= 7:
                ax.text(l0 + vv / 2, yy, br(vv), ha='center', va='center', fontsize=6.5, color=ct)
        left += v
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100], ['0', '25', '50', '75', '100%'])
    ax.spines['left'].set_visible(False); barra_h(ax); ax.grid(False)
    for yl in ax.get_yticklabels():
        if yl.get_text() in fracos:
            yl.set_color(FRACA)
    if titulo:
        ax.set_title(titulo)


def handles_modos():
    return [chapa(lab, c) for _, lab, c, _ in MODOS]


@figura_tese
def c2_01_modo_renda_sexo_cor():
    """Gráfico 1 (Análise I) — modo por rendimento, sexo e cor (microdados Censo 2022)."""
    a = censo_modo()
    RENDA = ['ate_0.5', '0.5_1', '1_2', '2_3', '3_5', '5_10', 'mais_10']
    RENDAL = ['Até R$ 606', 'R$ 606 a 1.212', 'R$ 1.212 a 2.424', 'R$ 2.424 a 3.636', 'R$ 3.636 a 6.060', 'R$ 6.060 a 12.120', 'Mais de R$ 12.120']
    tr = share(a, 'renda').loc[RENDA]
    # r39 (09/10/2026, pedido do autor): sexo e cor ordenados pelo uso do automóvel, do menor ao maior,
    # como já ocorre no painel de rendimento
    SEXO = {1: 'Homens', 2: 'Mulheres'}; COR = {1: 'Branca', 2: 'Preta', 3: 'Amarela', 4: 'Parda', 5: 'Indígena'}
    ts = share(a, 'sexo').loc[[1, 2]].sort_values('auto')
    tc = share(a, 'cor').loc[[1, 2, 4, 3, 5]].sort_values('auto')
    fig, (a1, a2, a3) = figura(14.0, nrows=3, gridspec_kw={'height_ratios': [7, 2.2, 5]})
    barras_empilhadas(a1, tr, RENDAL, 'Por rendimento mensal de todos os trabalhos, em reais de 2022 (salário mínimo: R$ 1.212)')
    barras_empilhadas(a2, ts, [SEXO[i] for i in ts.index], 'Por sexo')
    barras_empilhadas(a3, tc, [COR[i] for i in tc.index], 'Por cor ou raça')
    legenda_topo(fig, handles_modos(), ncol=3)
    salvar(fig, 'tese-cap2-01-modo-renda-sexo-cor')


@figura_tese
def c2_02_modo_porte_regiao():
    """Gráfico 2 (Análise I) — modo por porte e região, todos × até 2 SM."""
    a = censo_modo(); lo = a[a.renda.isin(['ate_0.5', '0.5_1', '1_2'])]
    # r39 (09/10/2026): cada grupo vira um par de barras com o nome em negrito acima,
    # e os rótulos do eixo dizem só 'todos' e 'até 2 SM' (leitura mais clara, pedido do autor)
    def painel(ax, k, ordem, rot, titulo):
        t1 = share(a, k).loc[ordem]; t2 = share(lo, k).loc[ordem]
        ys, rows, labs = [], [], []
        for i, (o, r_) in enumerate(zip(ordem, rot)):
            y0 = i * 2.9
            ys += [y0, y0 + 1.0]; rows += [t1.loc[o], t2.loc[o]]; labs += ['todos', 'até 2 SM']
            ax.text(0, y0 - 0.62, r_, ha='left', va='bottom', fontsize=7.6, fontweight='medium', color=TINTA)
        t = pd.DataFrame(rows); left = np.zeros(len(t)); ys = np.array(ys)
        for kk, lab, c, ct in MODOS:
            v = t[kk].values
            ax.barh(ys, v, left=left, color=c, height=0.8, edgecolor='white', linewidth=0.5)
            for yy, l0, vv in zip(ys, left, v):
                if vv >= 7:
                    ax.text(l0 + vv / 2, yy, br(vv), ha='center', va='center', fontsize=6.5, color=ct)
            left += v
        ax.set_yticks(ys, labs); ax.invert_yaxis(); ax.set_xlim(0, 100)
        ax.set_ylim(ys.max() + 0.7, -1.25)
        ax.set_xticks([0, 25, 50, 75, 100], ['0', '25', '50', '75', '100%'])
        ax.spines['left'].set_visible(False); barra_h(ax); ax.grid(False)
        for yl in ax.get_yticklabels():
            if yl.get_text() == 'até 2 SM': yl.set_color(FRACA)
        ax.set_title(titulo)
    fig, (a1, a2) = figura(11.0, ncols=2, sharex=True)
    painel(a1, 'faixa_pop_2022', FX, ['Até 20 mil habitantes', '20 mil a 100 mil', '100 mil a 250 mil', '250 mil a 500 mil', 'Mais de 500 mil'], 'Por faixa de população')
    painel(a2, 'reg', RG, RG, 'Por região')
    legenda_topo(fig, handles_modos(), ncol=3)
    salvar(fig, 'tese-cap2-02-modo-porte-regiao')


@figura_tese
def c2_03_motorizacao_porte_regiao():
    """Gráfico 3 (Análise II) — motorização 2013 e 2025 por faixa e região."""
    b = base3().copy()
    def taxa(x, y, v): return x[f'frota_{v}_{y}'].sum() / x[f'pop_{y}'].sum() * 1000
    rows = [('Brasil', b)] + [(r_, b[b.faixa_pop_2022 == f]) for f, r_ in zip(FX, FXR)] + [(r_, b[b.reg == r_]) for r_ in RG]
    y = np.array([0, 1.4, 2.4, 3.4, 4.4, 5.4, 6.8, 7.8, 8.8, 9.8, 10.8])
    fig, axs = figura(8.8, ncols=2, sharey=True)
    for ax, v, c, tit, xmax in [(axs[0], 'auto', COR_MODO['auto'], 'Automóveis por mil habitantes', 560),
                                (axs[1], 'moto', COR_MODO['moto'], 'Motocicletas por mil habitantes', 230)]:
        for yy, (lab, x) in zip(y, rows):
            v0, v1 = taxa(x, 2013, v), taxa(x, 2025, v)
            ax.plot([v0, v1], [yy, yy], color=c, lw=2.2, alpha=0.3, solid_capstyle='round')
            ax.scatter([v0], [yy], s=22, color='white', edgecolor=c, zorder=3, lw=1.2)
            ax.scatter([v1], [yy], s=26, color=c, zorder=3)
            ax.text(v1 + xmax * 0.02, yy, f'{br(v1)} (+{br((v1 / v0 - 1) * 100)}%)', va='center', fontsize=6.5, color=TINTA2)
        ax.set_title(tit); ax.set_xlim(0, xmax); barra_h(ax)
        for h in (0.7, 6.1):
            ax.axhline(h, color=EIXO, lw=0.6)
    axs[0].set_yticks(y, [r[0] for r in rows]); axs[0].invert_yaxis()
    legenda_topo(fig, [Line2D([], [], marker='o', ls='', mfc='white', mec=FRACA, ms=5, label='2013'),
                       Line2D([], [], marker='o', ls='', color=FRACA, ms=5, label='2025')])
    salvar(fig, 'tese-cap2-03-motorizacao-porte-regiao')


@figura_tese
def c2_04_despesa_viario_tpc():
    """Gráfico 4 (Análise III) — Finbra/Siconfi: viário × TPC."""
    dd = D / 'Analises_Cap2'
    brs = pd.read_csv(dd / 'analise_III_brasil_ano.csv'); fx = pd.read_csv(dd / 'analise_III_faixa_2023.csv')
    fig, (a1, a2) = figura(7.6, ncols=2, gridspec_kw={'width_ratios': [1.1, 1]})
    x = brs.ano
    VIA, VIA2 = cor('grafite', 800), cor('grafite', 500)
    a1.plot(x, brs.pct_s451, color=VIA, lw=1.8, marker='o', ms=3)
    a1.plot(x, brs.pct_s782, color=VIA2, lw=1.8, marker='o', ms=3)
    a1.plot(x, brs.pct_s453 + brs.pct_fu26, color=TZ, lw=1.8, ls=(0, (3, 2)), marker='o', ms=3, mfc='white')
    a1.plot(x, brs.pct_s453, color=TZ, lw=1.8, marker='o', ms=3)
    a1.set_ylabel('% da despesa municipal liquidada'); a1.set_xticks(list(x), [str(v) for v in x]); a1.set_ylim(0, None)
    a1.yaxis.set_major_locator(mticker.MultipleLocator(1)); fmt_eixo(a1, 'y', 0); a1.set_title('Brasil, 2019–2023'); barra_v(a1)
    f = fx.set_index('faixa_pop_2022').loc[FX]; yy = np.arange(len(FX)); h = 0.38
    vv = (f.pct_s451 + f.pct_s782).values; vt = (f.pct_s453 + f.pct_fu26).values
    a2.barh(yy - h / 2, vv, h, color=VIA); a2.barh(yy + h / 2, vt, h, color=TZ)
    for y0, v in zip(yy - h / 2, vv): a2.text(v + 0.1, y0, br(v, 1), va='center', fontsize=6.5, color=TINTA2)
    for y0, v in zip(yy + h / 2, vt): a2.text(v + 0.1, y0, br(v, 1), va='center', fontsize=6.5, color=TINTA2)
    a2.set_yticks(yy, FXR); a2.invert_yaxis(); a2.set_xlabel('% da despesa liquidada'); barra_h(a2); fmt_eixo(a2, 'x', 0)
    a2.set_xlim(0, max(vv.max(), vt.max()) * 1.15); a2.set_title('Por faixa de população, 2023')
    legenda_topo(fig, [linha('15.451 Infraestrutura urbana', VIA), linha('26.782 Transporte rodoviário', VIA2),
                       linha('TPC, teto (15.453 + demais subfunções da função 26)', TZ, ls=(0, (3, 2))),
                       linha('TPC, identificável (15.453)', TZ)], ncol=2)
    salvar(fig, 'tese-cap2-04-despesa-viario-tpc')


@figura_tese
def c2_05_munic_transporte_outorga():
    """Gráfico (Análise IV) — série MUNIC: municípios com TPC organizado e forma de outorga."""
    s = pd.read_csv(D / 'MUNIC' / 'serie_transporte_coletivo_intramunicipal_2005-2020.csv')
    fig, (a1, a2) = figura(7.4, ncols=2, gridspec_kw={'width_ratios': [1, 1.15]})
    a1.plot(s.ano, s.pct_com_transporte, color=TZ, lw=1.8, marker='o', ms=4, zorder=3)
    for x, v in zip(s.ano, s.pct_com_transporte):
        dx, ha = {2008: (-4, 'right'), 2009: (-3, 'right')}.get(x, (0, 'center'))
        a1.annotate(br(v, 1) + '%', (x, v), xytext=(dx, 6), textcoords='offset points', ha=ha, fontsize=6.5, color=TINTA2)
    a1.set_ylim(0, 45); a1.set_xticks(list(s.ano), [str(v) for v in s.ano]); fmt_eixo(a1, 'y', 0)
    for t, x in zip(a1.get_xticklabels(), s.ano):
        if x == 2008: t.set_ha('right')
        if x == 2009: t.set_ha('left')
    a1.set_ylabel('% dos municípios'); barra_v(a1)
    a1.set_title('Com ônibus intramunicipal organizado')
    o = s.dropna(subset=['pct_concessao_entre_com'])
    SER = [('pct_concessao_entre_com', 'Concessão', cor('azul', 700)), ('pct_permissao_entre_com', 'Permissão', cor('azul', 400)),
           ('pct_autorizacao_entre_com', 'Autorização', cor('grafite', 500)), ('pct_nao_regulamentado_entre_com', 'Não regulamentado', cor('grafite', 300))]
    x = np.arange(len(o)); w = 0.2
    for i, (c, lab, co) in enumerate(SER):
        a2.bar(x + (i - 1.5) * w, o[c], w * 0.92, color=co)
        for xi, v in zip(x + (i - 1.5) * w, o[c]):
            a2.text(xi, v + 1, br(v), ha='center', va='bottom', fontsize=6, color=TINTA2)
    a2.set_xticks(x, [str(v) for v in o.ano]); a2.set_ylim(0, 70); fmt_eixo(a2, 'y', 0); barra_v(a2)
    a2.set_ylabel('% dos municípios com ônibus')
    a2.set_title('Forma de outorga (mais de uma por município)')
    legenda_topo(fig, [linha('Municípios com ônibus organizado', TZ, marker='o', ms=4)] + [chapa(l, c) for _, l, c in SER], ncol=5)
    salvar(fig, 'tese-cap2-05-munic-transporte-outorga')


@figura_tese
def c2_06_cnae_transporte():
    """Gráfico (Análise VI) — CNPJs-base ativos por CNAE de transporte de passageiros."""
    c = pd.read_csv(D / 'Analises_Cap3' / 'contagem_cnae_transporte_mesclado.csv')
    lab = {'nucleo': 'Urbano municipal e metropolitano\n4921-3/01 e /02 (núcleo)', 'intermun': 'Intermunicipal e interestadual\n4922-1',
           'fretamento': 'Fretamento\n4929-9/01 e /02', 'excursao_outros': 'Excursões e outros\n4929-9/03, /04 e /99',
           'escolar': 'Transporte escolar\n4924-8/00', 'saude_remocao': 'Remoção de pacientes\n8622-4/00',
           'saude_urgencia': 'Atendimento móvel de urgência\n8621-6/01 e /02'}
    c = c.set_index('grupo').loc[['fretamento', 'escolar', 'excursao_outros', 'nucleo', 'saude_urgencia', 'saude_remocao', 'intermun']]
    fig, ax = figura(9.2)
    y = np.arange(len(c))
    A4, A7 = cor('azul', 400), cor('azul', 700)
    ax.barh(y, c.cnpj_base_ativos_qualquer / 1000, 0.64, color=A4, zorder=3)
    ax.barh(y, c.cnpj_base_ativos_principal / 1000, 0.64, color=A7, zorder=3)
    both = c.cnpj_base_ativos_tambem_nucleo.fillna(0)
    ax.scatter(both / 1000, y, marker='|', s=130, color=TINTA, lw=1.6, zorder=4)
    for yi, (g, r) in zip(y, c.iterrows()):
        t = f"{br(r.cnpj_base_ativos_qualquer)}  (principal: {br(r.cnpj_base_ativos_principal)}"
        t += f"; com núcleo: {br(r.cnpj_base_ativos_tambem_nucleo)})" if g != 'nucleo' else ')'
        ax.annotate(t, (r.cnpj_base_ativos_qualquer / 1000, yi), xytext=(4, 0), textcoords='offset points', va='center', fontsize=6.5, color=TINTA2)
    ax.set_yticks(y, [lab[g] for g in c.index], fontsize=7); ax.invert_yaxis(); ax.set_xlim(0, 420)
    ax.set_xlabel('mil CNPJs-base ativos'); barra_h(ax); fmt_eixo(ax, 'x', 0)
    legenda_topo(fig, [chapa('com a CNAE (principal ou secundária)', A4), chapa('com a CNAE como principal', A7),
                       Line2D([], [], marker='|', ls='', color=TINTA, ms=9, mew=1.6, label='que também têm CNAE do núcleo (4921-3)')], ncol=2)
    salvar(fig, 'tese-cap2-06-cnae-transporte')



# ═════════════════════════════════════════════════════════════════════════
# CAPÍTULO 3
# ═════════════════════════════════════════════════════════════════════════
@figura_tese
def c3_01_demanda_produtividade_ntu():
    """Gráfico (Análise VII) — NTU: passageiros equivalentes por veículo/dia e IPKe.
    Dados: ntu_ipke_passveic_1993_2025.csv (rótulos transcritos do Anuário NTU 2025-2026)."""
    ntu = pd.read_csv(D / 'Analises_Cap3' / 'ntu_ipke_passveic_1993_2025.csv')
    fig, (a1, a2) = figura(7.4, ncols=2)
    for ax, ind, tit, ylim, d, marcos in [
            (a1, 'pass_veic_dia', 'Passageiros equivalentes por veículo por dia', (0, 700), 0, [1996, 2019, 2020, 2025]),
            (a2, 'IPKe', 'Passageiros equivalentes por quilômetro (IPKe)', (0, 2.8), 2, [1993, 2019, 2020, 2025])]:
        x = ntu[ntu.indicador == ind]
        ax.fill_between(x.ano, x.abril, x.outubro, color=cor('rosa', 200), lw=0)
        ax.plot(x.ano, x.media, color=TZ, lw=1.8)
        for yr in marcos:
            v = float(x.loc[x.ano == yr, 'media'].iloc[0]); ax.scatter([yr], [v], s=14, color=TZ, zorder=3)
            ax.annotate(br(v, d), (yr, v), textcoords='offset points',
                        xytext=(6 if yr in (1993, 1996) else 0, 6 if yr != 2020 else -11),
                        ha='left' if yr in (1993, 1996) else 'center', fontsize=6.5, color=TINTA2)
        ax.set_ylim(*ylim); ax.set_xlim(1992, 2026); ax.set_title(tit); barra_v(ax)
        fmt_eixo(ax, 'y', 1 if d else 0)
    legenda_topo(fig, [chapa('intervalo entre abril e outubro', cor('rosa', 200)), linha('média de abril e outubro', TZ)])
    salvar(fig, 'tese-cap3-01-demanda-produtividade-ntu')


@figura_tese
def c3_02_pof_gasto_transporte():
    """Gráfico (Análise VIII) — POF 2017-2018: gasto com transporte por classe de rendimento.
    Valores transcritos dos rótulos da versão anterior (IBGE, POF 2017-2018, divulgação de
    04/10/2019): não há arquivo de dados no cofre para esta figura."""
    cl = ['Até R$ 1.908\n(2 SM de 2018)', 'Brasil\n(média)', 'Mais de R$ 23.850\n(25 SM de 2018)']
    SER = [('Transporte (total)', cor('grafite', 800), [9.4, 14.6, 15.3]),
           ('do qual: aquisição de veículo', cor('grafite', 400), [2.3, 5.6, 7.5]),
           ('do qual: transporte urbano', TZ, [2.1, 1.3, 0.4])]
    fig, ax = figura(7.2)
    x = np.arange(3); w = 0.26
    for i, (lab, c, v) in enumerate(SER):
        ax.bar(x + (i - 1) * w, v, w * 0.92, color=c)
        for xi, vi in zip(x + (i - 1) * w, v):
            ax.text(xi, vi + 0.25, br(vi, 1) + '%', ha='center', va='bottom', fontsize=7, color=TINTA2)
    ax.set_xticks(x, cl); ax.set_ylim(0, 17.5); fmt_eixo(ax, 'y', 0); barra_v(ax)
    ax.set_ylabel('% da despesa de consumo da família')
    legenda_topo(fig, [chapa(l, c) for l, c, _ in SER])
    salvar(fig, 'tese-cap3-02-pof-gasto-transporte')


@figura_tese
def c3_03_circulo_vicioso_escassez():
    """Figura — o Círculo Vicioso do Transporte na lógica da escassez (mesmo desenho do Cap. 1)."""
    from diagramas import tela, no, seta, ajustar, bloco_texto
    fig, ax = tela(16.0, 12.0)
    R, G, RC = 1.95, 0.14, 0.9
    P = {'tar': (8.0, -2.0), 'cus': (12.8, -5.9), 'ser': (8.0, -9.8), 'dem': (3.2, -5.9)}
    TXT = {
        'tar': (['Aumento da tarifa'], ['recompõe a receita;', 'afasta mais usuários,', 'sobretudo os mais pobres']),
        'cus': (['Pressão por corte', 'de custos'], ['equilíbrio econômico-', '-financeiro do contrato,', 'com receita que depende', 'do passageiro']),
        'ser': (['Piora do serviço'], ['frota envelhecida,', 'menor frequência,', 'intervalos mais longos']),
        'dem': (['Queda da demanda'], ['migração de quem pode', 'pagar para o automóvel,', 'a motocicleta e o aplicativo']),
    }
    for k, (x, y) in P.items():
        ent = k == 'tar'
        tit, sub = TXT[k]
        txt = '\n'.join([f'**{l}**' for l in tit] + [f'//{l}//' for l in sub])
        no(ax, x, y, R, txt, tamanho=8.5, entrelinha=1.4,
           fundo=cor('grafite', 700) if ent else cor('grafite', 200),
           cor_texto='#FFFFFF' if ent else TINTA, cor_negrito='#FFFFFF' if ent else TINTA,
           cor_secundaria=cor('grafite', 200) if ent else TINTA2, escala_secundaria=0.84)
    (xt, yt), (xc, yc), (xs, ys), (xd, yd) = P['tar'], P['cus'], P['ser'], P['dem']
    seta(ax, [(xt + R + G, yt), (xc, yt), (xc, yc + R + G)], raio=RC)
    seta(ax, [(xc, yc - R - G), (xc, ys), (xs + R + G, ys)], raio=RC)
    seta(ax, [(xs - R - G, ys), (xd, ys), (xd, yd - R - G)], raio=RC)
    seta(ax, [(xd, yd + R + G), (xd, yt), (xt - R - G, yt)], raio=RC)
    bloco_texto(ax, 8.0, -5.9, 'lógica da escassez:\na tarifa como fonte\n(quase) única de custeio', 8,
                cor_texto=FRACA, entrelinha=1.4)
    # choque externo: de fora do ciclo, entra na queda da demanda pelo quadrante inferior esquerdo
    import math
    a = math.radians(225); px, py = xd + (R + G) * math.cos(a), yd + (R + G) * math.sin(a)
    x0 = px - 1.0
    seta(ax, [(x0, ys - 0.45), (x0, py - 1.0), (px, py)], raio=0.5, cor_traco=cor('grafite', 500), espessura=1.4)
    ax.patches[-1].set_linestyle((0, (3, 2)))
    bloco_texto(ax, x0 - 0.15, ys - 0.62, 'choque externo: a hegemonia\ndo automóvel, da motocicleta\ne do aplicativo (Capítulo 2)', 7.2,
                alinhar='left', ancora='topo', cor_texto=FRACA, entrelinha=1.35)
    ajustar(fig, ax, margem=0.3)
    salvar(fig, 'tese-cap3-03-circulo-vicioso-escassez')


@figura_tese
def c3_07_circulo_renda_motorizacao():
    """Figura (r39, 09/10/2026) — o círculo vicioso na versão da engenharia de transportes:
    renda e motorização (Ortúzar; Willumsen, 2011), no mesmo desenho da figura da lógica da escassez."""
    from diagramas import tela, no, seta, ajustar, bloco_texto
    fig, ax = tela(16.0, 12.0)
    R, G, RC = 1.95, 0.14, 0.9
    P = {'ren': (8.0, -2.0), 'dem': (12.8, -5.9), 'ofe': (8.0, -9.8), 'atr': (3.2, -5.9)}
    TXT = {
        'ren': (['Mais renda,', 'mais automóveis'], ['a renda cresce e', 'a posse de automóvel', 'aumenta']),
        'dem': (['Queda da demanda'], ['quem passa a ter', 'automóvel deixa', 'o transporte público']),
        'ofe': (['Menos frequência', 'ou tarifa maior'], ['o operador corta', 'oferta ou repassa', 'o custo à tarifa']),
        'atr': (['Transporte público', 'menos atraente'], ['espera maior e', 'viagem mais cara', 'empurram para', 'o automóvel']),
    }
    for k, (x, y) in P.items():
        ent = k == 'ren'
        tit, sub = TXT[k]
        txt = '\n'.join([f'**{l}**' for l in tit] + [f'//{l}//' for l in sub])
        no(ax, x, y, R, txt, tamanho=8.5, entrelinha=1.4,
           fundo=cor('grafite', 700) if ent else cor('grafite', 200),
           cor_texto='#FFFFFF' if ent else TINTA, cor_negrito='#FFFFFF' if ent else TINTA,
           cor_secundaria=cor('grafite', 200) if ent else TINTA2, escala_secundaria=0.84)
    (xr, yr), (xd, yd), (xo, yo), (xa, ya) = P['ren'], P['dem'], P['ofe'], P['atr']
    seta(ax, [(xr + R + G, yr), (xd, yr), (xd, yd + R + G)], raio=RC)
    seta(ax, [(xd, yd - R - G), (xd, yo), (xo + R + G, yo)], raio=RC)
    seta(ax, [(xo - R - G, yo), (xa, yo), (xa, ya - R - G)], raio=RC)
    seta(ax, [(xa, ya + R + G), (xa, yr), (xr - R - G, yr)], raio=RC)
    bloco_texto(ax, 8.0, -5.9, 'renda e motorização:\ncada volta torna o\nautomóvel mais vantajoso', 8,
                cor_texto=FRACA, entrelinha=1.4)
    # r102 (comentário #94 da orientadora, 11/11/2026): a ressalva dos autores entra no diagrama como freio
    # que age na queda da demanda (seta tracejada, mesma gramática do choque externo da figura da escassez)
    import math
    a = math.radians(-22); px, py = xd + (R + G) * math.cos(a), yd + (R + G) * math.sin(a)
    x0 = 15.45
    seta(ax, [(x0, yo - 0.55), (x0, py), (px, py)], raio=0.5, cor_traco=cor('grafite', 500), espessura=1.4)
    ax.patches[-1].set_linestyle((0, (3, 2)))
    bloco_texto(ax, x0 + 0.1, yo - 0.72, '**freio (ressalva dos autores)**\nnos países em desenvolvimento,\n'
                'o crescimento da população\nsustenta a demanda por mais\ntempo, e o círculo é menos\nautomático', 7.2,
                alinhar='right', ancora='topo', cor_texto=FRACA, cor_negrito=TINTA2, entrelinha=1.35)
    ajustar(fig, ax, margem=0.3)
    salvar(fig, 'tese-cap3-07-circulo-renda-motorizacao')


@figura_tese
def c3_04_tarifa_real_diesel():
    """Gráfico (Análise IX) — tarifa de ônibus e diesel em R$ de 2024."""
    t = pd.read_csv(D / 'Base Municipal v3' / 'painel_tarifa_onibus_1995_2024.csv')
    d = pd.read_csv(D / 'Base Municipal v3' / 'diesel_anp_real_2004_2024.csv')
    fig, ax = figura(6.8)
    e = t[t.ano <= 2005]; o = t[t.ano >= 2005]
    DIE = cor('grafite', 800)
    ax.plot(e.ano, e.tarifa_real_2024, color=TZ, lw=1.8, ls=(0, (3, 2)), marker='o', ms=3, mfc='white')
    ax.plot(o.ano, o.tarifa_real_2024, color=TZ, lw=1.8, marker='o', ms=3)
    ax.plot(d.ano, d['preco_diesel_real_2024_R$_litro'], color=DIE, lw=1.6, marker='s', ms=2.6)
    for yr in (2005, 2024):
        v = float(t.loc[t.ano == yr, 'tarifa_real_2024'].iloc[0])
        ax.annotate(br(v + 1e-6, 2), (yr, v), xytext=(0, -12) if yr == 2005 else (0, 6), textcoords='offset points',
                    ha='center', fontsize=7, color=TZ_TXT)
    ax.set_ylabel('R$ de 2024 (IPCA)'); ax.set_xlim(1994.5, 2024.5); ax.set_ylim(0, 8)
    ax.set_xticks(range(1995, 2025, 5), [str(v) for v in range(1995, 2025, 5)]); fmt_eixo(ax, 'y', 0); barra_v(ax)
    legenda_topo(fig, [linha('Tarifa de ônibus, 1995–2004 (estimada)', TZ, ls=(0, (3, 2)), marker='o', ms=3, mfc='white'),
                       linha('Tarifa de ônibus, 2005–2024 (mediana observada)', TZ, marker='o', ms=3),
                       linha('Diesel, R$ por litro (ANP)', DIE, marker='s', ms=2.6)], ncol=2)
    salvar(fig, 'tese-cap3-04-tarifa-real-diesel')


CAPITAIS = ['Brasília', 'Goiânia', 'Manaus', 'São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Curitiba', 'Porto Alegre',
            'Salvador', 'Recife', 'Fortaleza', 'Natal', 'Teresina', 'Cuiabá', 'Campo Grande', 'Florianópolis', 'Vitória',
            'Macapá', 'Palmas', 'Boa Vista']


@figura_tese
def c3_05_subsidio_regiao():
    """Gráfico (Análise X) — subsídio público em % do custeio, por região (NTU, 2025).
    Mesma seleção e mesmo sorteio (semente 7) da r18."""
    s = pd.read_csv(D / 'Base Municipal v3' / 'serie_subsidio_ntu.csv')
    s = s[(s.ano == 2025) & ~((s.cidade_ntu == 'Curitiba') & (s.escopo == 'RM'))]
    s = s.merge(base3()[['cod_ibge', 'reg']], on='cod_ibge', how='left')
    fig, ax = figura(7.6)
    ordem = ['Centro-Oeste', 'Norte', 'Sudeste', 'Sul', 'Nordeste']
    rng = np.random.default_rng(7); PT = cor('grafite', 800)
    OFF = {'Brasília': (6, 8), 'Goiânia': (-6, 8), 'Araucária': (-10, 8), 'Toledo': (10, -11), 'Manaus': (0, 8), 'São Paulo': (0, 8),
           'Campina Grande': (-4, 8), 'Natal': (2, -11), 'Salvador': (14, 8), 'Linhares': (0, 8)}
    for i, r_ in enumerate(ordem):
        x = s[s.reg == r_].sort_values('pct_subsidio'); jit = rng.uniform(-0.18, 0.18, len(x))
        cap = x.cidade_ntu.isin(CAPITAIS).values
        ax.scatter(x.pct_subsidio[~cap], i + jit[~cap], s=16, color='white', edgecolor=PT, lw=0.9, zorder=3)
        ax.scatter(x.pct_subsidio[cap], i + jit[cap], s=20, color=PT, zorder=3)
        med = x.pct_subsidio.median(); ax.plot([med, med], [i - 0.32, i + 0.32], color=TZ, lw=2.2, zorder=4)
        ax.text(101, i, f'n = {len(x)} · mediana {br(med)}%', va='center', fontsize=6.5, color=TINTA2)
        for _, rr in x[x.cidade_ntu.isin(list(OFF))].iterrows():
            dx, dy = OFF[rr.cidade_ntu]
            ax.annotate(rr.cidade_ntu, (rr.pct_subsidio, i), textcoords='offset points', xytext=(dx, dy), ha='center', fontsize=6, color=FRACA)
    m = s.pct_subsidio.mean()
    ax.axvline(m, color=FRACA, lw=0.8, ls=(0, (3, 2))); ax.text(m + 1, -0.62, f'média geral {br(m)}%', fontsize=6.5, color=FRACA)
    ax.set_yticks(range(len(ordem)), ordem); ax.set_xlim(-2, 100); ax.set_ylim(len(ordem) - 0.5, -0.9)
    ax.set_xlabel('subsídio público, em % do custeio do sistema (2025)'); barra_h(ax); fmt_eixo(ax, 'x', 0, '%')
    legenda_topo(fig, [Line2D([], [], marker='o', ls='', color=PT, ms=5, label='capital'),
                       Line2D([], [], marker='o', ls='', mfc='white', mec=PT, ms=5, label='demais municípios'),
                       linha('mediana da região', TZ)])
    salvar(fig, 'tese-cap3-05-subsidio-regiao')


@figura_tese
def c3_06_regime_prestacao_porte():
    """Gráfico (Análise XI) — regime de prestação e isenção para toda a população, MUNIC 2020."""
    f = pd.read_csv(D / 'Analises_Cap3' / 'munic2020_regime_por_faixa.csv').set_index('recorte')
    fx = ['até 20 mil', '20 a 100 mil', 'acima de 100 mil']
    fig, ax = figura(7.0)
    x = np.arange(3); w = 0.26
    SER = [('concessao', 'Concessão', cor('azul', 700)), ('prestacao_direta', 'Prestação direta pela prefeitura', cor('verde', 700)),  # r80: público no verde da família arranjo
           ('isencao_toda_populacao', 'Isenção para toda a população', TZ)]
    for i, (c, lab, co) in enumerate(SER):
        v = (f.loc[fx, c] / f.loc[fx, 'municipios_com_onibus'] * 100).values
        ax.bar(x + (i - 1) * w, v, w * 0.92, color=co)
        for xi, vi, n in zip(x + (i - 1) * w, v, f.loc[fx, c].values):
            ax.annotate(f'{br(vi)}%\n({br(n)})', (xi, vi), xytext=(0, 2), textcoords='offset points', ha='center', va='bottom',
                        fontsize=6.5, color=TINTA2, linespacing=1.15)
    ax.set_xticks(x, [f'{a}\n{br(n)} com ônibus' for a, n in zip(fx, f.loc[fx, 'municipios_com_onibus'])])
    ax.set_ylabel('% dos municípios com ônibus intramunicipal'); ax.set_ylim(0, 100); fmt_eixo(ax, 'y', 0); barra_v(ax)
    legenda_topo(fig, [chapa(l, c) for _, l, c in SER])
    salvar(fig, 'tese-cap3-06-regime-prestacao-porte')


# ═════════════════════════════════════════════════════════════════════════
# CAPÍTULO 4
# ═════════════════════════════════════════════════════════════════════════
@figura_tese
def c4_01_regua_descritiva():
    """Figura — a régua descritiva (esquema de 18/09/2026, A.1.4): contínuo, piso e camadas.
    Mesmo conteúdo da r18; 1b grafado "cadastro aberto", como no Mapa 3 e no texto."""
    from diagramas import tela, bloco_texto, ajustar
    from matplotlib.patches import Rectangle, FancyArrowPatch
    fig, ax = tela(16.0, 11.0)
    X0, X1 = 0.3, 15.7
    def caixa(x, y, w, h, fc, ec='none', lw=0):
        ax.add_patch(Rectangle((x, y - h), w, h, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=2, clip_on=False))
    def texto(x, y, t, tam=8, **kw):
        return bloco_texto(ax, x, y, t, tam, **kw)
    # contínuo
    texto(X0, 0, '**CONTÍNUO DE GRATUIDADE**', 7.5, alinhar='left', ancora='topo', cor_texto=FRACA, cor_negrito=FRACA)
    ax.add_patch(FancyArrowPatch((X1, -0.95), (X0, -0.95), arrowstyle='-|>,head_length=0.5,head_width=0.35',
                                 mutation_scale=9, lw=1.1, color=FRACA, clip_on=False))
    texto(X0, -1.2, 'gratuito para todos', 7.2, alinhar='left', ancora='topo', cor_texto=FRACA)
    texto(X1, -1.2, 'tarifado', 7.2, alinhar='right', ancora='topo', cor_texto=FRACA)
    yb, hb = -1.8, 1.75
    BOX = [(X0, 5.3, TZ, '#FFFFFF', 'Tarifa Zero', 'sem pagamento no embarque;\ncamadas abaixo'),
           (5.85, 3.15, cor('grafite', 300), TINTA, 'Gratuidades legais', 'estudantes, PcD e\noutros grupos'),
           (9.25, 3.15, cor('grafite', 200), TINTA, 'Subsídio', 'tarifa social, aporte\nque reduz o preço'),
           (12.55, 3.15, cor('grafite', 100), TINTA, 'Modelo tarifado', 'usuário paga o custo\npela tarifa')]
    for x, w, fc, tc, tit, sub in BOX:
        caixa(x, yb, w, hb, fc)
        texto(x + w / 2, yb - hb / 2, f'**{tit}**\n' + '\n'.join(f'//{l}//' for l in sub.split('\n')), 8.5,
              cor_texto=tc, cor_negrito=tc, cor_secundaria=tc, escala_secundaria=0.85, entrelinha=1.35)
    # piso
    ax.plot([X0, X1], [-3.95, -3.95], color=TINTA, lw=1.2, solid_capstyle='butt')
    texto(X0, -4.25, '**PISO** — gratuidade aos maiores de 65 anos (CF, art. 230, § 2º; Lei 10.741/2003, art. 39) e, desde 2024, no dia de votação\n'
                     '(ADPF 1013), válidas em todo sistema urbano. É ponto de partida comum, não camada.', 7.3,
          alinhar='left', ancora='topo', cor_texto=TINTA2, entrelinha=1.45)
    texto(X0, -5.55, '**Há alguma condição para viajar sem pagar?**', 9, alinhar='left', ancora='topo')
    # camadas
    yp, hp, wp = -6.15, 3.55, 7.55
    PAIN = [(X0, cor('rosa', 200), cor('rosa', 500), '**1 · UNIVERSAL** — sem portão, ou com portão anotado',
             [('1a', 'ausência\nde portão', cor('rosa', 500), '#FFFFFF'), ('1b', 'cadastro\naberto', cor('rosa', 800), '#FFFFFF'),
              ('1c', 'residência', cor('rosa', 300), TINTA), ('1d', 'prazo\ndeclarado,\nvigente', cor('rosa', 600), '#FFFFFF')]),
            # r79: camada 2 na família âmbar (matiz = camada, tom = subtipo)
            (X1 - wp, cor('ambar', 100), cor('ambar', 400), '**2 · PARCIAL** — há portão que restringe o acesso',
             [('2a', 'grupo\nsocial', cor('ambar', 700), '#FFFFFF'), ('2b', 'espaço\nou linha', cor('ambar', 500), TINTA),
              ('2c', 'dias da\nsemana', cor('ambar', 300), TINTA), ('2d', 'eventos', cor('ambar', 800), '#FFFFFF'),
              ('2e', 'finalidade', cor('ambar', 600), '#FFFFFF')])]
    for x, fc, ec, tit, subs in PAIN:
        caixa(x, yp, wp, hp, fc, ec, 1.0)
        texto(x + wp / 2, yp - 0.32, tit, 7.8, ancora='topo')
        pad, gap = 0.2, 0.15; nn = len(subs); ws = (wp - 2 * pad - (nn - 1) * gap) / nn
        for i, (k, t, sfc, stc) in enumerate(subs):
            sx = x + pad + i * (ws + gap); sy = yp - 0.95
            caixa(sx, sy, ws, 2.35, sfc)
            texto(sx + ws / 2, sy - 0.48, f'**{k}**', 9, ancora='topo', cor_texto=stc, cor_negrito=stc)
            texto(sx + ws / 2, sy - 1.45, t, 7, cor_texto=stc, entrelinha=1.3)
    texto(X0, yp - hp - 0.35, '**3 · ENCERRADAS** — políticas que terminaram, descritas por início, fim e motivação '
                              '(por desenho ou por trajetória)\ne pelo subtipo do último desenho antes do fim.', 7.3,
          alinhar='left', ancora='topo', cor_texto=FRACA, cor_negrito=FRACA, entrelinha=1.45)
    ajustar(fig, ax, margem=0.25)
    salvar(fig, 'tese-cap4-01-regua-descritiva')


# ═════════════════════════════════════════════════════════════════════════
# CAPÍTULO 5 — gráficos e mapas (retrato congelado de 01/10/2026)
# ═════════════════════════════════════════════════════════════════════════
RET = D / 'casos por fonte' / 'retratos' / os.environ.get('TZ_RETRATO', '2026-10-01')  # r56: TZ_RETRATO=2026-10-11 usa a base congelada


def retrato():
    if 'R' not in _cache:
        _cache['R'] = json.load(open(RET / 'retrato_cap5.json', encoding='utf-8'))
    return _cache['R']


@figura_tese
def c5_03_politicas_vigentes():
    """Gráfico — políticas vigentes no fim de cada ano e iniciadas no ano (retrato_cap5.json)."""
    R = retrato()
    vig = {int(k): int(v) for k, v in R['vigentes_por_ano'].items()}
    ini = {int(k): int(v) for k, v in R['inicio_por_ano_escopo'].items()}
    yrs = list(range(1990, 2027))
    fig, ax = figura(6.8)
    ax.bar(yrs, [ini.get(y, 0) for y in yrs], 0.72, color=cor('rosa', 300), zorder=2)
    ax.plot(yrs, [vig[y] for y in yrs], color=cor('rosa', 600), lw=1.9, zorder=3)
    for yv, rot in ((2013, 'junho de 2013'), (2020, 'pandemia')):
        ax.axvline(yv - 0.5, color=FRACA, lw=0.7, ls=(0, (2, 2)), zorder=1)
        ax.text(yv - 0.9, 188, rot, ha='right', va='top', fontsize=6.5, color=FRACA)
    for yv in (2012, 2019, 2022, 2026):
        ax.annotate(br(vig[yv]), (yv, vig[yv]), xytext=(-5, 3) if yv != 2026 else (0, 4), textcoords='offset points',
                    ha='right' if yv != 2026 else 'center', fontsize=7, color=cor('rosa', 600))
    ax.set_xlim(1989.4, 2026.6); ax.set_ylim(0, 195); ax.set_ylabel('nº de políticas municipais'); barra_v(ax)
    ax.set_xticks(range(1990, 2027, 5), [str(v) for v in range(1990, 2027, 5)])
    legenda_topo(fig, [linha('políticas vigentes no fim do ano', cor('rosa', 600)), chapa('políticas iniciadas no ano', cor('rosa', 300))])
    salvar(fig, 'tese-cap5-03-politicas-vigentes')


def _uf_geo():
    if 'uf' not in _cache:
        _cache['uf'] = json.load(open(D / 'espacial' / 'BR_UF_2022_simplificado.geojson', encoding='utf-8'))
    return _cache['uf']


def mapa_base(ax, ylim=(-34.2, 5.6)):
    for f in _uf_geo()['features']:
        g = f['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys:
            ax.add_patch(Polygon(np.array(poly[0]), closed=True, facecolor=cor('grafite', 100), edgecolor='#FFFFFF', lw=0.6, zorder=0))
    ax.set_xlim(-74.2, -34.4); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.axis('off')


def tam_pop(pop):
    """Área do marcador ∝ população (raiz), a mesma régua em todos os mapas."""
    return 4 + 140 * np.sqrt(pd.to_numeric(pop, errors='coerce').fillna(5000) / 360000)


def legenda_pop(ax, loc='lower right', bbox=None):
    hs = [ax.scatter([], [], s=tam_pop(pd.Series([p])).iloc[0], color=cor('grafite', 300), edgecolor='white', lw=0.4)
          for p in (10000, 50000, 300000)]
    return ax.legend(hs, ['10 mil hab.', '50 mil hab.', '300 mil hab.'], loc=loc, bbox_to_anchor=bbox, title='população (2022)',
                     title_fontsize=7, fontsize=7, labelspacing=1.1, frameon=False, alignment='left')


def pontos():
    if 'pts' not in _cache:
        _cache['pts'] = pd.read_csv(D / 'espacial' / 'pontos_representativos_municipios_2022.csv')
    return _cache['pts']


@figura_tese
def c5_04_mapa_camada1_periodo():
    """Mapa — camada 1 por período de início + encerradas. Mesma regra da r08/r18 (ano lido com
    pd.to_numeric; o que não é número puro conta como 'sem ano apurado')."""
    m = pd.read_excel(RET / 'Municípios TZ - consolidado.xlsx')
    m['cod'] = pd.to_numeric(m['Código IBGE'], errors='coerce'); m = m.merge(pontos(), left_on='cod', right_on='CD_MUN', how='left')
    c1 = m[(m['Situação'] == 'Ativa') & (m['Régua — aba'] == '1 Universal')].copy(); enc = m[m['Situação'] == 'Encerrada'].copy()
    ano = pd.to_numeric(c1['Ano início'].astype(str).str.extract(r'((?:19|20)\d\d)')[0], errors='coerce')  # r56: ano de quatro dígitos
    per = pd.cut(ano, [0, 2012, 2019, 2022, 2026], labels=['até 2012', '2013–2019', '2020–2022', '2023–2026'])
    c1['per'] = per.cat.add_categories('sem ano apurado').fillna('sem ano apurado')
    fig, ax = figura(14.2); mapa_base(ax)
    CL = {'até 2012': cor('rosa', 800), '2013–2019': cor('rosa', 600), '2020–2022': cor('rosa', 400),
          '2023–2026': cor('rosa', 300), 'sem ano apurado': cor('grafite', 500)}
    hs = []
    for k, co in CL.items():
        x = c1[c1.per == k]
        ax.scatter(x.lon, x.lat, s=tam_pop(x['População (2022)']), color=co, alpha=0.9, edgecolor='white', lw=0.35, zorder=3)
        hs.append(Line2D([], [], marker='o', ls='', color=co, ms=6, label=f'{k} ({len(x)})'))
    ax.scatter(enc.lon, enc.lat, s=tam_pop(enc['População (2022)']), facecolor='none', edgecolor=TINTA, lw=0.8, zorder=4)
    hs.append(Line2D([], [], marker='o', ls='', mfc='none', mec=TINTA, ms=6, label=f'encerradas ({len(enc)})'))
    l1 = ax.legend(handles=hs, loc='lower left', title='início da política (camada 1)', title_fontsize=7, fontsize=7,
                   frameon=False, alignment='left')
    ax.add_artist(l1); legenda_pop(ax)
    salvar(fig, 'tese-cap5-04-mapa-camada1-periodo')


@figura_tese
def c5_05_adocao_porte():
    """Gráfico — % com TZ universal (camada 1) por porte, com denominador (retrato_cap5.json)."""
    dp = retrato()['denominador_por_porte']; labs = list(dp)
    fig, ax = figura(6.8)
    x = np.arange(len(labs)); w = 0.38
    t_all = [dp[k]['tz_ativas'] / dp[k]['municipios'] * 100 for k in labs]
    t_idx = [dp[k]['tz_entre_idx5'] / dp[k]['indice_ge5'] * 100 for k in labs]
    ax.bar(x - w / 2, t_all, w * 0.92, color=cor('rosa', 300), zorder=2)
    ax.bar(x + w / 2, t_idx, w * 0.92, color=cor('rosa', 600), zorder=2)
    for xs, vs, num, den in ((x - w / 2, t_all, 'tz_ativas', 'municipios'), (x + w / 2, t_idx, 'tz_entre_idx5', 'indice_ge5')):
        for xi, v, k in zip(xs, vs, labs):
            ax.annotate(f"{br(v, 1)}%\n{dp[k][num]}/{br(dp[k][den])}", (xi, v), xytext=(0, 2), textcoords='offset points',
                        ha='center', va='bottom', fontsize=6.3, color=TINTA2, linespacing=1.15)
    ax.set_xticks(x, [k.replace('acima de ', '> ').replace('até ', '≤ ') for k in labs])
    ax.set_xlabel('população (Censo 2022)'); ax.set_ylabel('% com Tarifa Zero universal (camada 1)')
    ax.set_ylim(0, 20); fmt_eixo(ax, 'y', 0); barra_v(ax)
    legenda_topo(fig, [chapa('entre todos os municípios da faixa', cor('rosa', 300)),
                       chapa('entre os que têm indício de sistema de ônibus (índice ≥ 5)', cor('rosa', 600))])
    salvar(fig, 'tese-cap5-05-adocao-porte')


def _norm(t):
    return re.sub(r'[^A-Z]', '', unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode().upper())


def _regua_pontos():
    pts = pontos().copy(); pts['k'] = pts.NM_MUN.map(_norm) + '|' + pts.SIGLA_UF
    pts = pts.merge(base3()[['cod_ibge', 'pop_2022']], left_on='CD_MUN', right_on='cod_ibge', how='left')
    P = pts.set_index('k')
    TIP = RET / 'Tipologias TZ - consolidado.xlsx'
    out = {}
    for nome, aba in (('u1', '1 Universal'), ('u2', '2 Parcial'), ('u3', '3 Encerradas')):
        u = pd.read_excel(TIP, sheet_name=aba); u['k'] = u['Município'].map(_norm) + '|' + u.UF.str.strip(); out[nome] = u
    return P, out


@figura_tese
def c5_06_mapa_regua_camada1():
    """Mapa — camada 1 por subtipo + encerradas (planilha de tipologias, retrato de 01/10/2026)."""
    P, U_ = _regua_pontos(); u1, u3 = U_['u1'].copy(), U_['u3']
    u1['Subtipo'] = u1['Subtipo'].fillna('em verificação')
    fig, ax = figura(14.2); mapa_base(ax)
    hs = []
    x = u1[u1.Subtipo == 'em verificação'].merge(P, left_on='k', right_index=True)
    ax.scatter(x.lon, x.lat, s=tam_pop(x.pop_2022), facecolor='white', edgecolor=cor('grafite', 500), lw=0.7, zorder=2)
    hs.append(Line2D([], [], marker='o', ls='', mfc='white', mec=cor('grafite', 500), ms=6, label=f'subtipo em verificação ({len(x)})'))
    CL = [('1a', 'sem portão (1a)', cor('rosa', 500)), ('1b', 'cadastro aberto (1b)', cor('azul', 700)),
          ('1c', 'portão de residência (1c)', cor('verde', 700)), ('1d', 'prazo declarado (1d)', cor('amarelo', 500))]
    for k, lab, c in CL:
        x = u1[u1.Subtipo == k].merge(P, left_on='k', right_index=True)
        ax.scatter(x.lon, x.lat, s=tam_pop(x.pop_2022), color=c, alpha=0.92, edgecolor='white', lw=0.4, zorder=3)
        hs.append(Line2D([], [], marker='o', ls='', color=c, ms=6, label=f'{lab} ({len(x)})'))
    x = u3.merge(P, left_on='k', right_index=True)
    ax.scatter(x.lon, x.lat, s=26, marker='X', color=TINTA, lw=0, zorder=4)
    hs.append(Line2D([], [], marker='X', ls='', color=TINTA, ms=6, label=f'encerrada ({len(x)})'))
    l1 = ax.legend(handles=hs, loc='lower left', title='camada 1 · universal', title_fontsize=7, fontsize=7, frameon=False, alignment='left')
    ax.add_artist(l1); legenda_pop(ax)
    salvar(fig, 'tese-cap5-06-mapa-regua-camada1')


@figura_tese
def c5_07_mapa_regua_camada2():
    """Mapa — camada 2 (arranjos parciais) em quatro painéis, um por subtipo."""
    P, U_ = _regua_pontos(); u2 = U_['u2']
    # A.1.7, item 5 (06/10/2026): a gratuidade eleitoral é piso ou trajetória, não camada. No retrato
    # de 01/10 ela ainda estava na 2d; sai pela coluna "Regime da 2d" (fica só o evento não eleitoral).
    reg = [c for c in u2.columns if c.startswith('Regime da 2d')]
    if reg:
        r = u2[reg[0]].astype(str)
        u2 = u2[~((u2.Subtipo.astype(str) == '2d') & ~r.str.contains('não eleitoral', regex=False))]
    C2 = [('2a', 'grupo social (2a)'), ('2b', 'espaço ou linha (2b)'), ('2c', 'dias da semana (2c)'), ('2d', 'eventos (2d)')]
    if u2.Subtipo.astype(str).str.contains('2e', regex=False).any():   # r56: 2e (finalidade, A.1.12, 08/10/2026) ganha painel
        C2.append(('2e', 'finalidade (2e)'))
        fig, axs = figura(11.6, ncols=3, nrows=2); axs.flat[-1].axis('off')
    else:
        fig, axs = figura(13.6, ncols=2, nrows=2)
    for ax, (k, lab) in zip(axs.flat, C2):
        mapa_base(ax)
        x = u2[u2.Subtipo.astype(str).str.contains(k, regex=False)].drop_duplicates('k').merge(P, left_on='k', right_index=True)  # A.1.15
        ax.scatter(x.lon, x.lat, s=tam_pop(x.pop_2022) * 0.45, color=TZ, alpha=0.9, edgecolor='white', lw=0.35, zorder=3)
        ax.set_title(f'{lab} · {len(x)} município' + ('s' if len(x) != 1 else ''), fontsize=8)
    hs = [Line2D([], [], marker='o', ls='', color=cor('grafite', 300), mec='white',
                 ms=float(np.sqrt(tam_pop(pd.Series([p])).iloc[0] * 0.45)), label=l)
          for p, l in ((10000, '10 mil hab.'), (50000, '50 mil hab.'), (300000, '300 mil hab.'))]
    legenda_topo(fig, [Line2D([], [], ls='', label='população (2022):')] + hs)
    salvar(fig, 'tese-cap5-07-mapa-regua-camada2')


# ═════════════════════════════════════════════════════════════════════════
# REVISÃO SISTEMÁTICA (Cap. 5 e Apêndice B) — dados e regras de
# rede_bibliometrica.py e panorama_rsl.py (importados, não copiados)
# ═════════════════════════════════════════════════════════════════════════
def _rb():
    if 'rb' not in _cache:
        sys.path.insert(0, str(U / '_meta' / 'scripts'))
        import importlib
        rb = importlib.import_module('rede_bibliometrica')
        nos_acervo, ar = rb.ler()
        nos = rb.filtra_corpus81(nos_acervo)
        assert len(nos) == 81, len(nos)
        ar81 = [r for r in ar if not (r['tipo'] == 'interno' and (r['origem'] not in nos or r['destino'] not in nos))]
        _cache['rb'] = (rb, nos_acervo, nos, ar81)
    return _cache['rb']


CASO = {'empirico': ('cita caso(s) concreto(s)', TZ), 'teorico': ('teórico / conceitual', cor('grafite', 500))}
ANO_PARCIAL = 2026


def _ticks_anos(anos):
    t = [a for a in anos if a % 5 == 0 and a - anos[0] >= 3 and anos[-1] - a >= 3]
    return [anos[0]] + t + [anos[-1]]


NOTA_PARCIAL = Line2D([], [], ls='', label=f'* {2026}: ano parcial (até a busca, set./2026)')


def _barras_ano(ax, cont, cats, cores, anos, rot_parcial=True, rotulo_min=3):
    bottom = np.zeros(len(anos))
    for c in cats:
        v = np.array([cont.get((a, c), 0) for a in anos])
        ax.bar(anos, v, 0.66, bottom=bottom, color=cores[c], zorder=2, edgecolor='white', linewidth=0.3)
        for a, vv, b0 in zip(anos, v, bottom):
            if vv >= rotulo_min:
                ax.text(a, b0 + vv / 2, str(vv), ha='center', va='center', fontsize=5.6,
                        color='#FFFFFF' if cores[c] not in (cor('grafite', 300),) else TINTA)
        bottom += v
    ax.set_xlim(anos[0] - 0.7, anos[-1] + 0.7); barra_v(ax)
    ticks = _ticks_anos(anos)
    ax.set_xticks(ticks, [f'{a}*' if (a == ANO_PARCIAL and rot_parcial) else str(a) for a in ticks])
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    return bottom


@figura_tese
def c5_01_rsl_itens_ano():
    """Gráfico — itens do corpus (81) por ano de publicação, caso concreto × teórico (= Gráfico B.2)."""
    rb, _, nos, _ = _rb()
    import collections
    cont = collections.Counter((int(n['ano']), rb.classifica_caso(n)) for n in nos.values())
    anos_d = sorted({int(n['ano']) for n in nos.values()})
    anos = list(range(anos_d[0], max(anos_d[-1], ANO_PARCIAL) + 1))
    fig, ax = figura(6.4)
    _barras_ano(ax, cont, ['empirico', 'teorico'], {k: v[1] for k, v in CASO.items()}, anos)
    ax.set_ylabel('itens do corpus')
    lg = legenda_topo(fig, [chapa(v[0], v[1]) for v in CASO.values()] + [NOTA_PARCIAL])
    lg.get_texts()[-1].set_color(FRACA)
    salvar(fig, 'tese-cap5-01-rsl-itens-ano')


def _rede(color_of, legend_items, nome, ids_brancos=()):
    """Rede de citações internas do corpus, mesmo layout de rede_bibliometrica.svg_rede
    (Fruchterman-Reingold, semente 42; isolados em painel próprio), redesenhada no padrão:
    16 cm, rótulos de 6 pt, arestas finas."""
    rb, _, nos, ar81 = _rb()
    import collections, math
    from matplotlib.patches import Circle as C_, FancyArrowPatch as FA
    internas = [(r['origem'], r['destino']) for r in ar81 if r['tipo'] == 'interno']
    grau = collections.Counter()
    for a, b in internas: grau[a] += 1; grau[b] += 1
    todos = sorted(nos, key=int); con = [i for i in todos if grau[i] > 0]; iso = [i for i in todos if grau[i] == 0]
    W, M, HN = 780, 46, 450
    por_linha, passo = 30, 24
    linhas_iso = -(-len(iso) // por_linha) if iso else 0
    H = HN + (46 + linhas_iso * passo if iso else 0) + 8
    pr = rb.layout_forcas(con, internas, it=1100, seed=42)
    pr, (x0, x1, y0, y1) = rb.normalizar(pr)
    TOP = 30                                    # faixa da legenda
    P = {i: (M + (pr[i][0] - x0) / (x1 - x0) * (W - 2 * M), TOP + 14 + (1 - (pr[i][1] - y0) / (y1 - y0)) * (HN - TOP - 28)) for i in con}
    rai = {i: 5.5 + 1.7 * grau[i] for i in con}
    P = rb.resolve_sobreposicoes(P, rai, con, pad=3.0)
    PT = L * 72 / 2.54 / W                      # pt por px
    fig = plt.figure(figsize=(L * CM, H * PT / 72)); ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off'); fig._tela_exata = True
    for a, b in internas:
        if a in P and b in P:
            ax.add_patch(FA(P[a], P[b], arrowstyle='-|>,head_length=2.2,head_width=1.4', mutation_scale=1, lw=0.55,
                            color=cor('grafite', 300), shrinkA=rai[a] / PT * PT, shrinkB=rai[b] + 1, zorder=1))
    ordem = sorted(con, key=lambda i: (-grau[i], int(i)))
    ocup = [(P[i][0] - rai[i], P[i][1] - rai[i], P[i][0] + rai[i], P[i][1] + rai[i]) for i in ordem]
    ocup += [(-1e4, -1e4, 4, 1e4), (W - 4, -1e4, 1e4, 1e4), (-1e4, -1e4, 1e4, TOP)]   # bordas e faixa da legenda
    FS = 11.0                                   # px; folga de 10% para a largura da Poppins
    supr = []
    for i in ordem:
        x, y = P[i]; r = rai[i]; c = color_of(nos[i])
        dash = nos[i]['estado'] == 'a_receber'
        ax.add_patch(C_((x, y), r, facecolor=c, edgecolor=TINTA if dash else '#FFFFFF', lw=0.6, ls=(0, (2, 1)) if dash else '-', zorder=3))
        ax.text(x, y + 0.4, i, ha='center', va='center', fontsize=max(4.6, min(6.2, r * PT * 0.95)), fontweight='medium',
                color=TINTA if c in ids_brancos else '#FFFFFF', zorder=4)
    for i in ordem:
        x, y = P[i]; r = rai[i]
        nome_ = nos[i]['autores'].split(';')[0].strip('" ')[:24]
        t = f"{nome_} {nos[i]['ano']}"
        res = rb.posiciona_rotulo(x, y, r, t, FS * 1.1, ocup)
        if res:
            lx, ly, anc, fs = res
            ax.text(lx, ly, t, ha={'middle': 'center', 'start': 'left', 'end': 'right'}[anc], va='baseline',
                    fontsize=fs / 1.1 * PT, color=TINTA2, zorder=5)
        else:
            supr.append(i)
    if iso:
        yb = HN + 8
        ax.plot([M, W - M], [yb, yb], color=GRADE, lw=0.6)
        ax.text(M, yb + 18, f'Sem citação interna registrada ({len(iso)} itens): não citam nem são citados por outro item do corpus',
                fontsize=6.5, color=TINTA2, va='baseline')
        for k, i in enumerate(iso):
            rr, cc = divmod(k, por_linha)
            x = M + 9 + cc * passo; y = yb + 38 + rr * passo; c = color_of(nos[i])
            ax.add_patch(C_((x, y), 9, facecolor=c, edgecolor='#FFFFFF', lw=0.5, zorder=3))
            ax.text(x, y + 0.4, i, ha='center', va='center', fontsize=5, fontweight='medium',
                    color=TINTA if c in ids_brancos else '#FFFFFF', zorder=4)
    hs = [Line2D([], [], marker='o', ls='', color=c, ms=6, label=l) for l, c in legend_items]
    ax.legend(handles=hs, loc='upper left', bbox_to_anchor=(0, 1.0), ncol=len(hs), frameon=False, fontsize=7,
              handletextpad=0.3, columnspacing=1.2)
    _salvar(fig, OUT / f'{nome}.svg', png=True, auditar=False)
    print('  ok', nome, '| rótulos suprimidos por densidade:', ', '.join(sorted(supr, key=int)) or 'nenhum')
    return supr


@figura_tese
def c5_02_rsl_rede():
    """Figura — rede de citações internas do corpus, cor = caso concreto × teórico (= Figura B.2)."""
    rb, *_ = _rb()
    _rede(lambda n: CASO[rb.classifica_caso(n)][1], [(v[0], v[1]) for v in CASO.values()], 'tese-cap5-02-rsl-rede')


@figura_tese
def b_01_rsl_acervo_ano():
    """Gráfico B.1 — acervo (183 registros, qualquer desfecho) por ano de publicação."""
    _, acervo, _, _ = _rb()
    import collections
    cont = collections.Counter(int(r['ano']) for r in acervo.values() if (r.get('ano') or '').strip().isdigit())
    anos = list(range(min(cont), max(cont) + 1))
    fig, ax = figura(6.0)
    ax.bar(anos, [cont.get(a, 0) for a in anos], 0.66, color=cor('grafite', 700), zorder=2)
    ax.set_xlim(anos[0] - 0.7, anos[-1] + 0.7); barra_v(ax); ax.set_ylabel('registros')
    ticks = _ticks_anos(anos)
    ax.set_xticks(ticks, [str(a) for a in ticks]); ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    salvar(fig, 'tese-apB-01-rsl-acervo-ano')


@figura_tese
def b_02_rsl_funil():
    """Figura B.1 — funil de identificação: acervo → fichados → corpus (contas de panorama_rsl.fig_funil)."""
    from diagramas import tela, bloco_texto, ajustar, seta
    from matplotlib.patches import Rectangle
    _, acervo, nos, _ = _rb(); rows = list(acervo.values()); total = len(rows)
    proc = collections_counter(r.get('procedimento') or '(vazio)' for r in rows)
    outros = total - sum(proc.get(p, 0) for p in ('busca_de_base', 'bola_de_neve', 'enumeracao_de_volume'))
    est = collections_counter((r.get('estado') or '').strip() for r in rows)
    fich, exc, rec, ind = est.get('fichado', 0), est.get('excluido_apos_leitura', 0), est.get('reclassificado_db', 0), est.get('indisponivel', 0)
    n81 = len(nos); fora = fich - n81
    assert fich + exc + rec + ind == total and n81 == 81
    fig, ax = tela(16.0, 9.0)
    def caixa(x, y, w, h, fc, txt, tc=TINTA, tam=8.5, sec=None):
        ax.add_patch(Rectangle((x, y - h), w, h, facecolor=fc, edgecolor='none', zorder=2))
        bloco_texto(ax, x + w / 2, y - h / 2, txt, tam, cor_texto=tc, cor_negrito=tc, cor_secundaria=sec or tc,
                    escala_secundaria=0.86, entrelinha=1.4, largura_cm=w - 0.4)
    CX, CW, SX, SW = 0.3, 8.6, 9.7, 6.0
    caixa(CX, 0, CW, 1.9, cor('grafite', 200),
          f"**Identificados: {total} registros**\n//todo o acervo lido pela revisão, qualquer desfecho//\n"
          f"//busca em base {proc.get('busca_de_base', 0)} · bola de neve {proc.get('bola_de_neve', 0)} · "
          f"dossiês temáticos {proc.get('enumeracao_de_volume', 0)} · outros {outros}//", sec=TINTA2)
    caixa(CX, -2.7, CW, 1.5, cor('grafite', 200), f"**Fichados: {fich}**\n//texto lido e registrado, qualquer estrato//", sec=TINTA2)
    caixa(SX, -2.5, SW, 1.9, cor('grafite', 100),
          f"**Não seguem: {exc + rec + ind}**\n//excluídos com motivo registrado: {exc}//\n"
          f"//reclassificados para banco de dados: {rec}//\n//indisponível (acesso): {ind}//", tam=8, sec=TINTA2)
    caixa(CX, -5.0, CW, 1.9, TZ, f"**Corpus da revisão (RSL1–4): {n81} itens**\n//pertence a um dos 4 estratos declarados;//\n"
          f"//é a população citada no Cap. 5 e neste apêndice//", tc='#FFFFFF')
    caixa(SX, -5.1, SW, 1.7, cor('grafite', 100),
          f"**Fichado fora dos 4 estratos: {fora}**\n//bola de neve ou acervo prévio sem estrato;//\n//não entra na contagem do corpus//",
          tam=8, sec=TINTA2)
    xm = CX + CW / 2; G = 0.12
    seta(ax, [(xm, -1.9 - G), (xm, -2.7 + G)], raio=0, espessura=1.4)
    seta(ax, [(xm, -4.2 - G), (xm, -5.0 + G)], raio=0, espessura=1.4)
    seta(ax, [(CX + CW + G, -3.45), (SX - G, -3.45)], raio=0, espessura=1.4)
    seta(ax, [(CX + CW + G, -5.95), (SX - G, -5.95)], raio=0, espessura=1.4)
    ajustar(fig, ax, margem=0.25)
    salvar(fig, 'tese-apB-02-rsl-funil')


def collections_counter(it):
    import collections
    return collections.Counter(it)


SUP_TOP = [('artigo_periodico', 'artigo em periódico', cor('rosa', 500)), ('tese_dissertacao', 'tese ou dissertação', cor('azul', 700)),
           ('comunicacao_congresso', 'comunicação em congresso', cor('verde', 700))]


@figura_tese
def b_03_rsl_rede_suporte():
    """Figura B.3 — mesma rede, cor pelo suporte documental. Padrão: até 4 cores; os três suportes
    mais frequentes têm cor e os outros cinco (slides, relatório técnico, livro ou capítulo,
    documento institucional, outros) ficam em 'demais suportes'. A contagem fina está no
    Relatório da rede (gerado)."""
    rb, *_ = _rb()
    m = {k: c for k, _, c in SUP_TOP}; OUTRO = cor('grafite', 300)
    def c_of(n):
        s_ = rb.SUPORTE_ALIAS.get(rb.gsup(n), rb.gsup(n)); return m.get(s_, OUTRO)
    _rede(c_of, [(l, c) for _, l, c in SUP_TOP] + [('demais suportes', OUTRO)], 'tese-apB-03-rsl-rede-suporte', ids_brancos=(OUTRO,))


@figura_tese
def b_04_rsl_genero_ano():
    """Gráfico B.3 — itens por ano, por gênero textual fino. Nove categorias não cabem em cor
    (teto de 4): a figura vira pequenos múltiplos, uma faixa por gênero, mesma escala."""
    rb, _, nos, _ = _rb()
    import collections
    def gf(n):
        g = (n.get('genero') or '').strip() or 'outros_generos'
        return g if g in rb.GENERO_TOPO else 'outros_generos'
    cont = collections.Counter((int(n['ano']), gf(n)) for n in nos.values())
    tot = collections.Counter(gf(n) for n in nos.values())
    cats = [c for c in rb.GENERO_TOPO + ['outros_generos'] if tot[c]]      # gênero sem item no corpus não ganha faixa vazia
    anos_d = sorted({int(n['ano']) for n in nos.values()})
    anos = list(range(anos_d[0], max(anos_d[-1], ANO_PARCIAL) + 1))
    vmax = max(cont.values())
    fig, axs = figura(1.6 + 1.15 * len(cats), nrows=len(cats), sharex=True)
    for ax, c in zip(axs, cats):
        v = [cont.get((a, c), 0) for a in anos]
        ax.bar(anos, v, 0.66, color=cor('grafite', 700), zorder=2)
        ax.set_ylim(0, vmax + 1); ax.set_yticks([]); ax.spines['left'].set_visible(False); ax.grid(False)
        ax.text(anos[0] - 0.9, vmax * 0.35, f"{rb.ROT_GENERO.get(c, c)} ({tot[c]})", ha='right', va='center', fontsize=7, color=TINTA2)
        for a, vv in zip(anos, v):
            if vv: ax.text(a, vv + 0.2, str(vv), ha='center', va='bottom', fontsize=5.5, color=TINTA2)
        ax.tick_params(axis='x', length=0)
    ticks = _ticks_anos(anos)
    axs[-1].set_xticks(ticks, [f'{a}*' if a == ANO_PARCIAL else str(a) for a in ticks]); axs[-1].set_xlim(anos[0] - 0.7, anos[-1] + 0.7)
    lg = legenda_topo(fig, [NOTA_PARCIAL, Line2D([], [], ls='', label='"outros gêneros" agrupa as categorias menos frequentes do vocabulário fino')], ncol=1)
    for t in lg.get_texts(): t.set_color(FRACA)
    salvar(fig, 'tese-apB-04-rsl-genero-ano')


# ═════════════════════════════════════════════════════════════════════════
# APÊNDICE A
# ═════════════════════════════════════════════════════════════════════════
@figura_tese
def a_01_motorizacao_brasil():
    """Gráfico A.1 — taxa de motorização individual, Brasil, 2013–2025 (DENATRAN/IBGE)."""
    sr = pd.read_csv(D / 'DENATRAN' / 'serie_taxa_motorizacao_brasil_2013-2025.csv').set_index('ano')
    fig, ax = figura(7.0)
    ax.axvspan(2021, 2023, color=cor('grafite', 100), zorder=0, lw=0)
    ax.text(2022, 330, 'denominador:\nCenso 2022', ha='center', va='top', fontsize=6.5, color=FRACA, linespacing=1.2)
    for col, k, rot in (('auto_por_1000hab', 'auto', 'Automóvel'), ('moto_por_1000hab', 'moto', 'Motocicleta')):
        c = COR_MODO[k]; t = sr[col]
        for trecho, ls in (([2013, 2014, 2015, 2016, 2017, 2018, 2019, 2021], '-'), ([2021, 2022, 2023], (0, (3, 2))), ([2023, 2024, 2025], '-')):
            ax.plot(trecho, t[trecho], color=c, lw=1.8, ls=ls, zorder=3)
        ax.plot(t.index, t.values, 'o', color=c, ms=3.2, zorder=4)
        for a in (2013, 2021, 2025):
            ax.annotate(br(t[a]), (a, t[a]), textcoords='offset points', xytext=(0, 5), ha='center', va='bottom', fontsize=7, color=c)
        ax.annotate(rot, (2025, t[2025]), textcoords='offset points', xytext=(8, 0), ha='left', va='center', fontsize=7.5, color=c, fontweight='medium')
    ax.set_xlim(2012.5, 2027.4); ax.set_ylim(0, 345); fmt_eixo(ax, 'y', 0); barra_v(ax)
    anos = [a for a in range(2013, 2026) if a != 2020]
    ax.set_xticks(anos, [str(a) for a in anos], fontsize=7)
    ax.text(2020, 6, '2020\nsem dado', ha='center', va='bottom', fontsize=6.5, color=FRACA, linespacing=1.2)
    ax.spines['bottom'].set_bounds(2013, 2025); ax.set_ylabel('veículos por 1.000 habitantes')
    salvar(fig, 'tese-apA-01-motorizacao-brasil')


@figura_tese
def a_02_munic_tz():
    """Gráfico A.2 — MUNIC 2020: transporte coletivo organizado e concessão, TZ (ativa em 2020) × demais.
    Valores transcritos dos rótulos da versão de julho (MUNIC 2020 + Dataverse Santini v8): a
    figura não tem arquivo de dados no cofre. '*' = menos de 15 municípios TZ na faixa."""
    fx = ['< 20', '20–100', '100–250', '250–500', '> 500']
    dem1, tz1 = [19, 50, 88, 99, 100], [80, 95, 100, None, None]
    dem2, tz2 = [30, 59, 81, 85, 93], [6, 21, 100, None, None]
    sem_resp = ['75% sem resposta', '53% sem resposta', '0% sem resposta', '', '']
    pequeno = [False, False, True, False, False]
    fig, (a1, a2) = figura(7.8, ncols=2, sharey=True)
    x = np.arange(5); w = 0.38
    for ax, d, t, tit in ((a1, dem1, tz1, 'Com ônibus intramunicipal organizado (2020)'),
                          (a2, dem2, tz2, 'Entre os que têm ônibus: % com concessão (2020)')):
        ax.bar(x - w / 2, d, w, color=DEMAIS, zorder=2)
        for xi, v in zip(x - w / 2, d): ax.text(xi, v + 1.5, f'{v}', ha='center', va='bottom', fontsize=6.5, color=TINTA2)
        for i, v in enumerate(t):
            if v is None:
                ax.text(x[i] + w / 2, 2, 'sem\ncaso', ha='center', va='bottom', fontsize=6.3, color=FRACA, linespacing=1.15); continue
            ax.bar(x[i] + w / 2, v, w, zorder=2, color='#FFFFFF' if pequeno[i] else TZ, edgecolor=TZ, linewidth=1.1 if pequeno[i] else 0)
            ax.text(x[i] + w / 2, v + 1.5, f'{v}', ha='center', va='bottom', fontsize=6.5, color=FRACA if pequeno[i] else TINTA)
        ax.set_title(tit); ax.set_ylim(0, 118); barra_v(ax)
        ax.set_xticks(x, fx, fontsize=7)
    for ax in (a1, a2): ax.set_xlabel('mil habitantes')
    a1.set_ylabel('% dos municípios'); fmt_eixo(a1, 'y', 0)
    lg = legenda_topo(fig, [chapa('demais municípios', DEMAIS), chapa('Tarifa Zero (ativa em 2020)', TZ),
                            vazada('idem, menos de 15 municípios na faixa', TZ)], ncol=3)
    a2.text(0.02, 0.985, 'TZ sem resposta sobre a outorga: 75% (< 20 mil), 53% (20–100 mil), 0% (100–250 mil)',
            transform=a2.transAxes, ha='left', va='top', fontsize=6.3, color=FRACA)
    salvar(fig, 'tese-apA-02-munic-tz')


def _boxplot_tarifa(col, fonte_csv, nome, ylabel, ipca=False):
    d = pd.read_csv(D / 'Base Municipal v3' / fonte_csv)
    anos = sorted(d.ano.unique())
    dados = [d.loc[d.ano == a, col].dropna().values for a in anos]
    fig, ax = figura(8.0)
    for a0, a1, rot in ((2005, 2009, 'ANTP/SIMOB'), (2010, 2015, 'SIMU'), (2016, 2017, 'transição\nSIMU + PEMOB'), (2018, 2024, 'PEMOB')):
        ax.text((a0 + a1) / 2, 0.25, rot, ha='center', va='bottom', fontsize=6.3, color=FRACA, linespacing=1.15)
    for xv in (2009.5, 2015.5, 2017.5):
        ax.axvline(xv, color=EIXO, lw=0.7, ls=(0, (2, 2)), zorder=1)
    bp = ax.boxplot(dados, positions=anos, widths=0.56, patch_artist=True, showfliers=True,
                    boxprops=dict(facecolor=cor('grafite', 200), edgecolor=cor('grafite', 600), lw=0.7),
                    whiskerprops=dict(color=cor('grafite', 600), lw=0.7), capprops=dict(color=cor('grafite', 600), lw=0.7),
                    medianprops=dict(color=cor('grafite', 800), lw=1.8),
                    flierprops=dict(marker='o', ms=2.2, mfc=cor('grafite', 500), mec='none'), zorder=2)
    for a, v in zip(anos, dados):
        ax.text(a, 7.85, f'n={len(v)}', ha='center', va='top', fontsize=5.6, color=FRACA)
    hs = [Line2D([], [], color=cor('grafite', 800), lw=1.8, label='mediana do ano (caixa: quartis; hastes: 1,5 × intervalo interquartil)')]
    if ipca:
        t = pd.read_csv(D / 'Base Municipal v3' / 'tarifa_corrigida_ipca_2005_2024.csv')
        ax.plot(t.ano, t.tarifa_corrigida_ipca, color=TZ, lw=1.8, marker='o', ms=3, zorder=4)
        hs.append(linha('trajetória se corrigida só pelo IPCA (base: mediana de 2005)', TZ, marker='o', ms=3))
    ax.set_xlim(2004.4, 2024.6); ax.set_ylim(0, 8); ax.set_ylabel(ylabel); fmt_eixo(ax, 'y', 0); barra_v(ax)
    ax.set_xticks(anos, [str(a) for a in anos], fontsize=6.6)
    legenda_topo(fig, hs, ncol=1)
    salvar(fig, nome)


@figura_tese
def a_04_tarifa_real_boxplot():
    """Gráfico A.4 — tarifa de ônibus nos municípios pesquisados, R$ de 2024 (IPCA), 2005–2024."""
    _boxplot_tarifa('valor_real_2024', 'serie_tarifa_real_2024.csv', 'tese-apA-04-tarifa-real-boxplot', 'tarifa, R$ de 2024 (IPCA)')


@figura_tese
def a_05_tarifa_nominal_boxplot():
    """Gráfico A.5 — tarifa em valores correntes, com a trajetória de correção pelo IPCA."""
    _boxplot_tarifa('valor', 'serie_tarifa_dedup_2005_2024.csv', 'tese-apA-05-tarifa-nominal-boxplot', 'tarifa, R$ correntes', ipca=True)


# ═════════════════════════════════════════════════════════════════════════
# r40 (11/10/2026) — fluxo da reestimativa e comparação das listas
# ═════════════════════════════════════════════════════════════════════════
def _deteccao():
    """Detectores de cada política em escopo (base-mestre; Situação Ativa ou Encerrada).
    S = Santini (Dataverse, qualquer versão, ou planilha de set./2026); N = NTU (casos nomeados, 2024–2026);
    O = outros levantamentos (Brinco 2017, Santini 2019, Vermander 2021, Angelo 2023, Fernandes Pereira et al. 2023,
    UnB/Geourb 2025); M = MUNIC 2020 (isenção a toda a população); L = literatura da revisão sistemática."""
    import openpyxl
    base = D / 'casos por fonte'
    wb = openpyxl.load_workbook(base / 'Municípios TZ - consolidado.xlsx', read_only=True, data_only=True)
    rows = [r for r in list(wb['consolidado'].iter_rows(values_only=True))[1:] if r[0] and r[3] in ('Ativa', 'Encerrada')]
    out = []
    for r in rows:
        s81 = str(r[81] or '')
        m = re.search(r'RSL: (\d+) fichamento', str(r[83] or ''))
        out.append(dict(
            S=(r[76] is not None) or ('Santini' in s81),
            N=any(k in s81 for k in ('NTU (2024)', 'NTU (2025)', 'NTU (2026)')),
            O=any(k in s81 for k in ('Fernandes Pereira', 'Brinco', 'Angelo (2023)', 'Vermander', 'UnB/Geourb', 'Santini (2019)')),
            M=str(r[69]).startswith('Sim'),
            L=bool(m and int(m.group(1)) > 0)))
    return out


@figura_tese
def c5_08_upset_fontes():
    """Figura (r40) — em quais listas cada política da base aparece (gráfico de interseções).
    Contas de _deteccao(); retrato da base-mestre no momento da execução."""
    from collections import Counter
    from matplotlib.patches import Rectangle
    det = _deteccao(); n = len(det)
    K = ['S', 'N', 'O', 'M', 'L']
    NOME = {'S': 'Santini (Dataverse e planilha)', 'N': 'NTU (casos nomeados, 2024–2026)',
            'O': 'outros levantamentos (2017–2025)', 'M': 'MUNIC 2020 (autodeclaração)', 'L': 'literatura (revisão sistemática)'}
    comb = Counter(tuple(k for k in K if d[k]) for d in det)
    itens = sorted(comb.items(), key=lambda kv: (-kv[1], len(kv[0])))
    tot = {k: sum(d[k] for d in det) for k in K}
    fig = plt.figure(figsize=(L * CM, 9.2 * CM))
    gs = fig.add_gridspec(2, 1, height_ratios=[2.0, 1.45], hspace=0.06, left=0.36, right=0.99, top=0.9, bottom=0.03)
    axb = fig.add_subplot(gs[0]); axm = fig.add_subplot(gs[1], sharex=axb)
    xs = np.arange(len(itens))
    C3, C12 = cor('grafite', 800), cor('grafite', 400)
    for x, (c, v) in zip(xs, itens):
        cc = TZ if len(c) == 0 else (C3 if len(c) >= 3 else C12)
        axb.bar(x, v, width=0.66, color=cc, zorder=2)
        axb.text(x, v + 1, br(v), ha='center', va='bottom', fontsize=6.6, color=TINTA2)
    axb.set_ylabel('políticas'); barra_v(axb); axb.tick_params(axis='x', bottom=False, labelbottom=False)
    axb.set_ylim(0, max(v for _, v in itens) * 1.12)
    for sp in ('top', 'right'): axb.spines[sp].set_visible(False)
    ys = {k: i for i, k in enumerate(reversed(K))}
    for x, (c, _) in zip(xs, itens):
        for k in K:
            axm.plot(x, ys[k], 'o', ms=5.0, color=(C3 if k in c else cor('grafite', 100)), zorder=3)
        if len(c) > 1:
            yy = [ys[k] for k in c]; axm.plot([x, x], [min(yy), max(yy)], color=C3, lw=1.4, zorder=2)
    axm.set_yticks([ys[k] for k in K], [f'{NOME[k]} · {br(tot[k])}' for k in K], fontsize=7)
    axm.tick_params(axis='y', left=False, pad=4)
    axm.tick_params(axis='x', bottom=False, labelbottom=False)
    for sp in axm.spines.values(): sp.set_visible(False)
    axm.set_ylim(-0.6, len(K) - 0.4); axm.set_xlim(-0.6, len(itens) - 0.4)
    legenda_topo(fig, [chapa('em três listas ou mais', C3), chapa('em uma ou duas', C12),
                       chapa(f'em nenhuma lista: só a busca desta pesquisa ({br(comb.get((), 0))})', TZ)], ncol=3)
    salvar(fig, 'tese-cap5-08-listas-intersecoes')


@figura_tese
def c5_00_fluxo_reestimativa():
    """Figura (r40) — o percurso da reestimativa, das listas de partida às fichas (refaz o esboço do autor)."""
    from diagramas import tela, bloco_texto, ajustar, seta
    from matplotlib.patches import Rectangle
    fig, ax = tela(16.0, 11.0)
    def caixa(x, y, w, h, fc, txt, tc=TINTA, tam=8.2, sec=None):
        ax.add_patch(Rectangle((x, y - h), w, h, facecolor=fc, edgecolor='none', zorder=2))
        bloco_texto(ax, x + w / 2, y - h / 2, txt, tam, cor_texto=tc, cor_negrito=tc, cor_secundaria=sec or tc,
                    escala_secundaria=0.86, entrelinha=1.4, largura_cm=w - 0.3)
    G = 0.12
    # linha 1: duas entradas
    caixa(0.3, 0, 7.4, 1.9, cor('grafite', 200), '**Listas de partida**\n//Santini, NTU, MUNIC 2020 e literatura//\n//(Seção 5.1 e abertura)//', sec=TINTA2)
    caixa(8.3, 0, 7.4, 1.9, cor('grafite', 200), '**Busca de casos não mapeados**\n//índice da base municipal, PNCP, diários//\n//oficiais e Santini atualizado (Seção 5.3)//', sec=TINTA2)
    # linha 2: verificação
    caixa(2.3, -2.7, 11.4, 1.9, cor('grafite', 700), '**Verificação caso a caso**\n//norma lida, contrato ou empenho e prova de operação de 2025–2026;//\n//pedido de acesso à informação quando a busca se esgota (Seção 5.2)//',
          tc='#FFFFFF', sec=cor('grafite', 200))
    # linha 3: régua e enriquecimento
    caixa(0.3, -5.4, 7.4, 1.9, cor('grafite', 200), '**Aplicação da régua descritiva**\n//camada e subtipo pelo portão de acesso;//\n//trajetória de cada política (Seção 5.5)//', sec=TINTA2)
    caixa(8.3, -5.4, 7.4, 1.9, cor('grafite', 200), '**Enriquecimento com a base municipal**\n//porte, sistema de ônibus, finanças e//\n//operador (Parte 1 e Apêndice A)//', sec=TINTA2)
    # linha 4: saídas
    caixa(0.3, -8.1, 7.4, 1.9, TZ, '**Panorama reestimado**\n//quantas, onde, desde quando e entre//\n//quantos municípios com ônibus (Seção 5.4)//', tc='#FFFFFF')
    caixa(8.3, -8.1, 7.4, 1.9, TZ, '**Fichas municipais**\n//norma, contratos, régua e operador//\n//de cada município (Apêndice D)//', tc='#FFFFFF')
    # setas
    seta(ax, [(4.0, -1.9 - G), (4.0, -2.7 + G)], raio=0, espessura=1.4)
    seta(ax, [(12.0, -1.9 - G), (12.0, -2.7 + G)], raio=0, espessura=1.4)
    seta(ax, [(4.0, -4.6 - G), (4.0, -5.4 + G)], raio=0, espessura=1.4)
    seta(ax, [(12.0, -4.6 - G), (12.0, -5.4 + G)], raio=0, espessura=1.4)
    seta(ax, [(4.0, -7.3 - G), (4.0, -8.1 + G)], raio=0, espessura=1.4)
    seta(ax, [(12.0, -7.3 - G), (12.0, -8.1 + G)], raio=0, espessura=1.4)
    seta(ax, [(7.7 + G, -6.35), (8.3 - G, -6.35)], raio=0, espessura=1.4)
    bloco_texto(ax, 8.0, -10.5, 'a verificação não terminou: casos abertos e pedidos sem resposta voltam ao topo a cada rodada,\n'
                'e as contagens são datadas', 7.2, cor_texto=FRACA, entrelinha=1.35)
    seta(ax, [(15.7 + G + 0.15, -3.65), (15.95, -3.65), (15.95, 0.6), (8.0, 0.6), (8.0, 0 + G)], raio=0.4, espessura=1.0,
         cor_traco=cor('grafite', 300))
    ajustar(fig, ax, margem=0.3)
    salvar(fig, 'tese-cap5-00-fluxo-reestimativa')


if __name__ == '__main__':
    alvo = sys.argv[1:] or list(FIG)
    for n in alvo:
        FIG[n]()
