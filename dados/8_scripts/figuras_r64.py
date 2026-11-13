# -*- coding: utf-8 -*-
"""figuras_r64.py — figuras da revisão r64 (Cap. 7, régua analítica), no padrão de figuras_padrao.py.
  tese-r64-c7-plano            : Figura 19 refeita como figura conceitual (sem contagens; posições do plano)
  tese-r64-c7-destinatario-porte: destinatário do recurso por faixa de população — base de 11/10/2026 e frente CNPJ v6 (14/10/2026, a conferir)
  tese-r64-c7-pagamentos-vipe  : pagamentos de São Caetano do Sul à VIPE por ano e estimativas de custo (2023–2026)
Dados embutidos (poucos valores), com a origem anotada em cada bloco."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figuras_padrao as fp
from figuras_padrao import *   # noqa
from matplotlib.patches import Rectangle, Patch
import numpy as np
R = {}
def reg(f): R[f.__name__] = f; return f

# ── Figura 19: o plano, conceitual ─────────────────────────────────────────
COLS = [('(i)', 'Operação pública', 'prestação direta,\nautarquia, empresa pública'),
        ('(ii)', 'Operador privado\npago pela oferta', 'km, veículo, custo,\nvalor fixo'),
        ('(iii)', 'Operador privado\npago pela demanda', 'passageiro, subvenção\nda tarifa, reequilíbrio'),
        ('(iv)', 'Usuário', 'vale, crédito\nou passe pago')]
ROWS = [('Gratuidade universal', 'sem tarifa para todos'),
        ('Gratuidade parcial', 'de grupo, de tempo\nou de espaço (portão)'),
        ('Subsídio à tarifa', 'reduz o preço\npara todos'),
        ('Tarifa sem subsídio', 'usuário paga\no custo')]
@reg
def r64_c7_plano():
    from diagramas import tela, bloco_texto, ajustar
    fig, ax = tela(16.0, 12.5)
    X0, Y0, wl, wc, hh, hr = 0.2, 0, 3.2, 3.15, 1.75, 2.15
    ax.annotate('', xy=(X0 - 0.05, Y0 - hh - 0.05), xytext=(X0 - 0.05, Y0 - hh - 4 * hr + 0.05),
                arrowprops=dict(arrowstyle='-|>', color=FRACA, lw=1.0, mutation_scale=8), annotation_clip=False)
    bloco_texto(ax, X0 + wl / 2, Y0 - 0.15, '**GRAU**\n//desmercantilização//\n//do acesso//', 7.2, ancora='topo', entrelinha=1.3,
                cor_texto=FRACA, cor_negrito=FRACA)
    for j, (k, t, sub) in enumerate(COLS):
        x = X0 + wl + j * wc
        bloco_texto(ax, x + wc / 2, Y0 - 0.15, f'**{k} {t.splitlines()[0]}**' + (f'\n**{t.splitlines()[1]}**' if '\n' in t else '')
                    + '\n' + '\n'.join(f'//{l}//' for l in sub.split('\n')), 7.2, ancora='topo', entrelinha=1.3, escala_secundaria=0.92)
    for i, (t, sub) in enumerate(ROWS):
        y = Y0 - hh - i * hr
        ax.add_patch(Rectangle((X0, y - hr), wl + 4 * wc, hr, facecolor='none', edgecolor=NEUTROS['grade'], lw=0.6, zorder=1))
        bloco_texto(ax, X0 + 0.1, y - hr / 2, f'**{t}**\n' + '\n'.join(f'//{l}//' for l in sub.split('\n')), 7.2,
                    alinhar='left', entrelinha=1.3, escala_secundaria=0.92)
    y1 = Y0 - hh
    cel = [(cor('rosa', 700), '#FFFFFF', '**gasto público**\ncom controle social:\ngestão do comum;\nsem ele, operação\nsem controle'),
           (TZ, '#FFFFFF', '**com contrapartida:**\ngestão do comum\n**sem contrapartida:**\ngarantia de receita\nsem controle'),
           (cor('rosa', 200), TINTA, '**com contrapartida:**\ngratuidade sem ruptura\n**sem contrapartida:**\n“Bolsa-Empresário”'),
           ('#FFFFFF', TINTA, 'formal: lê-se como (iii)\nquando o crédito volta\nao operador por\npassageiro')]
    for j, (fc, tc, txt) in enumerate(cel):
        x = X0 + wl + j * wc
        ax.add_patch(Rectangle((x + 0.08, y1 - hr + 0.08), wc - 0.16, hr - 0.16, facecolor=fc,
                               edgecolor=(cor('rosa', 300) if fc == '#FFFFFF' else 'none'), lw=0.9, zorder=2))
        bloco_texto(ax, x + wc / 2, y1 - hr / 2, txt, 6.3, cor_texto=tc, cor_negrito=tc, entrelinha=1.3, zorder=4)
    def zona(c0, c1, row, txt, fc=cor('grafite', 200), tc=TINTA):
        x = X0 + wl + c0 * wc; y = Y0 - hh - row * hr
        ax.add_patch(Rectangle((x + 0.08, y - hr + 0.08), (c1 - c0 + 1) * wc - 0.16, hr - 0.16, facecolor=fc, edgecolor='none', zorder=2))
        bloco_texto(ax, x + (c1 - c0 + 1) * wc / 2, y - hr / 2, txt, 6.8, largura_cm=(c1 - c0 + 1) * wc - 0.5, cor_texto=tc, entrelinha=1.35, zorder=4)
    zona(2, 2, 1, '**T2 · inequidade cruzada**\n//o pagante custeia//\n//o gratuito//')
    zona(0, 1, 1, '//gratuidade de grupo paga//\n//pelo orçamento: subsídio//\n//público (Seção 4.4)//', fc=cor('grafite', 100))
    zona(1, 2, 2, '**T1 · subsídio parcial**\n//aporte que reduz a tarifa//\n//(29% a 33% do custo, conforme a fonte)//')
    zona(1, 2, 3, '**modelo tarifado**\n//operação “por conta e risco”,//\n//remuneração pela tarifa//', fc=cor('grafite', 100))
    ajustar(fig, ax, margem=0.25)
    salvar(fig, 'tese-r64-c7-plano')

# ── Destinatário × porte (base 11/10 e frente v6) ───────────────────────────
# origem: s5_figA_destinatario_porte_long.csv (sessão r64), recálculo sobre a base congelada e a frente CNPJ v6
FAIXAS = ['< 20 mil (60)', '20–50 mil (73)', '50–100 mil (27)', '> 100 mil (14)']
CATS = ['(i) operação pública', '(ii) privado, pago pela oferta', '(iii) privado, pago pela demanda', 'privado, remuneração não apurada', 'não apurado']
BASE = np.array([[29, 11, 2, 4, 14], [22, 22, 0, 8, 21], [9, 6, 1, 4, 7], [2, 2, 1, 7, 2]])
FRENTE = np.array([[34, 18, 1, 2, 5], [23, 31, 0, 10, 9], [6, 13, 0, 5, 3], [3, 7, 1, 3, 0]])
@reg
def r64_c7_destinatario_porte():
    cores = [cor('rosa', 700), TZ, cor('rosa', 200), cor('grafite', 300), cor('grafite', 100)]
    fig, axs = figura(8.4, ncols=2, sharey=True)
    for ax, M, tit in ((axs[0], BASE, 'A · base de 11/10/2026'), (axs[1], FRENTE, 'B · com o levantamento do arranjo (14/10/2026, a conferir)')):
        y = np.arange(len(FAIXAS))[::-1]
        left = np.zeros(len(FAIXAS))
        for k in range(5):
            v = M[:, k]; p = v / M.sum(1) * 100
            ax.barh(y, p, left=left, color=cores[k], edgecolor='#FFFFFF', lw=0.6, height=0.62)
            for yi, pi, li, vi in zip(y, p, left, v):
                if pi >= 6:
                    ax.text(li + pi / 2, yi, str(vi), ha='center', va='center', fontsize=6.6,
                            color='#FFFFFF' if k in (0, 1) else TINTA)
            left += p
        ax.set_yticks(y, FAIXAS); ax.set_xlim(0, 100); fmt_eixo(ax, 'x', suf='%'); barra_h(ax)
        ax.set_title(tit, fontsize=7.6, loc='left')
    legenda_topo(fig, [chapa(c, k) for c, k in zip(CATS, cores)], ncol=3)
    salvar(fig, 'tese-r64-c7-destinatario-porte')

# ── Pagamentos à VIPE (São Caetano do Sul) ──────────────────────────────────
# origem: Repasses VIPE - São Caetano do Sul (2023-2026).xlsx, aba Resumo por Ano (extração de 19/07/2026);
# referências: NTU (2024; 2025b) R$ 34,8 mi/ano; NTU (2026b) R$ 50 mi/ano; relatório USCS/SEMOB R$ 3,74 mi/mês.
@reg
def r64_c7_pagamentos_vipe():
    fig, ax = figura(7.6)
    anos = ['2023\n(jul.–dez.)', '2024', '2025', '2026\n(até 14/07)']
    x = np.arange(4)
    ax.bar(x[0], 10.0, color=cor('rosa', 300), width=0.6, edgecolor='#FFFFFF')
    ax.bar(x[0], 4.62, bottom=10.0, color=TZ, width=0.6, edgecolor='#FFFFFF')
    ax.bar(x[1:3], [41.90, 38.60], color=TZ, width=0.6, edgecolor='#FFFFFF')
    ax.bar(x[3], 18.56, color='#FFFFFF', edgecolor=TZ, hatch='////', lw=1.0, width=0.6)
    for xi, v in zip(x, [14.62, 41.90, 38.60, 18.56]):
        ax.text(xi, v + 0.9, br(v, 1).replace('.', ','), ha='center', va='bottom', fontsize=7.2, color=TINTA)
    refs = [(34.8, 'NTU (2024; 2025b): 34,8'), (44.9, 'relatório USCS/SEMOB: 44,9'), (50.0, 'NTU (2026b): 50,0')]
    for v, t in refs:
        ax.axhline(v, color=cor('azul', 600), lw=0.9, ls=(0, (3, 2)), zorder=0)
        ax.text(3.42, v + 0.5, t, ha='right', va='bottom', fontsize=6.4, color=cor('azul', 700))
    ax.set_xticks(x, anos); ax.set_ylim(0, 56); barra_v(ax); ax.set_ylabel('R$ milhões')
    legenda_topo(fig, [chapa('repasses extraordinários (2023)', cor('rosa', 300)), chapa('pagamentos recorrentes', TZ),
                       vazada('2026, ano incompleto', TZ)], ncol=3)
    salvar(fig, 'tese-r64-c7-pagamentos-vipe')

if __name__ == '__main__':
    for n in (sys.argv[1:] or list(R)): R[n]()
