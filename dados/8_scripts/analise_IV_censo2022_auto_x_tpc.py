"""Análise IV (Cap. 2, Seção 2.4) — automóvel × transporte público coletivo no deslocamento habitual (Censo 2022).
Fonte: IBGE, Censo 2022, SIDRA 10332 (percentual de pessoas por meio de transporte habitual para trabalho/estudo),
arquivo 03 - Dados/_data/sidra_censo2022/censo2022_matriz_modal_por_municipio.csv ; pesos e faixas: base_municipal_v3.csv.
Mesma ponderação da Análise I (população 2022). TPC = Ônibus + BRT + Trem ou metrô (van/perua fica à parte).
Saída: 03 - Dados/_data/Analises_Cap2/analise_IV_*.csv. Criado em 01/10/2026.
"""
import pandas as pd, os
BASE=os.path.expanduser('~/mnt/doutorado/03 - Dados/_data')
OUT=f'{BASE}/Analises_Cap2'
d=pd.read_csv(f'{BASE}/sidra_censo2022/censo2022_matriz_modal_por_municipio.csv')
w=d.pivot_table(index='codigo_municipio',columns='meio_transporte',values='percentual',aggfunc='sum').fillna(0)
G={'auto':['Automóvel'],'moto':['Motocicleta'],'taxi_app':['Táxi ou assemelhados'],'mototaxi':['Mototáxi'],
   'tpc':['Ônibus','BRT ou ônibus de trânsito rápido','Trem ou metrô'],'onibus':['Ônibus'],'brt':['BRT ou ônibus de trânsito rápido'],'trilhos':['Trem ou metrô'],
   'van':['Van, perua ou assemelhados'],'ape':['A pé'],'bici':['Bicicleta']}
g=pd.DataFrame({k:w[v].sum(axis=1) for k,v in G.items()}); g.index=g.index.astype(str)
b=pd.read_csv(f'{BASE}/Base Municipal v3/base_municipal_v3.csv',usecols=['cod_ibge','uf','faixa_pop_2022','pop_2022','tz_universal','tz_ano_inicio'],low_memory=False)
b['cod_ibge']=b.cod_ibge.astype(str); b=b.set_index('cod_ibge')
m=g.join(b,how='left')
REG={'N':'RO AC AM RR PA AP TO','NE':'MA PI CE RN PB PE AL SE BA','SE':'MG ES RJ SP','S':'PR SC RS','CO':'MS MT GO DF'}
r2={u:k for k,v in REG.items() for u in v.split()}; m['regiao']=m.uf.map(r2)
m['tz2022']=((m.tz_universal==1)&(m.tz_ano_inicio<=2022)).astype(int)
m['tpc_maior_auto']=(m.tpc>m.auto).astype(int)
cols=list(G)
def wavg(x): 
    s=x.pop_2022.sum(); out={c:(x[c]*x.pop_2022).sum()/s for c in cols}
    out.update(municipios=len(x),pop_mi=s/1e6,mun_tpc_maior_auto=int(x.tpc_maior_auto.sum()),
               pop_tpc_maior_auto_mi=x.loc[x.tpc_maior_auto==1,'pop_2022'].sum()/1e6,
               media_simples_auto=x.auto.mean(),media_simples_tpc=x.tpc.mean())
    return pd.Series(out)
br=wavg(m.copy()).to_frame('Brasil').T
fx=m.groupby('faixa_pop_2022').apply(wavg); rg=m.groupby('regiao').apply(wavg)
tz=m.groupby(['faixa_pop_2022','tz2022']).apply(wavg)
for name,t in [('brasil',br),('faixa',fx),('regiao',rg),('faixa_tz',tz)]:
    t['razao_auto_tpc']=t.auto/t.tpc; t.to_csv(f'{OUT}/analise_IV_{name}.csv')
m.to_csv(f'{OUT}/analise_IV_municipio.csv')
pd.set_option('display.width',250); pd.set_option('display.max_columns',40)
for t in (br,fx,rg,tz): print(t.round(2).to_string()); print()
print('soma pop',m.pop_2022.sum(), 'sem pop', m.pop_2022.isna().sum())
print(m.sort_values('pop_2022',ascending=False).head(15)[['uf','pop_2022','auto','tpc','taxi_app','moto']].round(1).to_string())
