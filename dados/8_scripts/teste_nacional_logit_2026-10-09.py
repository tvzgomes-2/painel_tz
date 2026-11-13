# -*- coding: utf-8 -*-
"""Teste nacional da hipótese (09/10/2026): logit penalizado de Firth com efeito fixo de UF.
Substitui, como teste principal, a GW logística de São Paulo (07/10/2026), que fica exploratória.
Etapas: (1) base — Y = adoção de Tarifa Zero (base-mestre: Ativa ou Encerrada; ano de início),
X = presença de empresa de grupo econômico multiempresa (Tabela mestre ago-2026) e de grande grupo
(os que somam metade do capital), covariáveis da Base Municipal v3; (2) modelos — Desenho A (todas as
adoções; interação grupo × faixa de população e grupo × posição no arranjo) e Desenho B (adoções de 2023
em diante, depois do Censo, contra quem ainda não tinha adotado; interação grupo × uso do ônibus por quem
trabalha no próprio município, Censo 2022). Erro-padrão agrupado por região geográfica intermediária.
Recorte dos testes (decisão do autor, 09/10/2026, revisão r46): as Partes 2 e 3 não usam as parciais em testes.
A especificação final (etapa 4) usa Y = Tarifa Zero universal (camada 1 ativa e encerradas cujo último desenho era universal)
e deixa fora da amostra os municípios com política parcial (aba 2 Parcial da planilha de tipologias e encerradas num desenho
parcial, como Paulínia/SP); a sensibilidade com as parciais tratadas como não adoção vai para resultados_final_sensibilidade.json.
As etapas 2 e 3 ficam como registro exploratório (todas as adoções, parciais incluídas).
Uso (na raiz do cofre): python "_meta/scripts/teste_nacional_logit_2026-10-09.py"
Saídas: 03 - Dados/_data/Análise espacial GE x TZ (out-2026, teste nacional)/
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import os
VAULT = os.environ.get('TZ_VAULT', os.getcwd())
os.environ.setdefault('TZ_DADOS', os.path.join(VAULT, '03 - Dados') + '/')
SAIDA = os.path.join(VAULT, '03 - Dados', '_data', 'Análise espacial GE x TZ (out-2026, teste nacional)')
os.makedirs(SAIDA, exist_ok=True)

# ===================== etapa 1: base =====================
import re, json, unicodedata
import pandas as pd, numpy as np
U = os.environ.get('TZ_DADOS', '/mnt/user-data/uploads/doutorado/03 - Dados/')
n = lambda s: re.sub(r"\s+", " ", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip())

df = pd.read_csv(U + '_data/Base Municipal v3/base_municipal_v3.csv', low_memory=False)
df['cod_ibge'] = df.cod_ibge.astype(int)
print('municípios', len(df))

# ---- Y
m = pd.read_excel(U + '_data/casos por fonte/Municípios TZ - consolidado.xlsx', sheet_name='consolidado')
m['cod'] = pd.to_numeric(m['Código IBGE'], errors='coerce')
print('Situação', m['Situação'].value_counts().to_dict())
esc = m[m['Situação'].isin(['Ativa', 'Encerrada'])].copy()
esc['ano'] = pd.to_numeric(esc['Ano início'], errors='coerce')
univ = set(esc.loc[(esc['Situação'] == 'Ativa') & esc['Régua — aba'].astype(str).str.contains('1 Universal'), 'cod'].dropna().astype(int))
ano = dict(zip(esc.cod.astype(int), esc.ano))
df['tz_ever'] = df.cod_ibge.isin(ano).astype(int)
df['tz_univ'] = df.cod_ibge.isin(univ).astype(int)
df['tz_ano'] = df.cod_ibge.map(ano)
# recorte dos testes (r46): universal = camada 1 ativa + encerradas cujo último desenho é universal; parciais fora
enc_univ = set(esc.loc[(esc['Situação'] == 'Encerrada') & ~esc['Régua — subtipo'].astype(str).str.startswith('2'), 'cod'].dropna().astype(int))
par = set(esc.loc[esc['Régua — aba'].astype(str).str.startswith('2') | esc['Régua — subtipo'].astype(str).str.startswith('2'), 'cod'].dropna().astype(int))
tip2 = pd.read_excel(U + '_data/casos por fonte/Tipologias TZ - consolidado.xlsx', sheet_name='2 Parcial')
key0 = {(n(a), b): c for a, b, c in zip(df.nome_mun, df.uf, df.cod_ibge)}; key0[('embu das artes', 'SP')] = 3515004
for a, b, c in zip(tip2['Município'], tip2['UF'], tip2['Código IBGE']):
    if pd.notna(c): par.add(int(c))
    elif (n(a), str(b).strip()) in key0: par.add(key0[(n(a), str(b).strip())])
    else: print('parcial sem casamento:', a, b)
df['y_univ'] = (df.tz_univ.astype(bool) | df.cod_ibge.isin(enc_univ)).astype(int)
df['parcial'] = df.cod_ibge.isin(par).astype(int)
print('Y universal', df.y_univ.sum(), '(encerradas universais', len(enc_univ), ') · municípios com política parcial (fora dos testes)', df.parcial.sum())
print('tz_ever', df.tz_ever.sum(), 'tz_univ', df.tz_univ.sum(), 'com ano', df.tz_ano.notna().sum())

# ---- X
TM = U + 'Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx'
E = pd.read_excel(TM, sheet_name='Empresas')
R = pd.read_excel(TM, sheet_name='Resumo por grupo')
R = R.sort_values('capital_social_total_reais', ascending=False)
R['cum'] = R.capital_social_total_reais.cumsum() / R.capital_social_total_reais.sum()
top = set(R.loc[R.cum <= 0.5, 'id_grupo']) | {R.iloc[(R.cum > 0.5).values.argmax()].id_grupo}
multi = set(R.loc[R.n_empresas >= 2, 'id_grupo'])
print('grupos', len(R), 'multiempresa', len(multi), 'grandes (metade do capital)', len(top))
key = {(n(a), b): c for a, b, c in zip(df.nome_mun, df.uf, df.cod_ibge)}
key[('mogi mirim', 'SP')] = 3530805; key[('embu das artes', 'SP')] = 3515004
miss = {}
def munis(s):
    out = set()
    for p in str(s).split(';'):
        p = p.strip()
        if '/' in p:
            a, b = p.rsplit('/', 1); k = (n(a), b.strip())
            if k in key: out.add(key[k])
            elif len(b.strip()) == 2: miss[p] = miss.get(p, 0) + 1
    return out
E2 = E[E.id_grupo.notna()].copy()
pres = {}
for g, s1, s2 in zip(E2.id_grupo, E2.municipios_nucleo_ativo, E2.municipios_atuacao):
    for c in munis(s1) | munis(s2): pres.setdefault(c, set()).add(g)
print('nomes sem correspondência', len(miss), sorted(miss.items(), key=lambda x: -x[1])[:15])
df['ge_multi'] = df.cod_ibge.map(lambda c: int(bool(pres.get(c, set()) & multi)))
df['ge_top'] = df.cod_ibge.map(lambda c: int(bool(pres.get(c, set()) & top)))
df['ge_n'] = df.cod_ibge.map(lambda c: len(pres.get(c, ())))
print(df[['ge_multi', 'ge_top']].sum().to_dict())

# ---- covariáveis
df = df.copy()
df['log_pop'] = np.log(df.pop_2022)
df['faixa'] = pd.cut(df.pop_2022, [0, 20e3, 1e5, 2.5e5, 1e9], labels=['<20 mil', '20-100 mil', '100-250 mil', '>250 mil'])
df['log_pibpc'] = np.log(df.pib_per_capita_2021)
df['fpm'] = df.fpm_share_receita_corrente_2022
df['urb'] = df.taxa_urbanizacao_2022
df['bus_ficam'] = df.md22_modo_onibus_pct_ficam
df['bus17'] = pd.to_numeric(df.munic_onibus_intramun_2017, errors='coerce')
df['posicao'] = df.posicao_arranjo.fillna('isolado')
for c in ['log_pop', 'log_pibpc', 'fpm', 'urb', 'bus_ficam', 'bus17', 'rgint_cod_2022', 'reg']:
    print(c, 'NA', df[c].isna().sum())
print('posição', df.posicao.value_counts().to_dict())
cols = ['cod_ibge', 'nome_mun', 'uf', 'reg', 'rgint_cod_2022', 'pop_2022', 'tz_ever', 'tz_univ', 'y_univ', 'parcial', 'tz_ano', 'ge_multi', 'ge_top', 'ge_n',
        'log_pop', 'faixa', 'log_pibpc', 'fpm', 'urb', 'bus_ficam', 'bus17', 'posicao']
df[cols].to_csv(os.path.join(SAIDA, 'base_teste_nacional.csv'), index=False)
json.dump({'n_multi': len(multi), 'n_top': len(top), 'nomes_sem_match': miss,
           'base_mestre_situacao': m['Situação'].value_counts().to_dict()}, open(os.path.join(SAIDA, 'prep_meta.json'), 'w'), ensure_ascii=False, indent=1)

# ===================== etapa 2: modelos =====================
import json, numpy as np, pandas as pd
from scipy import stats

def firth(X, y, it=200, tol=1e-8):
    X = np.asarray(X, float); y = np.asarray(y, float)
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); w = p * (1 - p)
        XW = X * np.sqrt(w)[:, None]
        I = XW.T @ XW
        Ii = np.linalg.pinv(I)
        h = np.einsum('ij,jk,ik->i', XW, Ii, XW)
        U = X.T @ (y - p + h * (0.5 - p))
        step = Ii @ U
        mx = np.abs(step).max()
        if mx > 5: step *= 5 / mx
        b = b + step
        if np.abs(step).max() < tol: break
    p = 1 / (1 + np.exp(-X @ b)); w = p * (1 - p)
    XW = X * np.sqrt(w)[:, None]; I = XW.T @ XW; Ii = np.linalg.pinv(I)
    h = np.einsum('ij,jk,ik->i', XW, Ii, XW)
    return b, Ii, p, h

def cluster_vcov(X, y, p, h, Ii, g):
    s = X * (y - p + h * (0.5 - p))[:, None]
    S = pd.DataFrame(s).groupby(np.asarray(g)).sum().values
    G = S.shape[0]; n, k = X.shape
    c = G / (G - 1) * (n - 1) / (n - k)
    return c * Ii @ (S.T @ S) @ Ii

def fit(d, y, termos, fe='uf', cl='rgint_cod_2022', nome=''):
    d = d.dropna(subset=[c for c in termos if c in d.columns] + [y]).copy()
    if fe:
        ok = d.groupby(fe)[y].transform('sum') > 0
        d = d[ok]
    Xd = pd.DataFrame(index=d.index)
    for t in termos:
        if '*' in t:
            a, b = t.split('*'); Xd[t] = d[a] * d[b]
        else:
            Xd[t] = d[t]
    if fe:
        Xd = Xd.join(pd.get_dummies(d[fe], prefix=fe, drop_first=True, dtype=float))
    Xd.insert(0, 'const', 1.0)
    X = Xd.values.astype(float); yy = d[y].values.astype(float)
    b, Ii, p, h = firth(X, yy)
    V = cluster_vcov(X, yy, p, h, Ii, d[cl].values)
    res = pd.DataFrame({'coef': b, 'ep': np.sqrt(np.diag(V))}, index=Xd.columns)
    res['z'] = res.coef / res.ep; res['p'] = 2 * stats.norm.sf(res.z.abs())
    meta = dict(nome=nome, n=len(d), eventos=int(yy.sum()), ufs=int(d[fe].nunique()) if fe else None,
                clusters=int(d[cl].nunique()))
    return res, V, Xd.columns, meta, d

def combo(res, V, cols, pesos):
    w = np.array([pesos.get(c, 0.0) for c in cols])
    est = w @ res.coef.values; ep = np.sqrt(w @ V @ w)
    return dict(OR=float(np.exp(est)), ic_inf=float(np.exp(est - 1.96 * ep)), ic_sup=float(np.exp(est + 1.96 * ep)),
                p=float(2 * stats.norm.sf(abs(est / ep))))

d0 = pd.read_csv(os.path.join(SAIDA, 'base_teste_nacional.csv'))
d0['f3'] = (d0.pop_2022 >= 1e5).astype(int)
d0['f2'] = ((d0.pop_2022 >= 20e3) & (d0.pop_2022 < 1e5)).astype(int)
for c in ['log_pibpc', 'fpm', 'urb']:
    d0[c + '_z'] = (d0[c] - d0[c].mean()) / d0[c].std()
d0['bus_z'] = (d0.bus_ficam - d0.bus_ficam.mean()) / d0.bus_ficam.std()
d0['lpop_c'] = d0.log_pop - d0.log_pop.mean()
CTRL = ['fpm_z', 'log_pibpc_z', 'urb_z']
OUT = {}

def faixa_or(res, V, cols, X='ge_multi'):
    return {'<20 mil': combo(res, V, cols, {X: 1}),
            '20-100 mil': combo(res, V, cols, {X: 1, f'{X}*f2': 1}),
            '≥100 mil': combo(res, V, cols, {X: 1, f'{X}*f3': 1})}

def roda_A(nome, d, y='tz_ever', X='ge_multi', fe='uf'):
    termos = [X, 'f2', 'f3', f'{X}*f2', f'{X}*f3', 'lpop_c'] + CTRL
    res, V, cols, meta, dd = fit(d, y, termos, fe=fe, nome=nome)
    base, Vb, colsb, metab, _ = fit(d, y, [X, 'lpop_c'] + CTRL, fe=fe, nome=nome + ' (sem interação)')
    OUT[nome] = dict(meta=meta, global_=combo(base, Vb, colsb, {X: 1}),
                     fpm=combo(base, Vb, colsb, {'fpm_z': 1}),
                     por_faixa=faixa_or(res, V, cols, X),
                     coef=res.loc[[c for c in res.index if not c.startswith(fe or '#')]].round(4).to_dict('index'))
    return res

# ---------- Desenho A
roda_A('A1 principal (adoção, qualquer grupo multiempresa, UF)', d0)
roda_A('A2 região no lugar de UF', d0, fe='reg')
roda_A('A3 grande grupo (metade do capital)', d0, X='ge_top')
roda_A('A4 Y = universal ativa', d0, y='tz_univ')
roda_A('A5 só municípios com ônibus municipal (MUNIC 2017)', d0[d0.bus17 == 1])
# posição no arranjo
dA = d0.copy()
for k in ['polo', 'co-polo', 'satelite']:
    dA['pos_' + k] = (dA.posicao == k).astype(int)
dA['pos_central'] = dA[['pos_polo', 'pos_co-polo']].max(axis=1)
termos = ['ge_multi', 'pos_central', 'pos_satelite', 'ge_multi*pos_central', 'ge_multi*pos_satelite', 'lpop_c'] + CTRL
res, V, cols, meta, _ = fit(dA, 'tz_ever', termos, nome='A6 posição no arranjo')
OUT['A6 posição no arranjo'] = dict(meta=meta, por_posicao={
    'isolado': combo(res, V, cols, {'ge_multi': 1}),
    'polo ou co-polo': combo(res, V, cols, {'ge_multi': 1, 'ge_multi*pos_central': 1}),
    'satélite': combo(res, V, cols, {'ge_multi': 1, 'ge_multi*pos_satelite': 1})})

# ---------- Desenho B (pós-Censo)
dB = d0[~((d0.tz_ever == 1) & ~(d0.tz_ano >= 2023))].copy()
dB['y'] = (dB.tz_ano >= 2023).astype(int)
termos = ['ge_multi', 'bus_z', 'ge_multi*bus_z', 'lpop_c'] + CTRL
res, V, cols, meta, ddB = fit(dB, 'y', termos, nome='B1 pós-Censo, grupo × uso do ônibus')
sd = d0.bus_ficam.std(); mu = d0.bus_ficam.mean()
pts = {}
for v in [2, 5, 10, 15, 20, 30]:
    zz = (v - mu) / sd
    pts[f'{v}%'] = combo(res, V, cols, {'ge_multi': 1, 'ge_multi*bus_z': zz})
OUT['B1 pós-Censo, grupo × uso do ônibus'] = dict(meta=meta, por_uso_onibus=pts,
    onibus_principal=combo(res, V, cols, {'bus_z': 1}),
    coef=res.loc[[c for c in res.index if not c.startswith('uf')]].round(4).to_dict('index'),
    dist_uso=dict(media=float(mu), dp=float(sd), p90=float(d0.bus_ficam.quantile(.9)), p99=float(d0.bus_ficam.quantile(.99))))
base, Vb, colsb, mb, _ = fit(dB, 'y', ['ge_multi', 'bus_z', 'lpop_c'] + CTRL, nome='B0')
OUT['B1 pós-Censo, grupo × uso do ônibus']['global_'] = combo(base, Vb, colsb, {'ge_multi': 1})
OUT['B1 pós-Censo, grupo × uso do ônibus']['onibus_sem_interacao'] = combo(base, Vb, colsb, {'bus_z': 1})
roda_A('B2 pós-Censo, grupo × faixa', dB, y='y')
termos = ['ge_top', 'bus_z', 'ge_top*bus_z', 'lpop_c'] + CTRL
res, V, cols, meta, _ = fit(dB, 'y', termos, nome='B3 pós-Censo, grande grupo × uso do ônibus')
OUT['B3 pós-Censo, grande grupo × uso do ônibus'] = dict(meta=meta, por_uso_onibus={
    f'{v}%': combo(res, V, cols, {'ge_top': 1, 'ge_top*bus_z': (v - mu) / sd}) for v in [2, 5, 10, 15, 20, 30]})
res, V, cols, meta, _ = fit(dB, 'y', ['ge_multi', 'bus_z', 'ge_multi*bus_z', 'lpop_c'] + CTRL, fe='reg', nome='B4 região')
OUT['B4 pós-Censo, região no lugar de UF'] = dict(meta=meta, por_uso_onibus={
    f'{v}%': combo(res, V, cols, {'ge_multi': 1, 'ge_multi*bus_z': (v - mu) / sd}) for v in [2, 5, 10, 15, 20, 30]})

# contagens brutas
tab = d0.assign(fx=np.select([d0.f3 == 1, d0.f2 == 1], ['≥100 mil', '20-100 mil'], '<20 mil')).groupby(['fx', 'ge_multi']).tz_ever.agg(['sum', 'count'])
OUT['bruto_A'] = {f'{a} | grupo={b}': f'{int(r["sum"])}/{int(r["count"])}' for (a, b), r in tab.iterrows()}
json.dump(OUT, open(os.path.join(SAIDA, 'resultados_nacional.json'), 'w'), ensure_ascii=False, indent=1)

def fmt(r): return f"{r['OR']:.2f} [{r['ic_inf']:.2f}–{r['ic_sup']:.2f}] p={r['p']:.3f}"
for k, v in OUT.items():
    if k == 'bruto_A': print(k, v); continue
    print('\n==', k, v['meta'])
    for kk in ['global_', 'fpm', 'onibus_sem_interacao', 'onibus_principal']:
        if kk in v: print('  ', kk, fmt(v[kk]))
    for kk in ['por_faixa', 'por_posicao', 'por_uso_onibus']:
        if kk in v:
            for a, r in v[kk].items(): print('   ', kk, a, fmt(r))

# ===================== etapa 3: variantes (faixas de uso do ônibus, posição com grande grupo) =====================
def fmt(r): return f"{r['OR']:.2f} [{r['ic_inf']:.2f}–{r['ic_sup']:.2f}] p={r['p']:.3f}"
X={}
dB = d0[~((d0.tz_ever == 1) & ~(d0.tz_ano >= 2023))].copy(); dB['y'] = (dB.tz_ano >= 2023).astype(int)
for dd in (dB,):
    dd['b2']=((dd.bus_ficam>5)&(dd.bus_ficam<=10)).astype(int); dd['b3']=((dd.bus_ficam>10)&(dd.bus_ficam<=20)).astype(int); dd['b4']=(dd.bus_ficam>20).astype(int)
for X_ in ['ge_multi','ge_top']:
  t=[X_,'b2','b3','b4',f'{X_}*b2',f'{X_}*b3',f'{X_}*b4','lpop_c']+CTRL
  res,V,cols,meta,_=fit(dB,'y',t,nome='B5')
  r={'≤5%':combo(res,V,cols,{X_:1}),'5-10%':combo(res,V,cols,{X_:1,f'{X_}*b2':1}),'10-20%':combo(res,V,cols,{X_:1,f'{X_}*b3':1}),'>20%':combo(res,V,cols,{X_:1,f'{X_}*b4':1})}
  X[f'B5 pós-Censo, {X_} × faixa de uso do ônibus']=dict(meta=meta,por_faixa_onibus=r)
  print('\nB5',X_,meta); [print('  ',k,fmt(v)) for k,v in r.items()]
# sem controles fiscais (só UF): sensibilidade
t=['ge_multi','bus_z','ge_multi*bus_z','lpop_c']
res,V,cols,meta,_=fit(dB,'y',t,nome='B6')
mu=d0.bus_ficam.mean(); sd=d0.bus_ficam.std()
r={f'{v}%':combo(res,V,cols,{'ge_multi':1,'ge_multi*bus_z':(v-mu)/sd}) for v in [2,5,10,20,30]}
X['B6 pós-Censo, sem FPM/PIB/urbanização']=dict(meta=meta,por_uso_onibus=r); print('\nB6'); [print('  ',k,fmt(v)) for k,v in r.items()]
dA=d0.copy(); dA['pos_central']=dA.posicao.isin(['polo','co-polo']).astype(int); dA['pos_satelite']=(dA.posicao=='satelite').astype(int)
for ctrl,lab in [(CTRL,'com controles'),([],'sem controles fiscais')]:
  t=['ge_multi','pos_central','pos_satelite','ge_multi*pos_central','ge_multi*pos_satelite','lpop_c']+ctrl
  res,V,cols,meta,_=fit(dA,'tz_ever',t,nome='A6')
  r={'isolado':combo(res,V,cols,{'ge_multi':1}),'polo/co-polo':combo(res,V,cols,{'ge_multi':1,'ge_multi*pos_central':1}),'satélite':combo(res,V,cols,{'ge_multi':1,'ge_multi*pos_satelite':1})}
  X[f'A6 posição ({lab})']=dict(meta=meta,por_posicao=r); print('\nA6',lab); [print('  ',k,fmt(v)) for k,v in r.items()]
  # grande grupo
  t=['ge_top','pos_central','pos_satelite','ge_top*pos_central','ge_top*pos_satelite','lpop_c']+ctrl
  res,V,cols,meta,_=fit(dA,'tz_ever',t,nome='A7')
  r={'isolado':combo(res,V,cols,{'ge_top':1}),'polo/co-polo':combo(res,V,cols,{'ge_top':1,'ge_top*pos_central':1}),'satélite':combo(res,V,cols,{'ge_top':1,'ge_top*pos_satelite':1})}
  X[f'A7 grande grupo × posição ({lab})']=dict(meta=meta,por_posicao=r); print('A7',lab); [print('  ',k,fmt(v)) for k,v in r.items()]
json.dump(X,open(os.path.join(SAIDA, 'resultados_extra.json'),'w'),ensure_ascii=False,indent=1)

# ===================== etapa 4: especificação final, no recorte dos testes (decisões do autor, 09/10/2026) =====================
# Desenho A (principal): moderador = posição no arranjo. Desenho B (complementar): moderador = faixa de uso do ônibus.
# Controles nos dois: log da população + faixas de população, FPM, PIB per capita, urbanização; efeito fixo de UF.
# Y = Tarifa Zero universal; municípios com política parcial fora da amostra (r46). Sensibilidade: parciais como não adoção.
P4 = ['lpop_c', 'f2', 'f3'] + CTRL
def fmt(r): return f"{r['OR']:.2f} [{r['ic_inf']:.2f}–{r['ic_sup']:.2f}] p={r['p']:.3f}"
def faixasB(d):
    d = d[~((d.y_univ == 1) & ~(d.tz_ano >= 2023))].copy(); d['y'] = ((d.y_univ == 1) & (d.tz_ano >= 2023)).astype(int)
    d['b2'] = ((d.bus_ficam > 5) & (d.bus_ficam <= 10)).astype(int); d['b3'] = ((d.bus_ficam > 10) & (d.bus_ficam <= 20)).astype(int); d['b4'] = (d.bus_ficam > 20).astype(int)
    return d
def especificacao(d4):
    d4 = d4.copy()
    d4['pos_central'] = d4.posicao.isin(['polo', 'co-polo']).astype(int); d4['pos_satelite'] = (d4.posicao == 'satelite').astype(int)
    FINAL = {}
    for X_ in ['ge_multi', 'ge_top']:
        t = [X_, 'pos_central', 'pos_satelite', f'{X_}*pos_central', f'{X_}*pos_satelite'] + P4
        res, V, cols, meta, _ = fit(d4, 'y_univ', t, nome='final A')
        FINAL[f'A posição · {X_}'] = dict(meta=meta, por_posicao={
            'isolado': combo(res, V, cols, {X_: 1}),
            'satélite': combo(res, V, cols, {X_: 1, f'{X_}*pos_satelite': 1}),
            'polo/co-polo': combo(res, V, cols, {X_: 1, f'{X_}*pos_central': 1})},
            fpm=combo(res, V, cols, {'fpm_z': 1}))
        t = [X_, f'{X_}*f2', f'{X_}*f3'] + P4
        res, V, cols, meta, _ = fit(d4, 'y_univ', t, nome='final A porte')
        FINAL[f'A porte · {X_}'] = dict(meta=meta, por_faixa={'<20 mil': combo(res, V, cols, {X_: 1}),
            '20-100 mil': combo(res, V, cols, {X_: 1, f'{X_}*f2': 1}), '≥100 mil': combo(res, V, cols, {X_: 1, f'{X_}*f3': 1})})
    dB4 = faixasB(d4)
    for X_ in ['ge_multi', 'ge_top']:
        t = [X_, 'b2', 'b3', 'b4', f'{X_}*b2', f'{X_}*b3', f'{X_}*b4'] + P4
        res, V, cols, meta, _ = fit(dB4, 'y', t, nome='final B')
        FINAL[f'B uso do ônibus · {X_}'] = dict(meta=meta, por_faixa_onibus={
            '≤5%': combo(res, V, cols, {X_: 1}), '5-10%': combo(res, V, cols, {X_: 1, f'{X_}*b2': 1}),
            '10-20%': combo(res, V, cols, {X_: 1, f'{X_}*b3': 1}), '>20%': combo(res, V, cols, {X_: 1, f'{X_}*b4': 1})},
            fpm=combo(res, V, cols, {'fpm_z': 1}))
        mu, sd = d0.bus_ficam.mean(), d0.bus_ficam.std()
        res, V, cols, meta, _ = fit(dB4, 'y', [X_, 'bus_z', f'{X_}*bus_z'] + P4, nome='final B contínuo')
        FINAL[f'B uso do ônibus contínuo · {X_}'] = dict(meta=meta, por_uso_onibus={f'{v}%': combo(res, V, cols, {X_: 1, f'{X_}*bus_z': (v - mu) / sd}) for v in [2, 5, 10, 20, 30]},
            interacao_por_dp=combo(res, V, cols, {f'{X_}*bus_z': 1}))
    t = ['ge_multi', 'pos_central', 'pos_satelite', 'bus_z', 'ge_multi*pos_central', 'ge_multi*pos_satelite', 'ge_multi*bus_z'] + P4
    res, V, cols, meta, _ = fit(dB4, 'y', t, nome='B conjunto')
    FINAL['B conjunto (posição + uso do ônibus)'] = dict(meta=meta, interacoes={
        'grupo×polo': combo(res, V, cols, {'ge_multi*pos_central': 1}), 'grupo×satélite': combo(res, V, cols, {'ge_multi*pos_satelite': 1}),
        'grupo×ônibus (dp)': combo(res, V, cols, {'ge_multi*bus_z': 1})})
    # estrato alto (grande grupo e ônibus > 20%) nas UFs do desenho B: contagens, retirada de cada adoção e sem controles
    ok = set(dB4.groupby('uf').y.sum().loc[lambda x: x > 0].index)
    a = dB4[(dB4.b4 == 1) & dB4.uf.isin(ok) & dB4.fpm.notna()]
    t = ['ge_top', 'b2', 'b3', 'b4', 'ge_top*b2', 'ge_top*b3', 'ge_top*b4']
    loo = []
    for i in a[a.y == 1].index:
        res, V, cols, meta, _ = fit(dB4.drop(i), 'y', t + P4); loo.append(combo(res, V, cols, {'ge_top': 1, 'ge_top*b4': 1})['OR'])
    r1, V1, c1, _, _ = fit(dB4, 'y', t + CTRL); r2, V2, c2, _, _ = fit(dB4, 'y', t)
    FINAL['estrato alto B'] = dict(grande_grupo=f"{int(a[a.ge_top == 1].y.sum())}/{int((a.ge_top == 1).sum())}", sem_grande_grupo=f"{int(a[a.ge_top == 0].y.sum())}/{int((a.ge_top == 0).sum())}",
        adotantes=a[a.y == 1][['nome_mun', 'uf', 'ge_top']].values.tolist(), retirada_min=min(loo), retirada_max=max(loo),
        sem_porte=combo(r1, V1, c1, {'ge_top': 1, 'ge_top*b4': 1}), so_UF=combo(r2, V2, c2, {'ge_top': 1, 'ge_top*b4': 1}))
    dd = d4[d4.groupby('uf').y_univ.transform('sum') > 0]
    bruto = dd.groupby(['posicao', 'ge_multi']).y_univ.agg(['sum', 'count'])
    FINAL['taxas brutas A (UFs com adoção)'] = {f'{a} | grupo={b}': f"{int(r['sum'])}/{int(r['count'])} = {100*r['sum']/r['count']:.1f}%" for (a, b), r in bruto.iterrows()}
    FINAL['UFs com adoção'] = dict(ufs=int(dd.uf.nunique()), municipios=len(dd))
    FINAL['≥100 mil sem grupo (todas as UFs)'] = f"{int(d4[(d4.pop_2022 >= 1e5) & (d4.ge_multi == 0)].y_univ.sum())}/{int(((d4.pop_2022 >= 1e5) & (d4.ge_multi == 0)).sum())}"
    FINAL['mediana uso do ônibus por posição (%)'] = d4.groupby('posicao').bus_ficam.median().round(1).to_dict()
    return FINAL, dB4
def imprime(FINAL, titulo):
    print(f'\n===== {titulo} =====')
    for k, v in FINAL.items():
        if 'meta' in v: print(k, v['meta']['n'], v['meta']['eventos'], 'UFs', v['meta']['ufs'])
        for kk in ['por_posicao', 'por_faixa', 'por_faixa_onibus', 'por_uso_onibus', 'interacoes']:
            if kk in v:
                for a, r in v[kk].items(): print('   ', a, fmt(r))
        for kk in ['fpm', 'interacao_por_dp', 'sem_porte', 'so_UF']:
            if kk in v: print('   ', kk, fmt(v[kk]))
        if 'meta' not in v and not any(kk in v for kk in ['sem_porte']): print('   ', v)
        if 'sem_porte' in v: print('   ', {k2: v[k2] for k2 in ['grande_grupo', 'sem_grande_grupo', 'adotantes', 'retirada_min', 'retirada_max']})
FINAL, dB4 = especificacao(d0[d0.parcial == 0])
json.dump(FINAL, open(os.path.join(SAIDA, 'resultados_final.json'), 'w'), ensure_ascii=False, indent=1)
imprime(FINAL, 'ESPECIFICAÇÃO FINAL — recorte dos testes (só universal; parciais fora da amostra)')
SENS, _ = especificacao(d0)
json.dump(SENS, open(os.path.join(SAIDA, 'resultados_final_sensibilidade.json'), 'w'), ensure_ascii=False, indent=1)
imprime(SENS, 'SENSIBILIDADE — parciais tratadas como não adoção')
# lista do estrato alto sem Tarifa Zero universal (grande grupo, ônibus > 20%), nas UFs do desenho B
ok = set(dB4.groupby('uf').y.sum().loc[lambda x: x > 0].index)
alvo = dB4[(dB4.ge_top == 1) & (dB4.bus_ficam > 20) & (dB4.y == 0)]
alvo[alvo.uf.isin(ok)].sort_values(['uf', 'pop_2022'], ascending=[True, False])[['cod_ibge', 'nome_mun', 'uf', 'pop_2022', 'bus_ficam', 'posicao', 'ge_n']].to_csv(os.path.join(SAIDA, 'lista_estrato_alto.csv'), index=False)
alvo[~alvo.uf.isin(ok)][['cod_ibge', 'nome_mun', 'uf', 'pop_2022', 'bus_ficam', 'posicao']].to_csv(os.path.join(SAIDA, 'lista_estrato_alto_fora_desenho_B.csv'), index=False)
print('estrato alto sem Tarifa Zero universal:', int(alvo.uf.isin(ok).sum()), 'nas UFs do desenho B;', int((~alvo.uf.isin(ok)).sum()), 'fora')
