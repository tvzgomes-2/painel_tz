# -*- coding: utf-8 -*-
"""figuras_r62.py — figuras novas da revisão r62 (15/10/2026), no padrão de figuras_padrao.py.
Base: versão de 11/10/2026 (retratos/2026-10-11), salvo indicação. Saída: _attachments/tese-r62-*.svg + .png.
Uso (na raiz do cofre): python "_meta/scripts/figuras_r62.py" [nome ...]"""
import os, sys
os.environ.setdefault('TZ_RETRATO', '2026-10-11')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figuras_padrao as fp
from figuras_padrao import *   # noqa
import numpy as np, pandas as pd, re
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

R = {}
def fig_r62(f): R[f.__name__] = f; return f

def base_ret():
    m = pd.read_excel(fp.RET / 'Municípios TZ - consolidado.xlsx')
    m['cod'] = pd.to_numeric(m['Código IBGE'], errors='coerce')
    return m.merge(fp.pontos(), left_on='cod', right_on='CD_MUN', how='left')

PT = 9  # marcador fixo nos painéis pequenos (sem escala de população)

# ── Cap. 5: fluxo do método ────────────────────────────────────────────────
@fig_r62
def r62_c5_fluxo():
    from diagramas import tela, bloco_texto, ajustar, seta
    fig, ax = tela(16.0, 12.0)
    def caixa(x, y, w, h, fc, txt, tc=TINTA, sec=None, tam=8.0):
        ax.add_patch(Rectangle((x, y - h), w, h, facecolor=fc, edgecolor='none', zorder=2))
        bloco_texto(ax, x + w / 2, y - h / 2, txt, tam, cor_texto=tc, cor_negrito=tc, cor_secundaria=sec or TINTA2,
                    escala_secundaria=0.88, entrelinha=1.38, largura_cm=w - 0.3)
    G = 0.12; CL = cor('grafite', 200); CE = cor('grafite', 700); CS = TZ
    caixa(0.3, 0, 4.9, 2.0, CL, '**Listas de partida**\n//Santini, NTU, outros//\n//levantamentos e MUNIC 2020//')
    caixa(5.55, 0, 4.9, 2.0, CL, '**5.1 Busca de casos**\n**não mapeados**\n//índice municipal, PNCP,//\n//diários oficiais, legislativos//')
    caixa(10.8, 0, 4.9, 2.0, CL, '**5.2 Revisão sistemática**\n//81 trabalhos: casos citados//\n//e fatores da adoção//')
    for x in (2.75, 8.0, 13.25):
        seta(ax, [(x, -2.0 - G), (x, -2.7 + G)], raio=0, espessura=1.4)
    caixa(0.3, -2.7, 15.4, 2.1, CE, '**5.3 Pesquisa documental: verificação caso a caso**\n//norma lida, contrato ou empenho e prova de operação de 2025–2026;//\n//pedido de acesso à informação quando a busca se esgota//',
          tc='#FFFFFF', sec=cor('grafite', 200))
    seta(ax, [(8.0, -4.8 - G), (8.0, -5.5 + G)], raio=0, espessura=1.4)
    caixa(3.3, -5.5, 9.4, 1.6, cor('grafite', 400), '**Base de políticas municipais de Tarifa Zero**\n//187 em escopo: 181 ativas e 6 encerradas//', tc='#FFFFFF', sec='#FFFFFF')
    from diagramas import linha as _linha
    _linha(ax, [(8.0, -7.1 - G), (8.0, -7.45)], raio=0, espessura=1.4)
    _linha(ax, [(2.75, -7.45), (13.25, -7.45)], raio=0, espessura=1.4)
    for x in (2.75, 8.0, 13.25):
        seta(ax, [(x, -7.45), (x, -7.8 + G)], raio=0, espessura=1.4)
    caixa(0.3, -7.8, 4.9, 2.2, CS, '**5.4 Panorama**\n//quantas, onde e desde quando;//\n//porte e sistema de ônibus//', tc='#FFFFFF', sec='#FFFFFF')
    caixa(5.55, -7.8, 4.9, 2.2, CS, '**5.5 Régua descritiva**\n//camada e subtipo pelo//\n//portão de acesso; trajetória//', tc='#FFFFFF', sec='#FFFFFF')
    caixa(10.8, -7.8, 4.9, 2.2, CS, '**5.6 Arranjo**\n//norma, contrato, operação,//\n//veículo e remuneração (D1–D5)//', tc='#FFFFFF', sec='#FFFFFF')
    for x in (2.75, 8.0, 13.25):
        seta(ax, [(x, -10.0 - G), (x, -10.6 + G)], raio=0, espessura=1.2, cor_traco=cor('grafite', 400))
    caixa(0.3, -10.6, 15.4, 1.1, cor('grafite', 200), '**Fichas municipais** //(Apêndice D): norma, contratos, régua e operador de cada município//', tam=7.8)
    ajustar(fig, ax, margem=0.3)
    salvar(fig, 'tese-r62-c5-fluxo-metodo')

# ── Cap. 5: mapa-síntese das camadas ───────────────────────────────────────
@fig_r62
def r62_c5_mapa_sintese():
    P, U_ = fp._regua_pontos(); u1, u2, u3 = U_['u1'], U_['u2'], U_['u3']
    reg = [c for c in u2.columns if c.startswith('Regime da 2d')]
    if reg:
        r = u2[reg[0]].astype(str); u2 = u2[~((u2.Subtipo.astype(str) == '2d') & ~r.str.contains('não eleitoral', regex=False))]
    fig, ax = figura(14.2); mapa_base(ax)
    x2 = u2.drop_duplicates('k').merge(P, left_on='k', right_index=True)
    x1 = u1.merge(P, left_on='k', right_index=True); x3 = u3.merge(P, left_on='k', right_index=True)
    ax.scatter(x2.lon, x2.lat, s=tam_pop(x2.pop_2022) * 0.7, color=cor('azul', 700), alpha=0.85, edgecolor='white', lw=0.35, zorder=3)
    ax.scatter(x1.lon, x1.lat, s=tam_pop(x1.pop_2022) * 0.7, color=TZ, alpha=0.9, edgecolor='white', lw=0.35, zorder=4)
    ax.scatter(x3.lon, x3.lat, s=30, marker='X', color=TINTA, lw=0, zorder=5)
    hs = [Line2D([], [], marker='o', ls='', color=TZ, ms=6, label=f'camada 1 · universal ({len(x1)})'),
          Line2D([], [], marker='o', ls='', color=cor('azul', 700), ms=6, label=f'camada 2 · parcial ({len(x2)})'),
          Line2D([], [], marker='X', ls='', color=TINTA, ms=6, label=f'camada 3 · encerrada ({len(x3)})')]
    l1 = ax.legend(handles=hs, loc='lower left', title='camadas da régua descritiva', title_fontsize=7, fontsize=7, frameon=False, alignment='left')
    ax.add_artist(l1)
    hs2 = [ax.scatter([], [], s=tam_pop(pd.Series([p])).iloc[0] * 0.7, color=cor('grafite', 300), edgecolor='white', lw=0.4) for p in (10000, 50000, 300000)]
    ax.legend(hs2, ['10 mil hab.', '50 mil hab.', '300 mil hab.'], loc='lower right', title='população (2022)', title_fontsize=7, fontsize=7, labelspacing=1.1, frameon=False, alignment='left')
    salvar(fig, 'tese-r62-c5-mapa-sintese-camadas')

def _paineis(grupos, nome, altura=11.8):
    n = len(grupos); nrows = int(np.ceil(n / 3))
    fig, axs = figura(altura * nrows / 2, ncols=3, nrows=nrows)
    axs = np.atleast_1d(axs).flat
    for ax, (lab, x, c, mk) in zip(axs, grupos):
        mapa_base(ax)
        ax.scatter(x.lon, x.lat, s=PT if mk == 'o' else PT * 2.2, marker=mk, color=c, alpha=0.9, edgecolor='white' if mk == 'o' else 'none', lw=0.3, zorder=3)
        ax.set_title(f'{lab} · {len(x)}', fontsize=8)
    for ax in list(axs)[n:]: ax.axis('off')
    salvar(fig, nome)

@fig_r62
def r62_c5_mapas_camada1():
    P, U_ = fp._regua_pontos(); u1, u3 = U_['u1'].copy(), U_['u3']
    u1['Subtipo'] = u1['Subtipo'].fillna('sem')
    G = []
    for k, lab, c in (('1a', '1a · sem portão', cor('rosa', 500)), ('1b', '1b · cadastro aberto', cor('azul', 700)),
                      ('1c', '1c · residência', cor('verde', 700)), ('1d', '1d · prazo declarado', cor('amarelo', 500)),
                      ('sem', 'subtipo em verificação', cor('grafite', 600))):
        G.append((lab, u1[u1.Subtipo == k].merge(P, left_on='k', right_index=True), c, 'o'))
    G.append(('3 · encerradas', u3.merge(P, left_on='k', right_index=True), TINTA, 'X'))
    _paineis(G, 'tese-r62-c5-mapas-camada1')

@fig_r62
def r62_c5_mapas_camada2():
    P, U_ = fp._regua_pontos(); u2 = U_['u2']
    reg = [c for c in u2.columns if c.startswith('Regime da 2d')]
    if reg:
        r = u2[reg[0]].astype(str); u2 = u2[~((u2.Subtipo.astype(str) == '2d') & ~r.str.contains('não eleitoral', regex=False))]
    G = []
    for k, lab in (('2a', '2a · grupo social'), ('2b', '2b · espaço ou linha'), ('2c', '2c · tempo recorrente'),
                   ('2d', '2d · eventos'), ('2e', '2e · finalidade')):
        x = u2[u2.Subtipo.astype(str).str.contains(k, regex=False)].drop_duplicates('k').merge(P, left_on='k', right_index=True)
        G.append((lab, x, cor('azul', 700), 'o'))
    G.append(('camada 2 · todos os subtipos', u2.drop_duplicates('k').merge(P, left_on='k', right_index=True), cor('azul', 500), 'o'))
    _paineis(G, 'tese-r62-c5-mapas-camada2')

# ── Cap. 5: em quais levantamentos aparece cada política ──────────────────
@fig_r62
def r62_c5_mapa_levantamentos():
    import openpyxl
    wb = openpyxl.load_workbook(fp.RET / 'Municípios TZ - consolidado.xlsx', read_only=True, data_only=True)
    rows = [r for r in list(wb['consolidado'].iter_rows(values_only=True))[1:] if r[0] and r[3] in ('Ativa', 'Encerrada')]
    det = []
    for r in rows:
        s81 = str(r[81] or ''); m = re.search(r'RSL: (\d+) fichamento', str(r[83] or ''))
        det.append(dict(cod=pd.to_numeric(r[2], errors='coerce'),
                        S=(r[76] is not None) or ('Santini' in s81),
                        N=any(k in s81 for k in ('NTU (2024)', 'NTU (2025)', 'NTU (2026)')),
                        O=any(k in s81 for k in ('Fernandes Pereira', 'Brinco', 'Angelo (2023)', 'Vermander', 'UnB/Geourb', 'Santini (2019)')),
                        M=str(r[69]).startswith('Sim'), L=bool(m and int(m.group(1)) > 0)))
    d = pd.DataFrame(det); d['n'] = d[['S', 'N', 'O', 'M', 'L']].sum(axis=1)
    d = d.merge(fp.pontos(), left_on='cod', right_on='CD_MUN', how='left')
    fig = plt.figure(figsize=(L * CM, 20.5 * CM), layout='constrained')
    gs = fig.add_gridspec(3, 3, height_ratios=[2.3, 1, 1])
    ax = fig.add_subplot(gs[0, :]); mapa_base(ax)
    RAMP = {1: cor('grafite', 300), 2: cor('grafite', 500), 3: cor('grafite', 800), 4: cor('grafite', 800), 5: cor('grafite', 800)}
    for k in (5, 4, 3, 2, 1):
        x = d[d.n == k]; ax.scatter(x.lon, x.lat, s=14, color=RAMP[k], edgecolor='white', lw=0.3, zorder=3)
    x0 = d[d.n == 0]; ax.scatter(x0.lon, x0.lat, s=22, color=TZ, edgecolor='white', lw=0.3, zorder=5)
    hs = [Line2D([], [], marker='o', ls='', color=TZ, ms=6, label=f'em nenhuma lista: só esta pesquisa ({len(x0)})')]
    for k, lab in ((1, 'em uma lista'), (2, 'em duas'), (3, 'em três ou mais')):
        n = (d.n == k).sum() if k < 3 else (d.n >= 3).sum()
        hs.append(Line2D([], [], marker='o', ls='', color=RAMP[k], ms=6, label=f'{lab} ({n})'))
    ax.legend(handles=hs, loc='upper left', bbox_to_anchor=(0.0, 0.98), title=f'políticas em escopo ({len(d)}) por número de listas', title_fontsize=7, fontsize=7, frameon=False, alignment='left')
    NOME = [('S', 'Santini'), ('N', 'NTU (casos nomeados)'), ('O', 'outros levantamentos'), ('M', 'MUNIC 2020'), ('L', 'literatura (revisão)')]
    for i, (k, lab) in enumerate(NOME):
        a = fig.add_subplot(gs[1 + i // 3, i % 3]); mapa_base(a)
        x = d[d[k]]; a.scatter(x.lon, x.lat, s=PT, color=cor('grafite', 700), edgecolor='white', lw=0.3, zorder=3)
        a.set_title(f'{lab} · {len(x)}', fontsize=8)
    a = fig.add_subplot(gs[2, 2]); mapa_base(a)
    a.scatter(x0.lon, x0.lat, s=PT, color=TZ, edgecolor='white', lw=0.3, zorder=3); a.set_title(f'só esta pesquisa · {len(x0)}', fontsize=8)
    salvar(fig, 'tese-r62-c5-mapa-levantamentos')

# ── Cap. 6: funil do cadastro ao grupo ───────────────────────────────────
@fig_r62
def r62_c6_fluxo():
    from diagramas import tela, bloco_texto, ajustar, seta
    fig, ax = tela(16.0, 13.5)
    passos = [
        ('1 Delimitação', 'estabelecimentos com o ônibus municipal ou metropolitano como atividade principal (CNAE 4921-3/01 e /02)', '48.400 estabelecimentos'),
        ('2 Situação ativa', 'situação cadastral ativa', '14.988 estabelecimentos · 12.907 empresas'),
        ('3 Sócios', 'cruzamento com a tabela de sócios', '23.842 vínculos · 13.569 sócios'),
        ('4 Rede', 'empresas ligadas por sócio em comum; o grupo é o componente', 'componentes da rede'),
        ('5 Recorte de porte', 'três empresas ou mais, ou capital relevante', '327 grupos (165 + 58 + 104)'),
        ('6 Expansão', 'sócios pessoas jurídicas seguidos até o fim da cadeia', 'holdings e terceiro nível'),
        ('7 Qualificação', 'atuação municipal, nome de mercado, colapso e conduta, por fontes externas', 'auditoria dos 327 grupos'),
    ]
    y = 0; h = 1.55; gap = 0.35
    for i, (t, dsc, n) in enumerate(passos):
        w = 15.4 - i * 1.1; x = (16 - w) / 2
        fc = cor('grafite', 200) if i not in (4,) else TZ
        tc = TINTA if i != 4 else '#FFFFFF'
        ax.add_patch(Rectangle((x, y - h), w, h, facecolor=fc, edgecolor='none', zorder=2))
        bloco_texto(ax, 8.0, y - h / 2, f'**{t}** · {n}\n//{dsc}//', 7.8, cor_texto=tc, cor_negrito=tc, cor_secundaria=tc if i == 4 else TINTA2,
                    escala_secundaria=0.9, entrelinha=1.35, largura_cm=w - 0.4)
        if i < len(passos) - 1:
            seta(ax, [(8.0, y - h - 0.03), (8.0, y - h - gap + 0.03)], raio=0, espessura=1.2)
        y -= h + gap
    ajustar(fig, ax, margem=0.3)
    salvar(fig, 'tese-r62-c6-fluxo-cadastro-grupo')

# ── Cap. 8: barreira e simbiose no território ─────────────────────────────
@fig_r62
def r62_c8_mapa_zonas():
    b = pd.read_csv(D / 'Análise espacial GE x TZ (out-2026, teste nacional)' / 'base_teste_nacional.csv')
    b = b.merge(fp.pontos(), left_on='cod_ibge', right_on='CD_MUN', how='left')
    b = b[b.parcial != 1]
    cat = np.select([(b.y_univ == 1) & (b.ge_multi == 1), (b.y_univ == 1) & (b.ge_multi == 0), (b.y_univ == 0) & (b.ge_multi == 1)],
                    ['tz_grupo', 'tz_sem', 'grupo_sem'], 'resto')
    b['cat'] = cat
    fig, axs = figura(8.6, ncols=2)
    for ax, sel, tit in ((axs[0], b, 'Brasil'), (axs[1], b[b.posicao.isin(['satelite', 'satélite', 'polo', 'co-polo'])], 'municípios em arranjo populacional (polo e satélite)')):
        mapa_base(ax)
        x = sel[sel.cat == 'grupo_sem']; ax.scatter(x.lon, x.lat, s=5, color=cor('azul', 400), lw=0, zorder=2)
        x = sel[sel.cat == 'tz_sem']; ax.scatter(x.lon, x.lat, s=9, color=TZ, edgecolor='white', lw=0.25, zorder=3)
        x = sel[sel.cat == 'tz_grupo']; ax.scatter(x.lon, x.lat, s=14, color=TINTA, edgecolor='white', lw=0.25, zorder=4)
        ax.set_title(tit, fontsize=8)
    n = lambda c: int((b.cat == c).sum())
    legenda_topo(fig, [Line2D([], [], marker='o', ls='', color=cor('azul', 400), ms=5, label=f'grupo presente, sem Tarifa Zero ({br(n("grupo_sem"))})'),
                       Line2D([], [], marker='o', ls='', color=TZ, ms=5, label=f'Tarifa Zero universal, sem grupo ({n("tz_sem")})'),
                       Line2D([], [], marker='o', ls='', color=TINTA, ms=5, label=f'Tarifa Zero universal com grupo presente ({n("tz_grupo")})')], ncol=1)
    salvar(fig, 'tese-r62-c8-mapa-barreira-simbiose')
    print('zonas', b.cat.value_counts().to_dict(), b[b.posicao.isin(['satelite', 'satélite', 'polo', 'co-polo'])].cat.value_counts().to_dict())

if __name__ == '__main__':
    for n in (sys.argv[1:] or list(R)): R[n]()
