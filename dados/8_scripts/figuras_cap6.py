# -*- coding: utf-8 -*-
"""figuras_cap6.py — figuras do Cap. 6 (r21, 02/10/2026), no padrão do Design System (figuras_padrao.py).
  tese-cap6-01-regua-analitica-plano : o plano de dois eixos, com a contagem da Análise XII (camada 1, retrato 01/10/2026)
  tese-cap6-02-scs-duas-reguas       : São Caetano do Sul nas duas réguas (Análise XIII)
Contagens vindas de cap6_dados.py (mesmo retrato); valores passados como argumento para não reler a base aqui."""
import sys, json
from pathlib import Path
AQUI = Path(__file__).resolve().parent; sys.path.insert(0, str(AQUI))
import matplotlib as mpl; mpl.use('Agg')
from matplotlib.patches import Rectangle
from estilo_figuras import aplicar_estilo, salvar as _salvar, cor, NEUTROS
from diagramas import tela, bloco_texto, ajustar, seta
aplicar_estilo('tese')
TZ = cor('rosa', 500); TINTA, TINTA2, FRACA = NEUTROS['tinta'], NEUTROS['tinta_secundaria'], NEUTROS['tinta_fraca']
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI.parents[1] / '_attachments'
def salvar(fig, nome): _salvar(fig, OUT / f'{nome}.svg', png=True, auditar=False); print('ok', nome)

COLS = [('(i)', 'Operação pública', 'prestação direta,\nempresa pública'),
        ('(ii)', 'Operador privado\npago pela oferta', 'km, frota, custo,\nvalor fixo'),
        ('(iii)', 'Operador privado\npago pela demanda', 'passageiro, tarifa,\nreequilíbrio'),
        ('(iv)', 'Usuário', 'vale, crédito\nou passe pago')]
ROWS = [('Gratuidade universal', 'sem tarifa para todos'),
        ('Gratuidade parcial', 'de grupo, de tempo\nou de espaço'),
        ('Subsídio à tarifa', 'reduz o preço\npara todos'),
        ('Tarifa sem subsídio', 'usuário paga\no custo')]

def grade(ax, X0, Y0, wl, wc, hh, hr):
    for j, (k, t, sub) in enumerate(COLS):
        x = X0 + wl + j * wc
        bloco_texto(ax, x + wc / 2, Y0 - 0.15, f'**{k} {t.splitlines()[0]}**' + (f'\n**{t.splitlines()[1]}**' if '\n' in t else '')
                    + '\n' + '\n'.join(f'//{l}//' for l in sub.split('\n')), 7.2, ancora='topo', entrelinha=1.3, escala_secundaria=0.92)
    for i, (t, sub) in enumerate(ROWS):
        y = Y0 - hh - i * hr
        ax.add_patch(Rectangle((X0, y - hr), wl + 4 * wc, hr, facecolor='none', edgecolor=NEUTROS['grade'], lw=0.6, zorder=1))
        bloco_texto(ax, X0 + 0.1, y - hr / 2, f'**{t}**\n' + '\n'.join(f'//{l}//' for l in sub.split('\n')), 7.2,
                    alinhar='left', entrelinha=1.3, escala_secundaria=0.92)

def f1(cont):
    fig, ax = tela(16.0, 12.0)
    X0, Y0, wl, wc, hh, hr = 0.2, 0, 3.2, 3.15, 1.75, 2.15
    # eixo vertical
    ax.annotate('', xy=(X0 - 0.05, Y0 - hh - 0.05), xytext=(X0 - 0.05, Y0 - hh - 4 * hr + 0.05),
                arrowprops=dict(arrowstyle='-|>', color=FRACA, lw=1.0, mutation_scale=8), annotation_clip=False)
    bloco_texto(ax, X0 + wl / 2, Y0 - 0.15, '**GRAU**\n//desmercantilização//\n//do acesso//', 7.2, ancora='topo', entrelinha=1.3,
                cor_texto=FRACA, cor_negrito=FRACA)
    # faixa da gratuidade universal (linha 1)
    y1 = Y0 - hh
    for j, (k, n, fc, tc) in enumerate([('i', cont['i_publico'], cor('rosa', 700), '#FFFFFF'), ('ii', cont['ii_oferta'], TZ, '#FFFFFF'),
                                        ('iii', cont['iii_demanda'], cor('rosa', 200), TINTA), ('iv', 0, '#FFFFFF', TINTA)]):
        x = X0 + wl + j * wc
        if n:
            ax.add_patch(Rectangle((x + 0.08, y1 - hr + 0.08), wc - 0.16, hr - 0.16, facecolor=fc, edgecolor='none', zorder=2))
        else:
            ax.add_patch(Rectangle((x + 0.08, y1 - hr + 0.08), wc - 0.16, hr - 0.16, facecolor='#FFFFFF', edgecolor=cor('rosa', 300), lw=0.9, zorder=2))
        bloco_texto(ax, x + wc / 2, y1 - 0.55, f'**{n}**', 13, cor_texto=tc, cor_negrito=tc, zorder=4)
        sub = {'i': 'gestão do comum, se\nhouver controle social', 'ii': 'gestão do comum, com\ncontrapartida; sem ela,\ndesriscagem sem controle',
               'iii': 'gratuidade sem ruptura,\ncom contrapartida; sem ela,\n“Bolsa-Empresário”', 'iv': 'nenhum caso\nna camada 1'}[k]
        bloco_texto(ax, x + wc / 2, y1 - 1.5, sub, 5.9, cor_texto=tc, entrelinha=1.3, zorder=4)
    # tipologias nas linhas inferiores
    def zona(c0, c1, row, txt, fc=cor('grafite', 200), tc=TINTA):
        x = X0 + wl + c0 * wc; y = Y0 - hh - row * hr
        ax.add_patch(Rectangle((x + 0.08, y - hr + 0.08), (c1 - c0 + 1) * wc - 0.16, hr - 0.16, facecolor=fc, edgecolor='none', zorder=2))
        bloco_texto(ax, x + (c1 - c0 + 1) * wc / 2, y - hr / 2, txt, 7.0, largura_cm=(c1 - c0 + 1) * wc - 0.5, cor_texto=tc, entrelinha=1.35, zorder=4)
    zona(2, 2, 1, '**T2 · inequidade cruzada**\n//o pagante custeia//\n//o gratuito//')
    zona(0, 1, 1, '//gratuidade de grupo paga//\n//pelo orçamento: subsídio//\n//público (Seção 4.4)//', fc=cor('grafite', 100))
    zona(1, 2, 2, '**T1 · subsídio parcial**\n//aporte do Tesouro que reduz a tarifa//\n//(um terço do custo, em média; Análise X)//')
    zona(1, 2, 3, '**modelo tarifado**\n//operação “por conta e risco”,//\n//remuneração pela tarifa//', fc=cor('grafite', 100))
    grade(ax, X0, Y0, wl, wc, hh, hr)
    ajustar(fig, ax, margem=0.25)
    salvar(fig, 'tese-cap6-01-regua-analitica-plano')

def f2():
    fig, ax = tela(16.0, 12.6)
    # painel A — linha do tempo nas duas réguas
    bloco_texto(ax, 0.2, -0.1, '**A · Linha do tempo**', 8.0, alinhar='left', ancora='topo')
    X0, X1 = 2.0, 15.6
    import datetime as dt
    d0, d1 = dt.date(2023, 7, 1), dt.date(2026, 9, 1)
    xs = lambda d: X0 + (X1 - X0) * ((d - d0).days / (d1 - d0).days)
    yT = -2.2
    # faixas da régua descritiva
    for (a, b, lab, fc, tc) in [(dt.date(2023, 7, 1), dt.date(2023, 11, 1), 'tarifado', cor('grafite', 200), TINTA),
                                (dt.date(2023, 11, 1), dt.date(2026, 7, 15), '1a · universal, sem portão', TZ, '#FFFFFF'),
                                (dt.date(2026, 7, 15), dt.date(2026, 9, 1), '1c', cor('rosa', 300), TINTA)]:
        ax.add_patch(Rectangle((xs(a), yT), xs(b) - xs(a), 0.55, facecolor=fc, edgecolor='#FFFFFF', lw=0.8, zorder=2))
        bloco_texto(ax, (xs(a) + xs(b)) / 2, yT + 0.275, lab, 6.6, cor_texto=tc, zorder=4)
    bloco_texto(ax, 0.2, yT + 0.275, '**descritiva**', 6.6, alinhar='left', cor_texto=FRACA, cor_negrito=FRACA)
    yA = yT - 0.75
    for (a, b, lab, fc, tc) in [(dt.date(2023, 7, 1), dt.date(2023, 11, 1), '(iii)', cor('grafite', 200), TINTA),
                                (dt.date(2023, 11, 1), dt.date(2026, 7, 14), '(ii) pago por km e frota · sem instância de acompanhamento', cor('rosa', 700), '#FFFFFF'),
                                (dt.date(2026, 7, 14), dt.date(2026, 9, 1), 'ii', cor('rosa', 400), '#FFFFFF')]:
        ax.add_patch(Rectangle((xs(a), yA), xs(b) - xs(a), 0.55, facecolor=fc, edgecolor='#FFFFFF', lw=0.8, zorder=2))
        bloco_texto(ax, (xs(a) + xs(b)) / 2, yA + 0.275, lab, 6.6, cor_texto=tc, zorder=4)
    bloco_texto(ax, 0.2, yA + 0.275, '**analítica**', 6.6, alinhar='left', cor_texto=FRACA, cor_negrito=FRACA)
    # erosão por omissão
    a, b = dt.date(2025, 5, 1), dt.date(2025, 8, 31)
    ax.add_patch(Rectangle((xs(a), yA - 0.5), xs(b) - xs(a), 0.32, facecolor=cor('azul', 700), edgecolor='none', zorder=2))
    bloco_texto(ax, xs(a) - 0.12, yA - 0.34, 'erosão por omissão: frota −23,8%, repasses −17,2%', 6.4, alinhar='right', cor_texto=cor('azul', 700))
    # anos
    for y in (2024, 2025, 2026):
        x = xs(dt.date(y, 1, 1)); ax.plot([x, x], [yT + 0.75, yA - 0.6], color=NEUTROS['grade'], lw=0.6, zorder=1)
        bloco_texto(ax, x, yT + 0.95, str(y), 6.8, cor_texto=FRACA)
    EV = [(dt.date(2023, 10, 30), '1º aditivo:\npor km e frota', 0), (dt.date(2025, 5, 15), 'PL e Indicação\nrestritivos', 0),
          (dt.date(2025, 12, 23), 'anúncio da\nrestrição', 0), (dt.date(2026, 3, 31), 'convênio\nUSCS', 0),
          (dt.date(2026, 7, 15), 'lei votada (16/06);\nR$ 5 a não cadastrados\ne 4º aditivo (14–15/07)', 1)]
    for d, t, alt in EV:
        x = xs(d); yv = yA - 1.15 - alt * 0.95
        ax.plot([x, x], [yA - 0.62, yv + 0.05], color=FRACA, lw=0.5, zorder=1)
        bloco_texto(ax, x, yv, t, 6.2, ancora='topo', cor_texto=TINTA2, entrelinha=1.25, alinhar='right' if (d.year, d.month) in ((2026, 7), (2025, 12)) else 'center')
    # painel B — o plano
    yB = -6.6
    bloco_texto(ax, 0.2, yB, '**B · Posição no plano da régua analítica**', 8.0, alinhar='left', ancora='topo')
    PX0, PY0, wl, wc, hr = 3.4, yB - 0.75, 0, 3.05, 1.18
    cols = ['(i) operação\npública', '(ii) privado, pago\npela oferta', '(iii) privado, pago\npela demanda', '(iv) usuário']
    rows = ['gratuidade universal', 'gratuidade só a residentes', 'subsídio à tarifa', 'tarifa sem subsídio']
    for j, c in enumerate(cols):
        bloco_texto(ax, PX0 + j * wc + wc / 2, PY0, c, 6.6, ancora='topo', entrelinha=1.25, cor_texto=TINTA2)
    gy = PY0 - 0.8
    for i, r in enumerate(rows):
        y = gy - i * hr
        ax.add_patch(Rectangle((PX0, y - hr), 4 * wc, hr, facecolor='none', edgecolor=NEUTROS['grade'], lw=0.6, zorder=1))
        bloco_texto(ax, PX0 - 0.15, y - hr / 2, r, 6.6, alinhar='right', cor_texto=TINTA2)
    for j in range(5):
        ax.plot([PX0 + j * wc] * 2, [gy, gy - 4 * hr], color=NEUTROS['grade'], lw=0.6, zorder=1)
    def ponto(j, i, txt, fc, tc='#FFFFFF'):
        cx, cy = PX0 + j * wc + wc / 2, gy - i * hr - hr / 2
        ax.add_patch(Rectangle((cx - 1.3, cy - 0.4), 2.6, 0.8, facecolor=fc, edgecolor='none', zorder=3))
        bloco_texto(ax, cx, cy, txt, 6.4, cor_texto=tc, entrelinha=1.25, zorder=4)
        return cx, cy
    p0 = ponto(2, 3, 'até out. 2023\n“por conta e risco”', cor('grafite', 500))
    p1 = ponto(1, 0, 'nov. 2023 – jul. 2026\nsem contrapartida', cor('rosa', 700))
    p2 = ponto(1, 1, 'desde 15/07/2026\ntarifa + subsídio', cor('rosa', 400))
    seta(ax, [(p0[0] - 1.35, p0[1]), (p1[0] + 1.75, p0[1]), (p1[0] + 1.75, p1[1]), (p1[0] + 1.34, p1[1])], raio=0.3, cor_traco=FRACA, espessura=1.0)
    seta(ax, [(p1[0], p1[1] - 0.42), (p1[0], p2[1] + 0.44)], raio=0.1, cor_traco=FRACA, espessura=1.0)
    ajustar(fig, ax, margem=0.25)
    salvar(fig, 'tese-cap6-02-scs-duas-reguas')

if __name__ == '__main__':
    cont = json.loads(sys.argv[1])
    f1(cont); f2()
