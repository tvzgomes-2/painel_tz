#!/usr/bin/env python3
"""Banco Municipal v3 — FASE 1: séries históricas + taxas de crescimento, a
partir do que já temos. Gera serie_*.csv (município×ano), acrescenta as taxas
(CAGR) à base wide (v2 -> v3) e inicia o metadados.csv.

PREPARO (fontes em /tmp/v3src/):
  - pib_YYYY.csv (2002-2020): de banco_geral_nacional_csv_*.zip -> t_pib_hist/.
  - frota_munic_dezYYYY.csv (2013-2023): do mesmo zip -> t_denatran_*/.
  - serie_investimentos.csv: extraído do FINBRA_nacional/finbra_despesas_YYYY.csv
    via awk (coluna="Despesas Empenhadas"; cod_conta 4.4.00 / 4.4.90.51 / 4.0.00).
Demais fontes lidas direto de _data/ (FINBRA painel, v2, Base Municipal v3)."""
import pandas as pd, numpy as np, glob, re, unicodedata, os
SRC="/tmp/v3src"; V="/sessions/kind-sleepy-feynman/mnt/doutorado/03 - Dados/_data"
OUT=f"{V}/Base Municipal v3"; os.makedirs(OUT,exist_ok=True)
def c7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None
def norm(s):
    s=unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode()
    return re.sub(r'[^A-Z0-9]','',s.upper())
def cagr(a,b,n):
    a=pd.to_numeric(a,errors="coerce"); b=pd.to_numeric(b,errors="coerce")
    r=np.where((a>0)&(b>0),(b/a)**(1/n)-1,np.nan)
    return np.round(r*100,2)   # % ao ano

# ---------- 1) SÉRIE PIB (2002–2020) ----------
recs=[]
for f in sorted(glob.glob(f"{SRC}/pib_*.csv")):
    ano=int(re.search(r'pib_(\d{4})',f).group(1))
    d=pd.read_csv(f,dtype=str)
    col=[c for c in d.columns if c.startswith("ano_")][0]
    d=d.rename(columns={col:"pib"}); d["cod_ibge"]=d["cod"].map(c7); d["ano"]=ano
    recs.append(d[["cod_ibge","ano","pib"]])
serie_pib=pd.concat(recs,ignore_index=True).dropna(subset=["cod_ibge"])
serie_pib.to_csv(f"{OUT}/serie_pib.csv",index=False)

# ---------- ponte nome->código (do PIB 2020) ----------
p20=pd.read_csv(f"{SRC}/pib_2020.csv",dtype=str)
m=p20["municipio"].str.extract(r'^(.*)\((\w{2})\)\s*$')
p20["chave"]=m[1]+"|"+m[0].str.strip().map(norm); p20["cod_ibge"]=p20["cod"].map(c7)
bridge=p20[["chave","cod_ibge"]].dropna().drop_duplicates("chave")

# ---------- 2) SÉRIE FROTA (dez 2013–2023) ----------
recs=[]
for f in sorted(glob.glob(f"{SRC}/frota_munic_dez*.csv")):
    ano=int(re.search(r'dez(\d{4})',f).group(1))
    d=pd.read_csv(f,na_values=["-"])
    d["chave"]=d["uf"]+"|"+d["municipio"].map(norm)
    d=d.merge(bridge,on="chave",how="left").dropna(subset=["cod_ibge"])
    d["ano"]=ano
    recs.append(d[["cod_ibge","ano","total","automovel","motocicleta","onibus"]].rename(
        columns={"total":"frota_total","automovel":"frota_auto","motocicleta":"frota_moto","onibus":"frota_onibus"}))
serie_frota=pd.concat(recs,ignore_index=True)
serie_frota.to_csv(f"{OUT}/serie_frota.csv",index=False)

# ---------- 3) SÉRIE FINBRA (2019–2023) — receita/despesa + investimentos ----------
fb=pd.read_csv(f"{V}/Base Integrada/finbra_municipal_2019-2023.csv",dtype={"cod_ibge":str})
fb["cod_ibge"]=fb["cod_ibge"].map(c7); fb["ano"]=pd.to_numeric(fb["exercicio"],errors="coerce")
inv=pd.read_csv(f"{SRC}/serie_investimentos.csv",dtype={"cod_ibge":str})
inv["cod_ibge"]=inv["cod_ibge"].map(c7); inv["ano"]=pd.to_numeric(inv["exercicio"],errors="coerce")
fb=fb.merge(inv.drop(columns=["exercicio"]),on=["cod_ibge","ano"],how="left")
fb.to_csv(f"{OUT}/serie_finbra.csv",index=False)

# ---------- 4) SÉRIE POPULAÇÃO (2010/2015/2016/2022, de dados_gerais na v2) ----------
v2=pd.read_csv(f"{V}/Base Integrada/base_municipal_integrada_v2.csv",dtype={"cod_ibge":str})
popcols={"pop_2010":2010,"pop_2015":2015,"pop_2016":2016,"pop_2022":2022}
pp=[]
for c,a in popcols.items():
    if c in v2.columns:
        t=v2[["cod_ibge",c]].rename(columns={c:"populacao"}); t["ano"]=a; pp.append(t)
serie_pop=pd.concat(pp,ignore_index=True)[["cod_ibge","ano","populacao"]]
serie_pop.to_csv(f"{OUT}/serie_populacao.csv",index=False)

# ---------- 5) TAXAS (CAGR) no wide ----------
def pivot_last(serie,val,anos):
    w=serie.pivot_table(index="cod_ibge",columns="ano",values=val,aggfunc="first")
    return w
serie_pib["ano"]=serie_pib["ano"].astype(int)
pib_w=pivot_last(serie_pib,"pib",None)
fr_w=pivot_last(serie_frota,"frota_total",None)
fin_w=pivot_last(fb,"receita_liquida",None)
inv_w=pivot_last(fb,"investimentos",None)
pop_w=pivot_last(serie_pop,"populacao",None)

wide=v2.copy()
def add_rate(name,w,a,b):
    if a in w.columns and b in w.columns:
        r=cagr(w[a].reindex(wide["cod_ibge"]).values, w[b].reindex(wide["cod_ibge"]).values, b-a)
        wide[name]=r
def add_val(name,w,a):
    if a in w.columns:
        wide[name]=pd.to_numeric(w[a].reindex(wide["cod_ibge"]).values,errors="coerce")
add_rate("pib_cagr_2010_2020",pib_w,2010,2020)
add_rate("frota_cagr_2013_2023",fr_w,2013,2023)
add_rate("receita_cagr_2019_2023",fin_w,2019,2023)
add_rate("investimento_cagr_2019_2023",inv_w,2019,2023)
add_rate("pop_cagr_2010_2022",pop_w,2010,2022)
# snapshots fiscais recentes (investimento / obras) e share sobre despesa
add_val("investimentos_2022",inv_w,2022)
d22=fb[fb.ano==2022].set_index("cod_ibge")
for c in ["obras_instalacoes","despesa_empenhada"]:
    wide[c+"_2022"]=pd.to_numeric(d22[c].reindex(wide["cod_ibge"]).values,errors="coerce")
wide["pct_investimento_desp_2022"]=(wide["investimentos_2022"]/wide["despesa_empenhada_2022"]*100).round(2)
wide.to_csv(f"{OUT}/base_municipal_v3.csv",index=False)

# ---------- 6) METADADOS (starter, fase 1) ----------
meta=[
 ("serie_pib.csv","PIB municipal (série)","economia","IBGE (t_pib_hist)","R$ mil","2002–2020","valor anual","série"),
 ("serie_frota.csv","Frota por tipo (série)","motorização","DENATRAN","veículos","2013–2023 (dez)","ponte nome→código IBGE (99%)","série"),
 ("serie_finbra.csv","Receita/despesa/investimento (série)","fiscal","Siconfi/FINBRA Anexo I-D","R$","2019–2023","totais + investimentos (4.4) + obras (4.4.90.51) por munic×ano","série"),
 ("investimentos_2022","Investimentos (natureza 4.4)","fiscal","FINBRA I-D","R$","2022","categoria econômica 4.4.00.00.00","✅"),
 ("obras_instalacoes_2022","Obras e instalações (proxy infra)","fiscal","FINBRA I-D","R$","2022","natureza 4.4.90.51","✅"),
 ("pct_investimento_desp_2022","% investimento / despesa","fiscal","derivado","%","2022","inv/despesa empenhada","🧮"),
 ("investimento_cagr_2019_2023","Taxa cresc. investimento","fiscal","derivado","% a.a.","2019–2023","CAGR","🧮"),
 ("[PENDENTE] despesa_funcao_urbanismo","Despesa função Urbanismo (zeladoria/infra urbana, f.15) e Transporte (f.26)","fiscal","Siconfi — Despesas por Função (anexo NÃO coletado)","R$","2019–2023","exige nova coleta na API Siconfi","🌐"),
 ("serie_populacao.csv","População (série)","demografia","IBGE Censo/COPIS","habitantes","2010/2015/2016/2022","","série"),
 ("pib_cagr_2010_2020","Taxa cresc. PIB 2010–20","economia","derivado","% a.a.","2010–2020","CAGR geométrico","🧮"),
 ("frota_cagr_2013_2023","Taxa cresc. frota 2013–23","motorização","derivado","% a.a.","2013–2023","CAGR","🧮"),
 ("receita_cagr_2019_2023","Taxa cresc. receita 2019–23","fiscal","derivado","% a.a.","2019–2023","CAGR","🧮"),
 ("pop_cagr_2010_2022","Taxa cresc. pop 2010–22","demografia","derivado","% a.a.","2010–2022","CAGR","🧮"),
 ("renda_media_2010","Renda média mensal","economia","IBGE Censo 2010","R$","2010","(de dados_gerais)","✅"),
 ("area_km2","Área territorial","geografia","IBGE","km²","atual","(de dados_gerais)","✅"),
 ("total_de_areas_urbanizadas_km2_2019","Área urbanizada","uso do solo","IBGE","km²","2019","(de dados_gerais)","✅"),
]
pd.DataFrame(meta,columns=["id","rotulo","tema","fonte","unidade","ano_serie","metodo","status"]).to_csv(f"{OUT}/metadados.csv",index=False)

print("FASE 1 OK ->",OUT)
print(f"  serie_pib: {serie_pib.cod_ibge.nunique()} munic × {serie_pib.ano.nunique()} anos ({serie_pib.ano.min()}–{serie_pib.ano.max()})")
print(f"  serie_frota: {serie_frota.cod_ibge.nunique()} munic × {serie_frota.ano.nunique()} anos")
print(f"  serie_finbra: {fb.cod_ibge.nunique()} munic × {fb.exercicio.nunique()} anos")
print(f"  serie_pop: {serie_pop.cod_ibge.nunique()} munic × {serie_pop.ano.nunique()} anos")
print(f"  base_v3 wide: {wide.shape[0]} × {wide.shape[1]} col")
print(f"  investimentos 2022 preench.: {wide['investimentos_2022'].notna().sum()}")
print("  taxas+invest — amostra SP:")
print(wide[wide.cod_ibge=='3550308'][['pib_cagr_2010_2020','frota_cagr_2013_2023','receita_cagr_2019_2023','investimento_cagr_2019_2023','pop_cagr_2010_2022','investimentos_2022','pct_investimento_desp_2022']].to_string(index=False))
