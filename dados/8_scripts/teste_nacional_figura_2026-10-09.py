# -*- coding: utf-8 -*-
"""Figura do teste nacional (09/10/2026): razão de chances da presença de grupo econômico,
por posição no arranjo (todas as adoções) e por faixa de uso do ônibus (adoções de 2023 em diante).
Lê resultados_final.json (etapa 4 de teste_nacional_logit_2026-10-09.py: especificação final, no recorte dos testes — só a Tarifa Zero universal, parciais fora; r46). Padrão do Design System de Figuras (16 cm, Poppins, fundo branco).
Uso (na raiz do cofre): python "_meta/scripts/teste_nacional_figura_2026-10-09.py"
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import os, sys, json
from pathlib import Path
AQUI = Path(__file__).resolve().parent; sys.path.insert(0, str(AQUI))
import matplotlib as mpl; mpl.use('Agg')
import matplotlib.pyplot as plt, matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from estilo_figuras import aplicar_estilo, salvar, NEUTROS
V = Path(os.environ.get('TZ_VAULT', AQUI.parents[1]))
S = V / '03 - Dados' / '_data' / 'Análise espacial GE x TZ (out-2026, teste nacional)'
OUT = Path(os.environ.get('SAIDA', V / '_attachments'))
R = json.load(open(S / 'resultados_final.json', encoding='utf-8'))
aplicar_estilo('tese')
mpl.rcParams.update({'font.size': 8, 'axes.labelsize': 7.5, 'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5,
                     'legend.fontsize': 7.5, 'axes.titlesize': 8.5, 'axes.titleweight': 'medium', 'axes.titlelocation': 'left',
                     'axes.titlecolor': NEUTROS['tinta'], 'axes.labelcolor': NEUTROS['tinta_secundaria']})
QUALQUER, GRANDE = '#4F8BFF', '#1A54C7'
CM = 1 / 2.54
br = lambda v, d=2: f'{v:.{d}f}'.replace('.', ',')
paineis = [
    ('a) Posição no arranjo\nadoções da Tarifa Zero universal',
     R['A posição · ge_multi']['por_posicao'], R['A posição · ge_top']['por_posicao'],
     ['isolado', 'satélite', 'polo/co-polo'], ['Isolado', 'Satélite', 'Polo ou co-polo']),
    ('b) Ônibus no trabalho de quem fica no município\nadoções universais de 2023 em diante',
     R['B uso do ônibus · ge_multi']['por_faixa_onibus'], R['B uso do ônibus · ge_top']['por_faixa_onibus'],
     ['≤5%', '5-10%', '10-20%', '>20%'], ['Até 5%', '5 a 10%', '10 a 20%', 'Mais de 20%']),
]
fig, axs = plt.subplots(1, 2, figsize=(16 * CM, 7.6 * CM), layout='constrained', sharex=True)
for ax, (tit, rq, rg, ks, labs) in zip(axs, paineis):
    n = len(ks)
    for i, k in enumerate(ks):
        y = n - 1 - i
        for r, c, mk, dy in [(rq[k], QUALQUER, 'o', 0.14), (rg[k], GRANDE, 's', -0.14)]:
            ax.plot([r['ic_inf'], r['ic_sup']], [y + dy] * 2, color=c, lw=2, solid_capstyle='round', zorder=2)
            ax.plot(r['OR'], y + dy, mk, ms=6, color=c, mec='#FFFFFF', mew=1.2, zorder=3)
            if r['p'] < 0.05:
                ax.annotate(br(r['OR']), (r['ic_sup'], y + dy), xytext=(4, 0), textcoords='offset points',
                            va='center', ha='left', fontsize=7, color=NEUTROS['tinta'], fontweight='medium')
    ax.axvline(1, color=NEUTROS['tinta_fraca'], lw=1, zorder=1)
    ax.set_xscale('log'); ax.set_xlim(0.03, 12)
    ax.set_yticks(range(n)); ax.set_yticklabels(labs[::-1]); ax.set_ylim(-0.6, n - 0.4)
    ax.grid(axis='y', visible=False); ax.grid(axis='x', visible=True, color=NEUTROS['grade'], lw=0.6)
    ax.tick_params(axis='y', length=0)
    ax.xaxis.set_major_locator(mticker.FixedLocator([0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8]))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: br(v, 2).rstrip('0').rstrip(',')))
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.set_title(tit, loc='left')
h = [Line2D([], [], color=QUALQUER, marker='o', lw=2, ms=6, mec='#FFFFFF', label='Qualquer grupo multiempresa'),
     Line2D([], [], color=GRANDE, marker='s', lw=2, ms=6, mec='#FFFFFF', label='Grande grupo (metade do capital)')]
fig.supxlabel('Razão de chances da presença de grupo, em escala log (abaixo de 1: menos adoção onde há grupo)', fontsize=7.5, color=NEUTROS['tinta_secundaria'])
fig.legend(handles=h, loc='outside upper left', ncol=2, frameon=False, handlelength=1.8, columnspacing=1.4)
salvar(fig, OUT / 'tese-cap8-teste-nacional-razao-chances.svg', png=True, auditar=False)
print('ok')
