"""Análise III (Cap. 2) — despesa municipal com infraestrutura viária × transporte coletivo.
Fonte: FINBRA/SICONFI, DCA Anexo I-E (despesa por função/subfunção), 2019-2023, despesas liquidadas.
Entrada: 03 - Dados/_data/FINBRA_nacional/finbra_funcao_AAAA.csv ; base_municipal_v3.csv (faixa_pop_2022, tz).
Saída: 03 - Dados/_data/Analises_Cap2/analise_III_*.csv
Limite de método: o Anexo I-E só discrimina as subfunções típicas de cada função; a subfunção 453
(transportes coletivos urbanos) aparece discriminada sob a função 15 (15.453), mas quando lançada sob a
função 26 cai em 'FU26 - Demais Subfunções'. Por isso o TPC é medido em duas versões: identificável (15.453)
e teto (15.453 + FU26 Demais Subfunções). Criado em 01/10/2026.
"""
import pandas as pd, os
BASE=os.path.expanduser('~/mnt/doutorado/03 - Dados/_data')
OUT=f'{BASE}/Analises_Cap2'
CONTAS={'Despesas Exceto Intraorçamentárias':'total','26 - Transporte':'f26','26.782 - Transporte Rodoviário':'s782',
        '15.451 - Infraestrutura Urbana':'s451','15.453 - Transportes Coletivos Urbanos':'s453','FU26 - Demais Subfunções':'fu26','26.122 - Administração Geral':'s26_122'}
b=pd.read_csv(f'{BASE}/Base Municipal v3/base_municipal_v3.csv',usecols=['cod_ibge','faixa_pop_2022','pop_2022','tz_universal','tz_ano_inicio'],low_memory=False)
b['cod_ibge']=b.cod_ibge.astype(str)
rows=[]
for y in range(2019,2024):
    d=pd.read_csv(f'{BASE}/FINBRA_nacional/finbra_funcao_{y}.csv',usecols=['cod_ibge','coluna','conta','valor'],dtype={'cod_ibge':str})
    d=d[(d.coluna=='Despesas Liquidadas')&(d.conta.isin(CONTAS))]
    w=d.pivot_table(index='cod_ibge',columns='conta',values='valor',aggfunc='sum').rename(columns=CONTAS).fillna(0)
    w['ano']=y; rows.append(w.reset_index())
m=pd.concat(rows).merge(b,on='cod_ibge',how='left')
m['tpc_ident']=m.s453; m['tpc_teto']=m.s453+m.fu26
m['viario']=m.s782+m.s451
m['tz_no_ano']=((m.tz_universal==1)&(m.tz_ano_inicio<=m.ano)).astype(int)
m.to_csv(f'{OUT}/analise_III_finbra_municipio_ano.csv',index=False)
agg=lambda g: pd.Series({'municipios':g.cod_ibge.nunique(),'total':g.total.sum(),'s782':g.s782.sum(),'s451':g.s451.sum(),'s453':g.s453.sum(),'fu26':g.fu26.sum(),
    'mun_com_782':(g.s782>0).sum(),'mun_com_453':(g.s453>0).sum(),'mun_com_fu26':(g.fu26>0).sum()})
br=m.groupby('ano').apply(agg).reset_index()
for c in ['s782','s451','s453','fu26']: br[f'pct_{c}']=100*br[c]/br.total
br['razao_782_sobre_tpcteto']=br.s782/(br.s453+br.fu26)
br['razao_viario_sobre_tpcteto']=(br.s782+br.s451)/(br.s453+br.fu26)
br.to_csv(f'{OUT}/analise_III_brasil_ano.csv',index=False)
fx=m[m.ano==2023].groupby('faixa_pop_2022').apply(agg).reset_index()
for c in ['s782','s451','s453','fu26']: fx[f'pct_{c}']=100*fx[c]/fx.total
fx.to_csv(f'{OUT}/analise_III_faixa_2023.csv',index=False)
tz=m.groupby(['ano','tz_no_ano']).apply(agg).reset_index()
for c in ['s782','s451','s453','fu26']: tz[f'pct_{c}']=100*tz[c]/tz.total
tz.to_csv(f'{OUT}/analise_III_tz_ano.csv',index=False)
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
print(br.round(3).to_string()); print(fx.round(3).to_string()); print(tz.round(3).to_string())
sp=m[(m.cod_ibge=='3550308')][['ano','f26','s782','fu26','s26_122','s453']]; print(sp.to_string())
