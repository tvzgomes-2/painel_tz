# -*- coding: utf-8 -*-
"""figuras_r50.py — figuras que ficaram fora do Design System na r49, refeitas
no padrão de figuras_padrao.py (16 cm, Poppins, fundo branco, sem título ou
fonte dentro da imagem, cor com significado fixo).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni
Revisão r50 (10/10/2026).

Figuras (numeração da r49):
  Mapa 1     tese-cap2-07-mapa-indice-onibus      índice de indício (0–12), mesma conta de
                                                    figuras_familia_b.py (artigo ENANPUR), rampa rosa
  Mapa 4     tese-cap5-07-mapa-regua-camada2      gerada por figuras_padrao.c5_07 (corrigida)
  Figura 10  tese-cap6-04-componentes             valores TRANSCRITOS da figura de 24/07/2026
                                                    (o CSV disponível é de outra versão do universo)
  Gráfico 15 tese-cap6-05-concentracao-327        capital da tabela mestre; UF transcrita (Panorama ago/2026)
  Figura 11  tese-cap6-06-rede-socios-grupos      rede de sócios-hub (ars_rede_estendida_figuras_2026-10-08.py)
  Figura 12  tese-cap6-07-rede-estendida          rede estendida até o 3º nível (idem)
  Mapa 5     tese-cap6-08-mapa-agrupamentos       pequenos múltiplos, um mapa por agrupamento CL
  Figura 13  tese-cap6-09-cadeia-societaria       rodadas 2–5 conferidas em cadeia_cadastro.csv; a 1ª transcrita
  Figura 14  tese-cap6-10-comunidades             Barata e Comporte, Louvain (semente 0)

Regra de forma da ARS (estilo_rede do Design System): tipo de nó por forma e
preenchimento antes de cor; sócio pessoa física = círculo vazado; empresa = azul.
Nenhum CPF é lido para fora do script nem gravado.

Uso: DADOS=<raiz do cofre> SAIDA=<pasta> python figuras_r50.py [nome ...]
"""
import sys, os, re, json, collections, itertools, unicodedata, pickle, tempfile
from pathlib import Path
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, os.environ.get('SCRIPTS', str(AQUI)))
import figuras_padrao as fp
from figuras_padrao import (cor, NEUTROS, TINTA, TINTA2, FRACA, GRADE, EIXO, TZ, L, CM, br, fmt_eixo,
                            figura, legenda_topo, barra_h, barra_v, salvar, chapa, vazada, linha, U, D, OUT)
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle
from matplotlib.collections import LineCollection

FIG = {}
def fig_(f):
    FIG[f.__name__] = f
    return f

AZ = cor('azul', 700); AZ_ESC = cor('azul', 800); AZ_CLARO = cor('azul', 400)
CNPJ = D / 'CNPJ' / 'filtrados (6 CNAEs transporte, 24-07-2026)'
ARS = D / 'CNPJ' / 'ARS - métricas de rede (out-2026)'
MESTRE = U / '03 - Dados' / 'Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx'
TMP = Path(tempfile.gettempdir())


# ═════════════════════════════════════════════════════════════════════════
# Mapa 1 — índice de indício de sistema de ônibus (Cap. 2, Análise V)
# ═════════════════════════════════════════════════════════════════════════
def _indice():
    """Mesma conta de figuras_familia_b.py (Família B, 04/09/2026), sem alteração."""
    df = pd.read_csv(D / 'Base Municipal v3' / 'base_municipal_v3.csv', low_memory=False)
    num = lambda s: pd.to_numeric(s, errors='coerce')
    formal = df[['munic_concessao_2020', 'munic_permissao_2020', 'munic_autorizacao_2020',
                 'munic_prestacao_direta_2020']].eq(1).any(axis=1)
    A = np.where(df.munic_onibus_intramun_2020.eq(1),
                 np.where(formal, 4.0, np.where(df.munic_nao_regulamentado_2020.eq(1), 2.5, 4.0)), 0.0)
    r = num(df.vinculos_cnae_transporte_2022).fillna(0)
    B = np.select([r >= 200, r >= 50, r >= 10], [3.0, 2.0, 1.0], 0.0)
    o = num(df.n_pontos_onibus_osm).fillna(0)
    C = np.select([o >= 25, o >= 5], [2.0, 1.0], 0.0)
    Dd = (num(df.desp_tcu) > 0).astype(float)

    def q(s):
        c = s.dropna().quantile([.25, .5, .75]).values
        return s.apply(lambda v: 0.0 if pd.isna(v) else 0.25 if v <= c[0] else 0.5 if v <= c[1] else 0.75 if v <= c[2] else 1.0)
    pop = num(df.pop_2025).fillna(num(df.pop_2022))
    E = q(num(df.frota_onibus_2025) / pop * 1000)
    F = q(num(df.censo22_modal_onibus_pct))
    df['indice'] = A + B + C + Dd + E + F
    df['CD_MUN'] = df.cod_ibge.astype(str)
    return df[['CD_MUN', 'indice']]


@fig_
def mapa1_indice_onibus():
    import geopandas as gpd
    g = gpd.read_file(ARS / 'BR_municipios_2022_simpl.geojson')
    g = g.merge(_indice(), on='CD_MUN', how='left')
    FAIXAS = [(-0.01, 1, '0 a 1'), (1, 3, 'mais de 1 a 3'), (3, 5, 'mais de 3 a 5'),
              (5, 7, 'mais de 5 a 7'), (7, 9, 'mais de 7 a 9'), (9, 12, 'mais de 9 a 12')]
    CORES = [cor('grafite', 100), cor('rosa', 200), cor('rosa', 300), cor('rosa', 500), cor('rosa', 700), cor('rosa', 800)]
    g['f'] = pd.cut(g.indice, [f[0] for f in FAIXAS] + [12], labels=False)
    fig, ax = figura(14.2)
    hs = []
    for k, ((a, b, rot), c) in enumerate(zip(FAIXAS, CORES)):
        sub = g[g.f == k]
        sub.plot(ax=ax, color=c, edgecolor='white', linewidth=0.04, rasterized=True)
        hs.append(Patch(facecolor=c, edgecolor=cor('grafite', 300) if k == 0 else 'none', lw=0.5,
                        label=f'{rot} ({br(len(sub))})'))
    uf = json.load(open(D / 'espacial' / 'BR_UF_2022_simplificado.geojson', encoding='utf-8'))
    for f in uf['features']:
        gg = f['geometry']; polys = gg['coordinates'] if gg['type'] == 'MultiPolygon' else [gg['coordinates']]
        for p in polys:
            ax.add_patch(Polygon(np.array(p[0]), closed=True, fill=False, edgecolor=cor('grafite', 700), lw=0.45, zorder=3))
    ax.set_xlim(-74.2, -34.4); ax.set_ylim(-34.2, 5.6); ax.set_aspect('equal'); ax.axis('off')
    ax.legend(handles=hs, loc='lower left', title='índice (pontos de 0 a 12)', title_fontsize=7, fontsize=7,
              frameon=False, alignment='left', handlelength=1.4, handleheight=1.0)
    print('  sem índice:', int(g.indice.isna().sum()), '| contagem por faixa:', g.f.value_counts().sort_index().to_dict())
    salvar(fig, 'tese-cap2-07-mapa-indice-onibus')


# ═════════════════════════════════════════════════════════════════════════
# Figura 10 — componentes da rede de sócios (valores transcritos)
# ═════════════════════════════════════════════════════════════════════════
@fig_
def fig10_componentes():
    """Valores TRANSCRITOS da figura de 24/07/2026 (Distribuicao dos componentes da rede...).
    ⚠️ Conferir: o painel A soma 2.509 componentes com 2+ empresas e o C, 4.489; o B soma 68.938
    empresas e a nota de origem diz 67.138. Este script não muda número; a divergência fica para o autor."""
    faixas = ['1', '2', '3–5', '6–10', '11–20', '21–50', '51–100', '> 100']
    comp = [58066, 1629, 785, 69, 19, 5, 0, 2]
    emp = [58066, 7258, 2378, 492, 277, 163, 0, 304]
    ident = [('reconhecido\n(via sócio)', 10, AZ_ESC), ('tentativo\n(via empresa)', 3, cor('azul', 600)),
             ('sobrenome\nprovisório', 936, cor('azul', 300)), ('sem pista', 3537, cor('grafite', 300))]
    fig = plt.figure(figsize=(L * CM, 9.6 * CM), layout='constrained')
    sf = fig.subfigures(2, 1, height_ratios=[1.35, 1])
    a1, a2 = sf[0].subplots(1, 2)
    x = np.arange(len(faixas))
    for ax, v, tit, c in ((a1, comp, 'A · componentes por tamanho', AZ), (a2, emp, 'B · empresas por tamanho do componente', AZ)):
        ax.bar(x, [max(t, 0.0001) for t in v], 0.7, color=c, zorder=2)
        ax.set_yscale('log'); ax.set_ylim(0.8, 3e5)
        ax.set_yticks([1, 10, 100, 1000, 10000, 100000], ['1', '10', '100', '1.000', '10 mil', '100 mil'])
        ax.minorticks_off()
        for xi, t in zip(x, v):
            ax.text(xi, (t if t > 0 else 0.8) * 1.25, br(t), ha='center', va='bottom', fontsize=6.3, color=TINTA2)
        ax.set_xticks(x, faixas, fontsize=6.3); barra_v(ax)
        ax.set_xlabel('empresas no componente', fontsize=7)
        ax.set_title(tit, fontsize=8)
    a1.set_ylabel('componentes (escala log.)', fontsize=7); a2.set_ylabel('empresas (escala log.)', fontsize=7)
    a3 = sf[1].subplots()
    tot = sum(v for _, v, _ in ident)
    y = np.arange(len(ident))[::-1]
    for yi, (rot, v, c) in zip(y, ident):
        a3.barh(yi, v, 0.62, color=c, zorder=2)
        a3.text(v + 40, yi, f'{br(v)}  ({br(v / tot * 100, 1)}%)', va='center', fontsize=6.8, color=TINTA2)
    a3.set_yticks(y, [r.replace('\n', ' ') for r, _, _ in ident], fontsize=7)
    a3.set_xlim(0, 4300); fmt_eixo(a3, 'x', 0); barra_h(a3)
    a3.set_xlabel('componentes com duas empresas ou mais', fontsize=7)
    a3.set_title('C · situação de identificação dos componentes com duas empresas ou mais', fontsize=8)
    salvar(fig, 'tese-cap6-04-componentes')


# ═════════════════════════════════════════════════════════════════════════
# Gráfico 15 — concentração do capital dos 327 grupos
# ═════════════════════════════════════════════════════════════════════════
@fig_
def graf15_concentracao():
    """Capital: tabela mestre (12/08/2026), aba Resumo por grupo. UF predominante transcrita de
    figura_cap7_concentracao.py (Panorama quantitativo dos 327, ago/2026), sem alteração."""
    g = pd.read_excel(MESTRE, 'Resumo por grupo')
    c = np.sort(g.capital_social_total_reais.fillna(0).values)[::-1]
    cum = np.cumsum(c) / c.sum() * 100
    n = len(c); asc = np.sort(c); gini = (2 * np.sum(np.arange(1, n + 1) * asc) / (n * asc.sum())) - (n + 1) / n
    fig, (a1, a2) = figura(7.8, ncols=2)
    x = np.arange(1, n + 1)
    a1.plot([0, n], [0, 100], color=cor('grafite', 400), lw=0.8, ls=(0, (2, 2)), zorder=1)
    a1.plot(x, cum, color=AZ, lw=1.8, zorder=2)
    for k in (5, 10, 26, 50):
        a1.plot(k, cum[k - 1], 'o', color=AZ_ESC, ms=3.6, zorder=3)
        a1.annotate(f'{k} maiores: {br(cum[k - 1], 1)}%', (k, cum[k - 1]), xytext=(7, -2), textcoords='offset points',
                    ha='left', va='top', fontsize=6.8, color=TINTA2)
    a1.text(238, 60, 'igualdade\nperfeita', fontsize=6.5, color=FRACA, ha='left', va='top', linespacing=1.2)
    a1.set_xlim(0, 335); a1.set_ylim(0, 103); fmt_eixo(a1, 'y', 0, '%')
    a1.set_xlabel('grupos, do maior para o menor capital'); a1.set_ylabel('capital social acumulado')
    a1.set_title(f'A · concentração do capital (Gini {br(gini, 3)})')
    uf = pd.Series({'SP': 123, 'MG': 44, 'RJ': 28, 'RS': 23, 'BA': 15, 'PR': 13, 'SC': 11, 'PA': 11, 'GO': 10,
                    'PE': 9, 'MT': 7, 'ES': 7})
    y = np.arange(len(uf))[::-1]
    a2.barh(y, uf.values, 0.66, color=AZ, zorder=2)
    for yi, v in zip(y, uf.values):
        a2.text(v + 2, yi, str(v), va='center', fontsize=6.8, color=TINTA2)
    a2.set_yticks(y, uf.index, fontsize=7); a2.set_xlim(0, 135); barra_h(a2)
    a2.set_xlabel('grupos (UF predominante)'); a2.set_title('B · grupos por unidade da federação')
    print(f'  Gini {gini:.3f} | acumulado 1/5/10/26/50:', np.round(cum[[0, 4, 9, 25, 49]], 1))
    salvar(fig, 'tese-cap6-05-concentracao-327')


# ═════════════════════════════════════════════════════════════════════════
# Figura 13 — cadeia societária por rodada
# ═════════════════════════════════════════════════════════════════════════
@fig_
def fig13_cadeia():
    cad = pd.read_csv(CNPJ / 'cadeia_societaria' / 'cadeia_cadastro.csv', dtype=str)
    r = cad.rodada.astype(int).value_counts().sort_index()
    v = [1069] + [int(r.get(k, 0)) for k in (2, 3, 4, 5)]      # 1ª rodada transcrita (fora do CSV)
    fig, ax = figura(6.4)
    x = np.arange(1, 6)
    ax.bar(x, v, 0.62, color=AZ, zorder=2)
    for xi, t in zip(x, v):
        ax.text(xi, t * 1.2, br(t), ha='center', va='bottom', fontsize=7, color=TINTA2)
    ax.set_yscale('log'); ax.set_ylim(0.7, 4000); ax.minorticks_off()
    ax.set_yticks([1, 10, 100, 1000], ['1', '10', '100', '1.000'])
    ax.set_xticks(x, [f'{k}ª' for k in x]); barra_v(ax)
    ax.set_xlabel('rodada de expansão (camada de sócios pessoas jurídicas)')
    ax.set_ylabel('novas empresas (escala log.)')
    print('  rodadas:', v)
    salvar(fig, 'tese-cap6-09-cadeia-societaria')


# ═════════════════════════════════════════════════════════════════════════
# REDES (Figuras 11, 12 e 14; Mapa 5) — mesma reconstrução de
# ars_rede_estendida_figuras_2026-10-08.py e ars_metricas_rede_2026-10-08.py
# (método v4: núcleo sem consórcios, sócio = nome + documento mascarado,
# sem a qualificação 20). Só a forma muda.
# ═════════════════════════════════════════════════════════════════════════
import networkx as nx
_c = {}
HOLD1 = re.compile(r"PARTICIPA|HOLDING|EMPREEND|ADMINISTRA|INVEST|PATRIMON|GEST[AÃ]O|NEGOCIOS|NEGÓCIOS|CAPITAL|S/?A$")
HOLD2 = re.compile(r"PARTICIPA|HOLDING|EMPREEND|ADMINISTRA|INVEST|PATRIMON|GEST[AÃ]O|NEG[OÓ]CIOS|CAPITAL")
EXC = re.compile(r"ASSOCIA|SINDICAT|COOPERATIV|FEDERA[CÇ]|CONS[OÓ]RCIO")


def rede1():
    if 'r1' in _c: return _c['r1']
    comp = pd.read_csv(CNPJ / 'rede_nucleo_ativa_equity_componentes.csv', dtype=str); comp['cnpj_basico'] = comp.cnpj_basico.str.zfill(8)
    cons = comp.razao_social.str.upper().str.contains('CONSORCIO|CONSÓRCIO', regex=True)
    univ = set(comp.loc[~cons, 'cnpj_basico'])
    soc = pd.read_csv(CNPJ / 'socios_filtrado_6cnaes.csv', dtype=str); soc.columns = [c.strip() for c in soc.columns]
    soc['cnpj_basico'] = soc.cnpj_basico.str.zfill(8)
    sx = soc[soc.cnpj_basico.isin(univ) & (soc.qualificacao_socio != '20')].copy()
    sx['ident'] = sx.nome_socio_ou_razao_social.str.strip().str.upper() + '|' + sx.cnpj_cpf_socio.astype(str).str.strip()
    sx = sx[sx.ident.notna()]
    B = nx.Graph(); B.add_nodes_from(univ)
    for c, i in zip(sx.cnpj_basico, sx.ident): B.add_edge(c, 'S:' + i)
    G = nx.Graph(); G.add_nodes_from(univ); w = collections.Counter()
    for i, grp in sx.groupby('ident').cnpj_basico:
        for a, b in itertools.combinations(sorted(set(grp)), 2): w[(a, b)] += 1
    for (a, b), k in w.items(): G.add_edge(a, b, weight=k)
    E = pd.read_excel(MESTRE, sheet_name='Empresas', dtype=str); E['cnpj_basico'] = E.cnpj_basico.str.zfill(8)
    R = pd.read_excel(MESTRE, sheet_name='Resumo por grupo', dtype={'id_grupo': str})
    _c['r1'] = (B, G, sx[['cnpj_basico', 'ident', 'qualificacao_socio', 'tipo_socio']], E, R)
    print('  rede 1º nível: empresas', G.number_of_nodes(), 'arestas', G.number_of_edges(), 'sócios', sx.ident.nunique())
    return _c['r1']


def nome_grupo(R, n=18):
    def curto(v):
        t = str(v).split(' (')[0].replace(' Participacoes Ltda', '').replace(' Participacoes', '')
        if len(t) > n:
            t = t[:n].rsplit(' ', 1)[0] if ' ' in t[:n] else t[:n]
        return re.sub(r'\s+(Do|Da|De|Dos|Das|E|-)$', '', t.strip())
    return {k: curto(v) for k, v in zip(R.id_grupo, R.nome_grupo)}


def _cel(ax, H, x0, y0, lado, estilo, seed=1, it=60, k=None):
    """Desenha H dentro do quadrado [x0, x0+lado] × [y0-lado, y0] (cm), layout de molas com semente fixa."""
    n = H.number_of_nodes()
    if k is None and n > 30: k = 2.2 / np.sqrt(n)
    pos = nx.spring_layout(H, seed=seed, iterations=it if n <= 30 else max(it, 200), k=k)
    nodes = list(H); P = np.array([pos[v] for v in nodes])
    if n > 1:
        P = (P - P.min(0)) / np.maximum(np.ptp(P, 0).max(), 1e-9)
        esc = min(1.0, 0.3 + 0.17 * np.sqrt(n))       # grafo pequeno não estica até os cantos
        P = (P - P.max(0) / 2) * esc + 0.5
    else:
        P = P * 0 + 0.5
    m = lado * 0.08
    P = P * (lado - 2 * m); P[:, 0] += x0 + m; P[:, 1] = y0 - m - (lado - 2 * m) + P[:, 1]
    idx = {v: i for i, v in enumerate(nodes)}
    segs = [(P[idx[a]], P[idx[b]]) for a, b in H.edges()]
    ax.add_collection(LineCollection(segs, colors=cor('grafite', 300), linewidths=0.25 if n > 40 else 0.35, zorder=1))
    for t, (z, kw) in estilo(n).items():
        sel = [idx[v] for v in nodes if H.nodes[v]['t'] == t]
        if sel: ax.scatter(P[sel, 0], P[sel, 1], zorder=z, **kw)
    return P


def _tela(alt_cm):
    fig = plt.figure(figsize=(L * CM, alt_cm * CM))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, L); ax.set_ylim(-alt_cm, 0); ax.set_aspect('equal'); ax.axis('off')
    fig._tela_exata = True
    return fig, ax


def _cabeca(ax, y, texto):
    ax.text(0.05, y, texto, fontsize=7.3, color=TINTA2, va='bottom', ha='left', fontweight='medium')
    ax.plot([0.05, L - 0.05], [y - 0.12, y - 0.12], color=GRADE, lw=0.6)


def _legenda_tela(ax, y, itens, ncol):
    larg = (L - 0.1) / ncol
    for k, (rot, kw) in enumerate(itens):
        r, c = divmod(k, ncol); x = 0.15 + c * larg; yy = y - r * 0.45
        ax.scatter([x], [yy], **{**kw, 's': max(kw.get('s', 14), 14)})
        ax.text(x + 0.22, yy, rot, va='center', ha='left', fontsize=7, color=TINTA2)


# ── Figura 11 ────────────────────────────────────────────────────────────
@fig_
def fig11_rede_socios_grupos():
    B, G, s, E, R = rede1()
    nucleo = set(E.cnpj_basico) | set(G.nodes())
    def tipo(ident, t):
        if t != 'PJ': return 'PF'
        nome, doc = ident.split('|', 1); base = re.sub(r'\D', '', doc)[:8]
        if base in nucleo: return 'OP'
        if HOLD1.search(nome): return 'HOLD'
        return 'OUT'
    tp = {i: tipo(i, t) for i, t in zip(s.ident, s.tipo_socio)}
    gof = dict(zip(E.cnpj_basico, E.id_grupo))
    R = R.sort_values('capital_social_total_reais', ascending=False); ordem = list(R.id_grupo); nome = nome_grupo(R, 15)
    por_g = collections.defaultdict(list)
    for c, g in gof.items():
        if c in G: por_g[g].append(c)
    panels = []; n1 = 0; tipos = collections.Counter(); nv = 0
    for gid in ordem:
        cs = por_g.get(gid, [])
        if len(cs) < 2: continue
        sub = s[s.cnpj_basico.isin(cs)]
        cnt = sub.groupby('ident').cnpj_basico.nunique(); hubs = list(cnt[cnt >= 2].index)
        H = nx.Graph(); H.add_nodes_from(hubs)
        for c, grp in sub[sub.ident.isin(hubs)].groupby('cnpj_basico').ident:
            for a, b in itertools.combinations(sorted(set(grp)), 2): H.add_edge(a, b)
        for h in hubs: tipos[tp[h]] += 1; H.nodes[h]['t'] = tp[h]
        nv += H.number_of_edges()
        if len(hubs) < 2: n1 += 1; continue
        panels.append((gid, H))
    print('  Fig 11: painéis', len(panels), '| com 1 sócio-hub', n1, '| hubs', dict(tipos), sum(tipos.values()), '| ligações', nv)
    LAB = set(ordem[:26])
    A = [(g, H) for g, H in panels if g in LAB]; Bp = [(g, H) for g, H in panels if g not in LAB]
    PF_ = dict(facecolor='white', edgecolor=cor('grafite', 700))
    def estilo(n):
        s0 = 9 if n <= 12 else 6 if n <= 40 else 3.5
        lw = 0.6 if n <= 40 else 0.45
        return {'PF': (2, dict(s=s0, linewidths=lw, **PF_)),
                'HOLD': (3, dict(s=s0 * 1.3, color=AZ, linewidths=0)),
                'OP': (3, dict(s=s0 * 1.3, color=AZ_CLARO, linewidths=0)),
                'OUT': (3, dict(s=s0 * 1.3, color=cor('grafite', 500), linewidths=0))}
    def estilo_peq(n):
        s0 = 2.6 if n <= 12 else 1.6
        return {'PF': (2, dict(s=s0, linewidths=0.35, **PF_)),
                'HOLD': (3, dict(s=s0 * 1.4, color=AZ, linewidths=0)),
                'OP': (3, dict(s=s0 * 1.4, color=AZ_CLARO, linewidths=0)),
                'OUT': (3, dict(s=s0 * 1.4, color=cor('grafite', 500), linewidths=0))}
    NA, LA = 7, (L - 0.1) / 7          # seção A: 7 colunas
    NB, LB = 20, (L - 0.1) / 20        # seção B: 20 colunas
    ra = -(-len(A) // NA); rb = -(-len(Bp) // NB)
    alt = 1.05 + 0.55 + ra * (LA + 0.42) + 0.6 + rb * LB + 0.1
    fig, ax = _tela(alt)
    _legenda_tela(ax, -0.25, [(f'sócio pessoa física ({br(tipos["PF"])})', dict(s=14, linewidths=0.8, **PF_)),
                              (f'holding ou empresa de participações ({tipos["HOLD"]})', dict(s=16, color=AZ)),
                              (f'operadora sócia de operadora ({tipos["OP"]})', dict(s=16, color=AZ_CLARO)),
                              (f'outra pessoa jurídica ({tipos["OUT"]})', dict(s=16, color=cor('grafite', 500)))], ncol=2)
    y = -1.05 - 0.4
    _cabeca(ax, y, f'grupos entre os 26 de maior capital ({len(A)} com dois sócios-hub ou mais), em ordem de capital')
    y -= 0.2
    for k, (gid, H) in enumerate(A):
        r, c = divmod(k, NA)
        x0 = 0.05 + c * LA; y0 = y - r * (LA + 0.42)
        _cel(ax, H, x0, y0, LA, estilo)
        ax.text(x0 + LA / 2, y0 - LA - 0.02, f'{gid} {nome[gid]}', ha='center', va='top', fontsize=5.4, color=TINTA2)
    y = y - ra * (LA + 0.42) - 0.35
    _cabeca(ax, y, f'demais grupos ({len(Bp)}), em ordem de capital')
    y -= 0.15
    for k, (gid, H) in enumerate(Bp):
        r, c = divmod(k, NB)
        _cel(ax, H, 0.05 + c * LB, y - r * LB, LB, estilo_peq)
    salvar(fig, 'tese-cap6-06-rede-socios-grupos')


# ── rede estendida (Figura 12 e Mapa 5) ──────────────────────────────────
def rede_estendida():
    if 'X' in _c: return _c['X']
    B, G, s, E, R = rede1()
    gof = dict(zip(E.cnpj_basico, E.id_grupo)); nucleo = set(G.nodes())
    cnt = s.groupby('ident').cnpj_basico.nunique()
    pj = s[s.tipo_socio == 'PJ'].ident.unique()
    base = lambda i: re.sub(r'\D', '', i.split('|', 1)[1])[:8]
    hold = [i for i in pj if cnt[i] >= 2 and base(i) not in nucleo and HOLD2.search(i.split('|')[0])]
    hb = {base(i): i for i in hold}
    X = nx.Graph()
    for c, i in zip(s.cnpj_basico, s.ident): X.add_edge('E:' + c, 'S:' + i)
    s2 = pd.read_csv(CNPJ / 'socios_segunda_camada.csv', dtype=str); s2['cnpj_basico'] = s2.cnpj_basico.str.zfill(8)
    s2 = s2[s2.cnpj_basico.isin(hb) & (s2.qualificacao_socio != '20') & s2.nome_socio_ou_razao_social.notna()]
    s2['ident'] = s2.nome_socio_ou_razao_social.str.strip().str.upper() + '|' + s2.cnpj_cpf_socio.astype(str).str.strip()
    s2 = s2[~s2.nome_socio_ou_razao_social.str.upper().str.contains(EXC)]
    for h, i in zip(s2.cnpj_basico, s2.ident): X.add_edge('S:' + hb[h], 'S2:' + i)
    lv2 = set(s2.ident)
    e2b = pd.read_csv(CNPJ / 'empresas_ligadas_holdings_qualquer_setor.csv', dtype=str); e2b['cnpj_basico'] = e2b.cnpj_basico.str.zfill(8)
    e2b = e2b[~e2b.razao_social.str.upper().str.contains(EXC)]
    setor = dict(zip(e2b.cnpj_basico, e2b.setor))
    raw = pd.read_csv(ARS / 'socios_empresas_nivel2b_bruto.csv', sep=';', header=None, dtype=str)
    raw.columns = ['cnpj_basico', 'tipo', 'nome', 'doc', 'qualif', 'data', 'pais', 'rep', 'nomerep', 'qrep', 'faixa']
    raw['cnpj_basico'] = raw.cnpj_basico.str.zfill(8)
    raw = raw[raw.cnpj_basico.isin(setor) & (raw.qualif != '20') & raw.nome.notna()]
    raw['ident'] = raw.nome.str.strip().str.upper() + '|' + raw.doc.astype(str).str.strip()
    lig = raw[raw.ident.isin(lv2)]
    for c, i in zip(lig.cnpj_basico, lig.ident): X.add_edge('S2:' + i, 'E2:' + c)
    emp2b = set(lig.cnpj_basico)
    r3 = raw[raw.cnpj_basico.isin(emp2b) & ~raw.ident.isin(lv2)]
    c3 = r3.groupby('ident').cnpj_basico.nunique(); hub3 = set(c3[c3 >= 2].index)
    for c, i in zip(r3.cnpj_basico, r3.ident):
        if i in hub3: X.add_edge('E2:' + c, 'S3:' + i)
    print('  rede estendida: holdings-hub', len(hold), '| sócios nível 2', len(lv2), '| empresas ligadas', len(emp2b), '| sócios nível 3', len(hub3))
    _c['X'] = (X, setor, gof, R, E)
    return _c['X']


@fig_
def fig12_rede_estendida():
    X, setor, gof, R, E = rede_estendida()
    nome = nome_grupo(R, 14)
    def cat(n):
        if n.startswith('E:'): return 'op'
        if n.startswith('S:'): return 's1'
        if n.startswith('S2:') or n.startswith('S3:'): return 's23'
        st = setor.get(n[3:], '')
        return 'fin' if st == 'Serviços financeiros' else ('trp' if st == 'Transporte terrestre' else 'out')
    isl = []
    for c in nx.connected_components(X):
        if not any(n.startswith('E2:') for n in c): continue
        gs = collections.Counter(gof[n[2:]] for n in c if n.startswith('E:') and isinstance(gof.get(n[2:]), str))
        if not gs: continue
        isl.append((len(c), c, gs))
    isl.sort(key=lambda t: -t[0])
    fus = [t for t in isl if len(t[2]) >= 2]; resto = [t for t in isl if len(t[2]) < 2]
    print('  Fig 12: ilhas que cresceram', len(isl), '| com 2+ grupos', len(fus), [t[0] for t in fus])
    cats = collections.Counter(cat(n) for _, c, _ in isl for n in c)
    PF_ = dict(facecolor='white')
    def estilo(n, f=1.0):
        a = f * (1.0 if n < 120 else 0.7)
        return {'s23': (2, dict(s=4 * a, linewidths=0.35, edgecolor=cor('grafite', 400), **PF_)),
                's1': (2, dict(s=6 * a, linewidths=0.5, edgecolor=cor('grafite', 800), **PF_)),
                'out': (3, dict(s=5 * a, color=cor('grafite', 300), linewidths=0)),
                'trp': (3, dict(s=7 * a, color=AZ_CLARO, linewidths=0)),
                'op': (4, dict(s=10 * a, color=AZ, linewidths=0)),
                'fin': (5, dict(s=13 * a, color=cor('verde', 700), linewidths=0))}
    import textwrap
    def rot(n, gs, larg_cm, k=3):
        g = ' + '.join(f'{x} {nome[x]}' for x, _ in gs.most_common(k)) + (' …' if len(gs) > k else '')
        return '\n'.join(textwrap.wrap(f'{g} ·\u00a0{n}\u00a0nós', int(larg_cm * 7.2)))
    # seção A: as ilhas que fundem grupos — linha 1 com as duas maiores, linha 2 com as demais
    l1, l2 = fus[:2], fus[2:]
    W1 = (L - 0.3) / 2; W2 = (L - 0.3) / max(3, len(l2))
    H1, H2 = 5.5, 3.7
    NB = 11; LB = (L - 0.1) / NB; rb = -(-len(resto) // NB)
    alt = 1.5 + 0.4 + H1 + 0.5 + H2 + 0.75 + 0.55 + rb * (LB + 0.34) + 0.1
    fig, ax = _tela(alt)
    _legenda_tela(ax, -0.25, [(f'operadora do recorte ({br(cats["op"])})', dict(s=18, color=AZ)),
                              (f'sócio de operadora, 1º nível ({br(cats["s1"])})', dict(s=14, facecolor='white', edgecolor=cor('grafite', 800), linewidths=0.8)),
                              (f'empresa ligada: serviços financeiros ({br(cats["fin"])})', dict(s=18, color=cor('verde', 700))),
                              (f'sócio de holding ou de empresa ligada, 2º e 3º níveis ({br(cats["s23"])})', dict(s=10, facecolor='white', edgecolor=cor('grafite', 400), linewidths=0.6)),
                              (f'empresa ligada: transporte fora do recorte ({br(cats["trp"])})', dict(s=16, color=AZ_CLARO)),
                              (f'empresa ligada: outro setor ({br(cats["out"])})', dict(s=14, color=cor('grafite', 300)))], ncol=2)
    y = -1.5 - 0.35
    _cabeca(ax, y, f'ilhas que juntam dois grupos ou mais ({len(fus)})')
    y -= 0.15
    for k, (n, c, gs) in enumerate(l1):
        H = X.subgraph(c).copy()
        for v in H: H.nodes[v]['t'] = cat(v)
        x0 = 0.1 + k * (W1 + 0.1)
        _cel(ax, H, x0 + (W1 - H1) / 2, y, H1 - 0.35, lambda m: estilo(m, 1.0), seed=2, it=80)
        ax.text(x0 + W1 / 2, y - H1 + 0.3, rot(n, gs, W1), ha='center', va='top', fontsize=6, color=TINTA2, linespacing=1.3)
    y -= H1 + 0.45
    for k, (n, c, gs) in enumerate(l2):
        H = X.subgraph(c).copy()
        for v in H: H.nodes[v]['t'] = cat(v)
        x0 = 0.1 + k * (W2 + 0.05)
        _cel(ax, H, x0 + (W2 - (H2 - 0.35)) / 2, y, H2 - 0.35, lambda m: estilo(m, 1.0), seed=2, it=80)
        ax.text(x0 + W2 / 2, y - H2 + 0.3, rot(n, gs, W2 - 0.2), ha='center', va='top', fontsize=6, color=TINTA2, linespacing=1.3)
    y -= H2 + 0.8
    _cabeca(ax, y, f'ilhas de um grupo só que cresceram além do 1º nível ({len(resto)}), em ordem de tamanho')
    y -= 0.15
    for k, (n, c, gs) in enumerate(resto):
        H = X.subgraph(c).copy()
        for v in H: H.nodes[v]['t'] = cat(v)
        r, cc = divmod(k, NB)
        x0 = 0.05 + cc * LB; y0 = y - r * (LB + 0.34)
        _cel(ax, H, x0, y0, LB, lambda m: estilo(m, 0.75), seed=2, it=60)
        g = gs.most_common(1)[0][0]
        ax.text(x0 + LB / 2, y0 - LB + 0.02, f'{g} · {n}', ha='center', va='top', fontsize=5.2, color=TINTA2)
    salvar(fig, 'tese-cap6-07-rede-estendida')


# ── Mapa 5 ────────────────────────────────────────────────────────────────
@fig_
def mapa5_agrupamentos():
    import geopandas as gpd
    E = pd.read_excel(MESTRE, sheet_name='Empresas', dtype=str)
    C = pd.read_excel(MESTRE, sheet_name='Resumo por cluster', dtype=str)
    FUS = sorted(C[C.fusao_de_2plus_grupos.astype(str) == 'True'].cluster_id)
    g = gpd.read_file(ARS / 'BR_municipios_2022_simpl.geojson')
    def nz(t):
        t = unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode().upper()
        return re.sub(r'[^A-Z ]', '', t.replace('-', ' ')).strip()
    g['k'] = g.NM_MUN.map(nz) + '/' + g.SIGLA_UF
    key = set(g.k); E = E[E.id_grupo.notna()]
    cl = collections.defaultdict(set); grp = collections.defaultdict(set)
    for _, r in E.iterrows():
        for m in str(r.municipios_atuacao).split(';'):
            m = re.sub(r'\s*\(.*?\)', '', m).strip()
            if '/' not in m: continue
            n, uf = m.rsplit('/', 1); k = nz(n) + '/' + uf.strip()
            if k not in key: continue
            grp[k].add(r.id_grupo)
            if r.cluster_id in FUS: cl[k].add(r.cluster_id)
    LAB = {'CL-01': 'Barata + JAL', 'CL-02': 'Comporte + Lessa Carvalho + Rodap + 5 holdings',
           'CL-03': 'Belarmino + Weipar', 'CL-05': 'Gulin + Senestra + Transguara + Stabile + AGPS',
           'CL-06': 'Nossa Senhora do Ó + Del Rey', 'CL-09': 'Terra + Sunpass', 'CL-12': 'Nova Suissa + Guimarães Lopes'}
    n = {c: sum(c in v for v in cl.values()) for c in FUS}
    n2 = sum(len(v) > 1 for v in cl.values())
    print('  Mapa 5: municípios com grupo', len(grp), '| com agrupamento', len(cl), '| 2+', n2, n)
    ufg = g[['SIGLA_UF', 'geometry']].copy(); ufg['geometry'] = ufg.buffer(0.02)
    ufg = ufg.dissolve('SIGLA_UF'); ufg['geometry'] = ufg.buffer(-0.02).simplify(0.02)
    tem_g = g[g.k.isin(grp)]
    paineis = [(c, f'{c} · {LAB[c]}', g[g.k.map(lambda k: c in cl.get(k, ()))], n[c]) for c in FUS]
    paineis.append(('2+', 'dois agrupamentos ou mais', g[g.k.map(lambda k: len(cl.get(k, ())) > 1)], n2))
    fig, axs = figura(10.6, ncols=4, nrows=2)
    for ax, (c, tit, sub, nn) in zip(axs.flat, paineis):
        tem_g.plot(ax=ax, color=cor('grafite', 200), edgecolor='none', rasterized=True)
        ufg.boundary.plot(ax=ax, color=cor('grafite', 400), linewidth=0.25)
        sub.plot(ax=ax, color=AZ if c != '2+' else NEUTROS['tinta'], edgecolor=AZ if c != '2+' else NEUTROS['tinta'],
                 linewidth=0.25, rasterized=True)
        ax.set_xlim(-74.2, -34.4); ax.set_ylim(-34.2, 5.6); ax.set_aspect('equal'); ax.axis('off')
        import textwrap
        ax.set_title('\n'.join(textwrap.wrap(tit, 26)) + f'\n{nn} municípios', fontsize=6.6, loc='left', pad=2, linespacing=1.25)
    legenda_topo(fig, [chapa('município do agrupamento', AZ), chapa('em dois agrupamentos ou mais', NEUTROS['tinta']),
                       chapa(f'só grupos fora dos agrupamentos ({len(set(grp) - set(cl))})', cor('grafite', 200))])
    salvar(fig, 'tese-cap6-08-mapa-agrupamentos')


# ── Figura 14 ────────────────────────────────────────────────────────────
def _layout_comunidades(H, com, seed=3):
    """Layout em dois tempos: centros das comunidades (rede de comunidades, Kamada-Kawai) afastados até
    não se sobreporem; dentro de cada uma, molas com semente fixa num disco de raio ∝ raiz do tamanho."""
    cm = {x: k for k, c in enumerate(com) for x in c}
    Q = nx.Graph(); Q.add_nodes_from(range(len(com)))
    for a, b in H.edges():
        if cm[a] != cm[b]:
            w = Q.get_edge_data(cm[a], cm[b], {'weight': 0})['weight']; Q.add_edge(cm[a], cm[b], weight=w + 1)
    pq = nx.kamada_kawai_layout(Q, weight=None) if len(com) > 1 and nx.is_connected(Q) else nx.spring_layout(Q, seed=seed)
    rad = {k: 0.17 * np.sqrt(len(c)) for k, c in enumerate(com)}
    C = {k: np.array(v) for k, v in pq.items()}
    fat = 1.0
    for i, j in itertools.combinations(range(len(com)), 2):
        d = np.linalg.norm(C[i] - C[j])
        fat = max(fat, (rad[i] + rad[j] + 0.75) / max(d, 1e-6))
    pos = {}
    for k, c in enumerate(com):
        sub = H.subgraph(c)
        p = nx.spring_layout(sub, seed=seed, iterations=200) if len(c) > 1 else {next(iter(c)): np.zeros(2)}
        A = np.array(list(p.values())); A = A - A.mean(0); m = np.abs(A).max() or 1
        for v, xy in zip(p, A / m * rad[k]):
            pos[v] = C[k] * fat + xy
    return pos
@fig_
def fig14_comunidades():
    from shapely.geometry import MultiPoint
    B, G, s, E, R = rede1()
    e = pd.read_csv(ARS / 'ars_metricas_empresas.csv', dtype={'cnpj_basico': str})
    bt = dict(zip(e.cnpj_basico, e.intermediacao))
    fig, axs = figura(8.6, ncols=2)
    for ax, (gid, tit) in zip(axs, [('GE-001', 'A · Barata (51 empresas)'), ('GE-005', 'B · Comporte (20 empresas)')]):
        cs = sorted(e.loc[e.id_grupo == gid, 'cnpj_basico'])
        H = nx.Graph(); H.add_nodes_from(cs)                  # ordem fixa: o Louvain depende da ordem dos nós
        H.add_edges_from(sorted((min(a, b), max(a, b), d) for a, b, d in G.subgraph(cs).edges(data=True)))
        part = [nx.community.louvain_communities(H, weight='weight', seed=k) for k in range(20)]
        mods = [nx.community.modularity(H, c, weight='weight') for c in part]
        com = sorted(part[int(np.argmax(mods))], key=len, reverse=True)   # partição de maior modularidade em 20 sementes
        print(f'  {gid}: comunidades por semente {sorted(collections.Counter(len(c) for c in part).items())}, escolhida {len(com)}')
        cm = {x: k for k, c in enumerate(com) for x in c}
        pos = _layout_comunidades(H, com, seed=3)
        P = np.array([pos[x] for x in H]); P0 = P - P.mean(0)
        _, _, Vt = np.linalg.svd(P0, full_matrices=False)          # eixo maior na horizontal
        pos = {x: v @ Vt.T for x, v in zip(H, P0)}
        P = np.array(list(pos.values())); span = np.ptp(P, 0).max()
        r0 = span * 0.03
        cen = {}
        for k, c in enumerate(com):
            pts = MultiPoint([pos[x] for x in c]); hull = pts.convex_hull.buffer(r0 * 1.6, resolution=12)
            ax.add_patch(Polygon(np.array(hull.exterior.coords), closed=True, facecolor=cor('grafite', 100),
                                 edgecolor=cor('grafite', 300), lw=0.5, zorder=1))
            cen[k] = np.array([hull.centroid.x, hull.centroid.y])
            ax.text(cen[k][0], hull.bounds[3] + r0 * 0.4, str(k + 1), ha='center', va='bottom', fontsize=6.2, color=FRACA, zorder=6)
        par = collections.Counter(tuple(sorted((cm[a], cm[b]))) for a, b in H.edges() if cm[a] != cm[b])
        for (i, j), nij in par.items():
            ax.plot(*zip(cen[i], cen[j]), color=AZ, lw=0.7 + 0.55 * np.sqrt(nij), solid_capstyle='round', zorder=0.5)
            mx, my = (cen[i] + cen[j]) / 2
            ax.text(mx, my, str(nij), ha='center', va='center', fontsize=5.8, color=AZ, zorder=2.5,
                    bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none'))
        dentro = [(a, b) for a, b in H.edges() if cm[a] == cm[b]]
        nx.draw_networkx_edges(H, pos, edgelist=dentro, ax=ax, edge_color=cor('grafite', 400), width=0.5)
        nx.draw_networkx_nodes(H, pos, ax=ax, node_color=AZ_CLARO, edgecolors='white', linewidths=0.5,
                               node_size=[14 + 520 * bt.get(x, 0) for x in H]).set_zorder(3)
        mod = nx.community.modularity(H, com, weight='weight')
        ax.set_title(f'{tit}\n{len(com)} comunidades · modularidade {br(mod, 2)} · densidade {br(nx.density(H), 2)}',
                     fontsize=7.4, linespacing=1.4)
        ax.set_aspect('equal', adjustable='datalim'); ax.set_anchor('N'); ax.axis('off'); ax.margins(0.06)
    hs = [Patch(facecolor=cor('grafite', 100), edgecolor=cor('grafite', 300), lw=0.5, label='comunidade (Louvain), numerada'),
          Line2D([], [], color=cor('grafite', 400), lw=0.8, label='sócio em comum dentro da comunidade'),
          Line2D([], [], color=AZ, lw=2.0, label='ligações entre comunidades (número de pares de empresas)'),
          Line2D([], [], marker='o', ls='', color=AZ_CLARO, mec='white', ms=7, label='empresa (tamanho: intermediação)')]
    legenda_topo(fig, hs, ncol=2)
    salvar(fig, 'tese-cap6-10-comunidades')


if __name__ == '__main__':
    alvo = sys.argv[1:] or list(FIG)
    for n in alvo:
        FIG[n]()
