# -*- coding: utf-8 -*-
"""figuras_r65.py — figuras da revisão r65 (Cap. 8 reestruturado), no padrão de figuras_padrao.py.
  tese-r65-c8-bruto-ajustado : taxa bruta de adoção com e sem grupo por posição no arranjo, e a razão de chances ajustada
  tese-r65-c8-lisa           : LISA da Tarifa Zero universal (A) e LISA bivariado Tarifa Zero × grupo na vizinhança (B)
  tese-r65-c8-sp-gw          : coeficiente local da presença de grupo na GW logística de SP (base de 11/10/2026)
  tese-r65-c8-linha-tempo    : adoções da Tarifa Zero universal por ano e forma de entrada; fins e recuos
  tese-r65-c8-preco          : preço do quilômetro (reais de maio de 2026) × CadTerc, por forma de entrada (A); custo por habitante (B)
Base: congelada de 11/10/2026. Uso (na raiz do cofre): python "_meta/scripts/figuras_r65.py" [nome ...]
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import os, sys, re, json
os.environ.setdefault('TZ_RETRATO', '2026-10-11')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figuras_padrao as fp
from figuras_padrao import *   # noqa
import numpy as np, pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
R = {}
def reg(f): R[f.__name__] = f; return f
TN = D / 'Análise espacial GE x TZ (out-2026, teste nacional)'
BASE = D / 'congelamento-2026-10-11' / 'Municípios TZ - consolidado.xlsx'
GRP = cor('azul', 700); GRP_L = cor('azul', 300); SEM = cor('grafite', 400)

def classe(x):
    t = str(x).strip().lower() if pd.notna(x) else ''
    if not t or t.startswith(('não encontrado', 'não apurado', 'a apurar')): return 'nd'
    if re.search(r'locação|locado', t): return 'locacao'
    if t.startswith('contrat'): return 'aditivo' if re.search(r'aditivo|aditamento|adendo', t) else 'contrato'
    if re.search(r'prestação direta|execução direta|empresa pública|autarquia', t): return 'direta'
    if re.search(r'aditivo|aditamento|adendo', t): return 'aditivo'
    if t.startswith('concessão'): return 'concessao'
    return 'contrato'

# ── taxa bruta × razão de chances ajustada ─────────────────────────────────
@reg
def r65_c8_bruto_ajustado():
    J = json.load(open(TN / 'resultados_final.json', encoding='utf-8'))
    tb = J['taxas brutas A (UFs com adoção)']
    def frac(k):
        a, b = re.match(r'(\d+)/(\d+)', tb[k]).groups(); return int(a), int(b)
    pos = [('isolado', ['isolado']), ('satélite', ['satelite']), ('polo e co-polo', ['polo', 'co-polo'])]
    orr = J['A posição · ge_multi']['por_posicao']; keyor = {'isolado': 'isolado', 'satélite': 'satélite', 'polo e co-polo': 'polo/co-polo'}
    fig, (a1, a2) = figura(7.4, ncols=2, gridspec_kw={'width_ratios': [1.35, 1]})
    x = np.arange(len(pos)); w = 0.36
    for j, (lab, ks) in enumerate(pos):
        for g, dx, c in ((0, -w / 2, SEM), (1, w / 2, GRP)):
            n = sum(frac(f'{k} | grupo={g}')[0] for k in ks); d = sum(frac(f'{k} | grupo={g}')[1] for k in ks)
            v = 100 * n / d
            a1.bar(j + dx, v, w * 0.92, color=c)
            a1.text(j + dx, v + 0.2, f'{n}/{br(d)}', ha='center', va='bottom', fontsize=6.2, color=TINTA2)
            a1.text(j + dx, v + 0.95, br(v, 1) + '%', ha='center', va='bottom', fontsize=7)
    a1.set_xticks(x, [p for p, _ in pos]); barra_v(a1); fmt_eixo(a1, 'y', 0, '%')
    a1.set_ylim(0, 14); a1.set_title('A. Taxa bruta de adoção', fontsize=8.5)
    for j, (lab, _) in enumerate(pos):
        r = orr[keyor[lab]]; c = GRP if r['p'] < 0.05 else SEM
        a2.plot([r['ic_inf'], r['ic_sup']], [j, j], color=c, lw=1.6); a2.plot(r['OR'], j, 'o', color=c, ms=5.5)
        a2.text(r['ic_sup'] * 1.12, j, f"{br(r['OR'], 2)} ({br(r['ic_inf'], 2)}–{br(r['ic_sup'], 2)})", va='center', fontsize=7)
    a2.axvline(1, color=EIXO, lw=0.9); a2.set_xscale('log'); a2.set_xlim(0.08, 12)
    a2.set_xticks([0.1, 0.25, 0.5, 1, 2, 4], ['0,1', '0,25', '0,5', '1', '2', '4']); a2.minorticks_off()
    a2.set_yticks(range(len(pos)), [p for p, _ in pos]); a2.invert_yaxis(); barra_h(a2)
    a2.set_title('B. Razão de chances ajustada', fontsize=8.5); a2.set_xlabel('com controles (escala log)')
    legenda_topo(fig, [chapa('sem empresa de grupo', SEM), chapa('com empresa de grupo', GRP)])
    salvar(fig, 'tese-r65-c8-bruto-ajustado')

# ── LISA nacional ──────────────────────────────────────────────────────────
@reg
def r65_c8_lisa():
    import geopandas as gpd
    from libpysal.weights import KNN
    import esda
    b = pd.read_csv(TN / 'base_teste_nacional.csv'); b = b[b.parcial != 1].copy()
    b = b.merge(fp.pontos(), left_on='cod_ibge', right_on='CD_MUN', how='left').dropna(subset=['lon'])
    g = gpd.GeoDataFrame(b, geometry=gpd.points_from_xy(b.lon, b.lat), crs=4326).to_crs(5880).reset_index(drop=True)
    w = KNN.from_dataframe(g, k=8); w.transform = 'r'
    y = g.y_univ.values.astype(float); x = g.ge_multi.values.astype(float)
    gm = esda.Moran(y, w, permutations=999); bv = esda.Moran_BV(y, x, w, permutations=999)
    li = esda.Moran_Local(y, w, permutations=999, seed=1)
    lb = esda.Moran_Local_BV(y, x, w, permutations=999, seed=1)
    g['q'] = li.q; g['p'] = li.p_sim; g['qb'] = lb.q; g['pb'] = lb.p_sim
    fig, axs = figura(9.0, ncols=2)
    hh = g[(g.q == 1) & (g.p < 0.05)]; hb = g[(g.qb == 1) & (g.pb < 0.05)]; hl = g[(g.qb == 4) & (g.pb < 0.05)]
    tz = g[g.y_univ == 1]
    mapa_base(axs[0]); axs[0].scatter(tz.lon, tz.lat, s=5, color=TZ, lw=0, zorder=2)
    axs[0].scatter(hh.lon, hh.lat, s=16, facecolor='none', edgecolor=TINTA, lw=0.6, zorder=3)
    axs[0].set_title('A. Agrupamento da Tarifa Zero universal')
    mapa_base(axs[1]); axs[1].scatter(hb.lon, hb.lat, s=10, color=GRP, lw=0, zorder=3)
    axs[1].scatter(hl.lon, hl.lat, s=10, color=TZ, lw=0, zorder=4)
    axs[1].set_title('B. Tarifa Zero e grupo na vizinhança')
    legenda_topo(fig, [Line2D([], [], marker='o', ls='', color=TZ, ms=4, label='Tarifa Zero universal'),
                       Line2D([], [], marker='o', ls='', mfc='none', mec=TINTA, ms=5, label=f'agrupamento alto-alto, p < 0,05 ({len(hh)})'),
                       Line2D([], [], marker='o', ls='', color=GRP, ms=4, label=f'B: com Tarifa Zero e grupo nos vizinhos ({len(hb)})'),
                       ] + ([Line2D([], [], marker='o', ls='', color=TZ, ms=4, label=f'B: com Tarifa Zero e vizinhos sem grupo ({len(hl)})')] if len(hl) else []), ncol=2)
    salvar(fig, 'tese-r65-c8-lisa')
    out = dict(n=len(g), moran_tz=[round(gm.I, 4), round(gm.p_sim, 4)], moran_bv=[round(bv.I, 4), round(bv.p_sim, 4)],
               hh=len(hh), bv_hh=len(hb), bv_hl=len(hl), hh_uf=hh.uf.value_counts().to_dict(), bvhh_uf=hb.uf.value_counts().to_dict(), bvhl_uf=hl.uf.value_counts().to_dict(),
               hh_pos=hh.posicao.value_counts().to_dict(), bvhh_pos=hb.posicao.value_counts().to_dict(), bvhl_pos=hl.posicao.value_counts().to_dict())
    json.dump(out, open(TN / 'lisa_r65.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str); print(out)

# ── GW logística de SP (base de 11/10) ─────────────────────────────────────
@reg
def r65_c8_sp_gw():
    import geopandas as gpd
    from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
    g = gpd.read_file(D / 'Análise espacial GE x TZ (out-2026, teste SP, base 11-10)' / 'sp_resultados.geojson')
    cm = LinearSegmentedColormap.from_list('div', [cor('azul', 700), cor('azul', 200), '#FFFFFF', cor('grafite', 200), cor('grafite', 600)])
    fig, ax = figura(10.5)
    g.plot(column='b_ge_multi', ax=ax, cmap=cm, norm=TwoSlopeNorm(0, vmin=-1.5, vmax=1.5), edgecolor='white', linewidth=0.15)
    g[g.sig_ge_multi == 1].boundary.plot(ax=ax, color=TINTA, linewidth=0.55)
    c = g[g.tz_univ == 1].representative_point(); ax.scatter(c.x, c.y, s=7, color=TZ, edgecolor='white', lw=0.3, zorder=5)
    ax.set_aspect('equal'); ax.axis('off')
    sm_ = plt.cm.ScalarMappable(norm=TwoSlopeNorm(0, vmin=-1.5, vmax=1.5), cmap=cm)
    cb = fig.colorbar(sm_, ax=ax, orientation='horizontal', fraction=0.035, pad=0.02, aspect=40)
    cb.set_label('coeficiente local da presença de grupo (log da razão de chances)', fontsize=7); cb.ax.tick_params(labelsize=7)
    cb.set_ticks([-1.5, -1, -0.5, 0, 0.5, 1, 1.5], labels=['−1,5', '−1', '−0,5', '0', '0,5', '1', '1,5'])
    legenda_topo(fig, [Line2D([], [], marker='o', ls='', color=TZ, ms=4, label='Tarifa Zero universal'),
                       Patch(facecolor='none', edgecolor=TINTA, lw=0.8, label=f'coeficiente significativo ({int(g.sig_ge_multi.sum())} municípios)')])
    salvar(fig, 'tese-r65-c8-sp-gw')

# ── linha do tempo ─────────────────────────────────────────────────────────
@reg
def r65_c8_linha_tempo():
    m = pd.read_excel(BASE, sheet_name='consolidado')
    e = m[m['Situação'].isin(['Ativa', 'Encerrada'])].copy()
    e['ano'] = pd.to_numeric(e['Ano início'].astype(str).str.extract(r'(\d{4})')[0], errors='coerce')
    u = e[(e['Régua — aba'] == '1 Universal') | (e['Situação'] == 'Encerrada') | (e['Município'] == 'Monte Mor')].copy()
    u = u[~((u['Município'] == 'Paulínia'))]  # fase universal 1995–1997 entra à parte
    u['f'] = u['Prestação (eixo 2)'].map(classe).map({'direta': 'pub', 'contrato': 'nova', 'concessao': 'nova', 'locacao': 'nova', 'aditivo': 'adit', 'nd': 'nd'})
    anos = list(range(1990, 2027)); C = {k: [int(((u.ano == a) & (u.f == k)).sum()) for a in anos] for k in ('pub', 'nova', 'adit', 'nd')}
    C['nd'][anos.index(1995)] += 1  # Paulínia: fase universal de 1995 (forma de entrada não lida)
    fig, ax = figura(7.6)
    bot = np.zeros(len(anos)); cores = {'pub': cor('grafite', 500), 'nova': cor('azul', 300), 'adit': GRP, 'nd': cor('grafite', 200)}
    lab = {'pub': 'operação pública', 'nova': 'contrato novo, concessão nova ou locação', 'adit': 'aditivo à concessão existente', 'nd': 'forma de entrada não apurada'}
    for k in ('adit', 'nova', 'pub', 'nd'):
        ax.bar(anos, C[k], 0.75, bottom=bot, color=cores[k]); bot += np.array(C[k])
    fins = [(1997, 'Paulínia*'), (2017, 'Porto Real'), (2021, 'Jaboticabal'), (2022, 'Pirapora do B. J.'), (2025, 'Ubiratã'), (2025, 'Monte Mor*'), (2026, 'Getulina')]
    cnt = {}
    for a, n in fins:
        k = cnt.get(a, 0); cnt[a] = k + 1
        ax.bar(a, -1, 0.75, bottom=-k, color='#FFFFFF', edgecolor=TZ, hatch='////', lw=0.6)
    ax.bar(2026, -1, 0.75, bottom=-1, color='#FFFFFF', edgecolor=TZ_TXT, lw=0.9)  # São Caetano do Sul: restrição (1c), sem fim
    for a in (1992, 1996, 2000, 2004, 2008, 2012, 2016, 2020, 2024): ax.axvspan(a - 0.5, a + 0.5, color=cor('grafite', 100), zorder=0, lw=0)
    for j, a in enumerate(anos):
        if bot[j] > 0: ax.text(a, bot[j] + 0.4, str(int(bot[j])), ha='center', va='bottom', fontsize=6.3)
    ax.axhline(0, color=EIXO, lw=0.8); ax.set_xlim(1989.4, 2026.6); ax.set_ylim(-3.2, 41); barra_v(ax)
    ax.set_xticks(range(1990, 2027, 4), [str(v) for v in range(1990, 2027, 4)]); ax.set_ylabel('políticas universais por ano de início')
    legenda_topo(fig, [chapa(lab[k], cores[k]) for k in ('adit', 'nova', 'pub', 'nd')] +
                 [Patch(facecolor='#FFFFFF', edgecolor=TZ, hatch='////', label='fim ou recuo da gratuidade universal (abaixo do eixo)'),
                  Patch(facecolor='#FFFFFF', edgecolor=TZ_TXT, lw=1.2, label='restrição sem fim (São Caetano do Sul, 2026)'),
                  chapa('ano de eleição municipal', cor('grafite', 100))], ncol=2)
    salvar(fig, 'tese-r65-c8-linha-tempo')
    print({k: sum(v) for k, v in C.items()}, 'total', sum(sum(v) for v in C.values()), 'sem ano:', int(u.ano.isna().sum()))

# ── preço do quilômetro × CadTerc, por forma de entrada ───────────────────
@reg
def r65_c8_preco():
    k = pd.read_csv(D / 'Analises_Cap6' / 'km_tz_cadterc_saida_2026-10-11.csv')
    k = k[k.leitura.isin(['contrato', 'homologação', 'aditivo']) & ~k.municipio.str.contains('micro')].copy()
    fx = pd.read_csv(D / 'Analises_Cap6' / 'km_cadterc_faixas_2026-10-11.csv').set_index('regime')
    m = pd.read_excel(BASE, sheet_name='consolidado')
    pre = {(a, b): classe(c) for a, b, c in zip(m['Município'], m.UF, m['Prestação (eixo 2)'])}
    grp = {(a, b): str(c).startswith(('operador em grupo', 'operador é empresa isolada de grande')) for a, b, c in zip(m['Município'], m.UF, m['Operador × GE — resultado (cruzamento)'])}
    k['forma'] = [pre.get((a, b), 'nd') for a, b in zip(k.municipio, k.uf)]
    k.loc[k.leitura == 'aditivo', 'forma'] = 'aditivo'
    k.loc[(k.forma == 'nd') & k.leitura.isin(['contrato', 'homologação']), 'forma'] = 'contrato'  # Assis: PE 90028/2026 homologado
    k['grupo'] = [grp.get((a, b), False) for a, b in zip(k.municipio, k.uf)]
    k = k.sort_values('rkm_mai2026').reset_index(drop=True)
    h = pd.read_csv(D / 'Analises_Cap6' / 'cap6_analise12_destinatario_2026-10-11.csv'); h = h[h.custo_hab.notna()].sort_values('custo_hab')
    fig, (a1, a2) = figura(10.2, ncols=2, gridspec_kw={'width_ratios': [1.25, 1]})
    d0, d1 = fx.loc['44 lugares, 2ª a domingo, diurno', '8000 km/mês'], fx.loc['44 lugares, 2ª a domingo, diurno', '4000 km/mês']
    u0, u1 = fx.loc['44 lugares, 2ª a domingo, diuturno', '8000 km/mês'], fx.loc['44 lugares, 2ª a domingo, diuturno', '4000 km/mês']
    a1.axvspan(d0, d1, color=cor('grafite', 200), lw=0, zorder=0); a1.axvspan(d1, u1, color=cor('grafite', 100), lw=0, zorder=0)
    a1.axvline(5.64, color=TZ_TXT, lw=0.8, ls=':')
    cf = {'aditivo': GRP, 'contrato': cor('azul', 300), 'concessao': cor('azul', 300), 'locacao': cor('azul', 300), 'direta': SEM, 'nd': SEM}
    for i, r in k.iterrows():
        c = cf.get(r.forma, SEM)
        a1.plot(r.rkm_mai2026, i, marker='D' if r.grupo else 'o', ms=5.2, color=c, mec=TINTA if r.grupo else c, mew=0.8 if r.grupo else 0)
    a1.set_yticks(range(len(k)), [f'{a} ({b})' for a, b in zip(k.municipio, k.uf)], fontsize=6.6); barra_h(a1)
    a1.set_xlim(4.5, 17.5); fmt_eixo(a1, 'x', 0); a1.set_xlabel('R$ por km, maio de 2026 (n = %d)' % len(k))
    a1.text(5.5, -0.9, 'R$ 5,64', fontsize=6.3, color=TZ_TXT, ha='right', va='top'); a1.set_title('A. Preço do quilômetro')
    med = k.rkm_mai2026.median(); a1.axvline(med, color=TINTA, lw=0.7, ls='--'); a1.text(med + 0.15, -0.9, 'mediana R$ ' + br(med, 2), fontsize=6.3, va='top')
    a1.set_ylim(-1.6, len(k) - 0.4)
    a2.barh([f"{r['Município']} ({r['UF']})" for _, r in h.iterrows()], h.custo_hab, color=cor('grafite', 500), height=0.62)
    m2 = h.custo_hab.median(); a2.axvline(m2, color=TINTA, lw=0.7, ls='--'); a2.text(m2 + 3, -0.9, 'mediana R$ ' + br(m2, 1), fontsize=6.3, va='top')
    a2.tick_params(axis='y', labelsize=6.6); barra_h(a2); a2.set_ylim(-1.6, len(h) - 0.4); a2.set_xlabel('R$ por habitante ao ano (n = %d)' % len(h))
    a2.set_title('B. Custo anual por habitante')
    legenda_topo(fig, [Line2D([], [], marker='o', ls='', color=GRP, ms=5, label='aditivo à concessão existente'),
                       Line2D([], [], marker='o', ls='', color=cor('azul', 300), ms=5, label='contrato novo ou locação (licitado ou emergencial)'),
                       Line2D([], [], marker='D', ls='', color='#FFFFFF', mec=TINTA, ms=5, label='operador de grupo econômico'),
                       chapa('CadTerc, 44 lugares, diurno (4 a 8 mil km/mês)', cor('grafite', 200)),
                       chapa('CadTerc, diuturno (até o teto)', cor('grafite', 100))], ncol=2)
    salvar(fig, 'tese-r65-c8-preco')
    print(k[['municipio', 'uf', 'rkm_mai2026', 'forma', 'grupo']].to_string(), 'mediana', med, 'hab', len(h), m2)

if __name__ == '__main__':
    for n in (sys.argv[1:] or list(R)): R[n]()
