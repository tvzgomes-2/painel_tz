#!/usr/bin/env python3
"""Base Municipal Integrada v2 — layout rico da POLO (dados_gerais) + dados mais
atualizados. Join por código IBGE (7 díg). Fontes:
  - dados_gerais (POLO)  : espinha (~96 vars: pop2022, PIB2021, veíc2023, eleições2020,
                           entorno2010, IBEU/IDH, PDMU, concessionária/frota_bus…)
  - FINBRA 2022          : receita/despesa (base_municipal_integrada_2022.csv)
  - Censo 2022 (SIDRA)   : deslocamento trabalho/estudo + entorno urbanístico 2022
  - base-mestre TZ (155) : tz_universal/situacao/ano
  - Novo BD (PlanMobs)   : Passe Livre eleitoral 2022 (PASSE_1T/2T/AB_PASSE)
Saída: base_municipal_integrada_v2.csv (+ dicionário de origem impresso)."""
import pandas as pd, numpy as np
V="/sessions/kind-sleepy-feynman/mnt/doutorado/03 - Dados/_data"
def c7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None

# 1) espinha: dados_gerais
dg=pd.read_csv("/tmp/v2/dados_gerais.csv",dtype=str)
dg["cod_ibge"]=dg["cod_mun"].map(c7)
dg=dg.drop(columns=[c for c in ["cod_mun"] if c in dg.columns])

# 2) FINBRA 2022 (só o fiscal recente)
fb=pd.read_csv(f"{V}/Base Integrada/base_municipal_integrada_2022.csv",dtype={"cod_ibge":str})
fb["cod_ibge"]=fb["cod_ibge"].map(c7)
fb=fb[["cod_ibge","receita_liquida","receita_corrente","despesa_empenhada"]].rename(columns={
    "receita_liquida":"finbra_receita_liquida_2022","receita_corrente":"finbra_receita_corrente_2022",
    "despesa_empenhada":"finbra_despesa_empenhada_2022"})

# 3) Censo 2022 (SIDRA)
def sidra(name):
    d=pd.read_csv(f"{V}/sidra_censo2022/{name}",dtype=str,na_values=["-"])
    d["cod_ibge"]=d["cod_mun"].map(c7); return d.drop(columns=["cod_mun"])
tr=sidra("deslocamento_trabalho_2022.csv"); es=sidra("deslocamento_estudo_2022.csv"); en=sidra("entorno_urbanistico_2022.csv")

# 4) TZ base-mestre
tz=pd.read_excel(f"{V}/casos por fonte/Municípios TZ - consolidado.xlsx")
tz["cod_ibge"]=tz["Código IBGE"].map(c7)
tz=tz[["cod_ibge","Situação","Ano início"]].rename(columns={"Situação":"tz_situacao","Ano início":"tz_ano_inicio"})
tz["tz_universal"]=1

# 5) Passe Livre 2022 (Novo BD)
nb=pd.read_excel(f"{V}/Base Integrada/BD PlanMobs_Dashboard.xlsx",sheet_name="Novo BD")
nb["cod_ibge"]=nb["CODMUNDV"].map(c7)
passe=nb[["cod_ibge","PASSE_1T","PASSE_2T","ABG_PASSE"]].rename(columns={
    "PASSE_1T":"passe_1turno_2022","PASSE_2T":"passe_2turno_2022","ABG_PASSE":"passe_abrangencia_2022"})

# join
b=dg
for extra in (fb,tr,es,en,tz,passe):
    b=b.merge(extra,on="cod_ibge",how="left")
b["tz_universal"]=b["tz_universal"].fillna(0).astype(int)

# derivadas (numéricas)
def num(s): return pd.to_numeric(b[s],errors="coerce")
b["pct_trab_outro_munic_2022"]=(num("trab_outro_municipio")/num("trab_total")*100).round(2)
b["pct_estuda_outro_munic_2022"]=(num("estudo_outro_municipio")/num("estudo_total")*100).round(2)
b["pct_calcada_2022"]=(num("calcada_existe")/num("entorno_total")*100).round(2)
b["pct_iluminacao_2022"]=(num("iluminacao_publica_existe")/num("entorno_total")*100).round(2)
b["pct_rampa_2022"]=(num("rampa_cadeirante_existe")/num("entorno_total")*100).round(2)
b["motorizacao_2023"]=(num("veic_2023")/num("pop_2022")).round(4)

out=f"{V}/Base Integrada/base_municipal_integrada_v2.csv"
b.to_csv(out,index=False)
print(f"v2: {len(b)} municípios × {b.shape[1]} colunas -> {out}")
print(f"  com FINBRA 2022: {b.finbra_receita_liquida_2022.notna().sum()} | Censo desloc: {b.trab_total.notna().sum()} | entorno: {b.entorno_total.notna().sum()} | TZ: {int(b.tz_universal.sum())} | Passe 1T preench.: {b.passe_1turno_2022.notna().sum()}")
print("\nSCS (3548807):")
print(b[b.cod_ibge=='3548807'][['cod_ibge','pop_2022','pib_per_capita_2021','motorizacao_2023','pct_trab_outro_munic_2022','pct_calcada_2022','tz_universal','passe_1turno_2022']].to_string(index=False))
